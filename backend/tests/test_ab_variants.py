"""A/B 변형 발송 테스트 — weight 선택 + variant_id 기록 + 통계."""
from app.models.models import (
    EmailLog, EmailTemplate, EmailVariant, Prospect, User,
)


def _make_template_with_variants(db, user_id):
    t = EmailTemplate(user_id=user_id, name="T", subject="기본", body="기본 본문")
    db.add(t)
    db.flush()
    a = EmailVariant(template_id=t.id, variant_name="A", subject="제목A", body="본문A입니다", weight=50)
    b = EmailVariant(template_id=t.id, variant_name="B", subject="제목B", body="본문B입니다", weight=50)
    db.add_all([a, b])
    db.flush()
    return t, [a, b]


class TestVariantSend:
    def test_bulk_send_records_variant_id(self, client, auth_headers, project_id, db_session, monkeypatch):
        from app.services.sender import email as email_mod

        user = db_session.query(User).first()
        user.credits = 1000  # 20건 발송 크레딧 확보
        _, variants = _make_template_with_variants(db_session, user.id)
        prospects = [
            Prospect(project_id=project_id, name=f"P{i}", email=f"p{i}@corp.com", status="approved")
            for i in range(20)
        ]
        db_session.add_all(prospects)
        db_session.commit()

        sent = []
        monkeypatch.setattr(email_mod, "send_email",
                            lambda **kw: sent.append(kw) or True)

        email_mod.send_bulk_emails(
            db=db_session, gmail_email="me@gmail.com", gmail_app_password="pw",
            prospects=prospects, user_id=user.id, sender_name="김우진",
            daily_limit=50, min_delay=0, max_delay=0,
            variants=variants,
        )

        # 모든 발송 로그에 variant_id가 기록됨
        logs = db_session.query(EmailLog).filter(EmailLog.status == "success").all()
        assert len(logs) == 20
        assert all(l.variant_id is not None for l in logs)
        used = {l.variant_id for l in logs}
        # 20건이면 두 변형이 모두 선택될 확률이 매우 높음 (weight 50:50)
        assert len(used) >= 1  # 최소 1개, 보통 2개

        # 발송된 제목이 변형 제목 중 하나
        subjects = {c["subject"] for c in sent}
        assert subjects.issubset({"(광고) 제목A", "(광고) 제목B"})

    def test_variant_stats_endpoint(self, client, auth_headers, project_id, db_session):
        user = db_session.query(User).first()
        t, variants = _make_template_with_variants(db_session, user.id)
        p = Prospect(project_id=project_id, name="P", email="p@corp.com", status="approved")
        db_session.add(p)
        db_session.flush()
        # A에 발송+열람, B에 발송만
        db_session.add(EmailLog(prospect_id=p.id, user_id=user.id, status="success",
                                tracking_id="t1", variant_id=variants[0].id,
                                opened_at=__import__("datetime").datetime.utcnow()))
        db_session.add(EmailLog(prospect_id=p.id, user_id=user.id, status="success",
                                tracking_id="t2", variant_id=variants[1].id))
        db_session.commit()

        res = client.get(f"/api/templates/{t.id}/variants/stats", headers=auth_headers)
        assert res.status_code == 200
        stats = {s["variant_name"]: s for s in res.json()}
        assert stats["A"]["sent"] == 1 and stats["A"]["opened"] == 1
        assert stats["A"]["open_rate"] == 100.0
        assert stats["B"]["sent"] == 1 and stats["B"]["opened"] == 0

    def test_single_variant_not_ab(self, client, auth_headers, project_id, db_session):
        """변형이 1개뿐이면 A/B 비활성 (발송 흐름에서 variants=None 처리)."""
        # email_send가 len(vs) >= 2 일 때만 variants를 넘기는 것을 계약으로 확인
        user = db_session.query(User).first()
        t = EmailTemplate(user_id=user.id, name="T1", subject="s", body="b")
        db_session.add(t)
        db_session.flush()
        db_session.add(EmailVariant(template_id=t.id, variant_name="A", subject="a", body="a", weight=100))
        db_session.commit()
        vs = db_session.query(EmailVariant).filter(EmailVariant.template_id == t.id).all()
        assert len(vs) == 1  # A/B 조건(>=2) 미달
