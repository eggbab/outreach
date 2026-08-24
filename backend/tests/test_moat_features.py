"""해자 기능 테스트 — 컴플라이언스, 수신거부, 반응 피드백 루프, 워밍업 강제, discover 과금."""
from datetime import datetime, timezone

import pytest

from app.models.models import (
    Blacklist,
    CreditTransaction,
    EmailLog,
    EmailSequence,
    GlobalProspect,
    GlobalUnsubscribe,
    Project,
    Prospect,
    SequenceEnrollment,
    User,
)
from app.services.compliance import (
    apply_ad_prefix,
    build_compliance_footer,
    build_list_unsubscribe_headers,
    inject_compliance_footer,
    is_email_suppressed,
)
from app.core.plans import get_enforced_daily_limit


# ──────────────────────────────────────
# 컴플라이언스 단위 테스트
# ──────────────────────────────────────

class TestCompliance:
    def test_ad_prefix_added(self):
        assert apply_ad_prefix("특가 제안").startswith("(광고) ")

    def test_ad_prefix_idempotent(self):
        once = apply_ad_prefix("특가 제안")
        assert apply_ad_prefix(once) == once

    def test_ad_prefix_disabled(self):
        assert apply_ad_prefix("특가 제안", enabled=False) == "특가 제안"

    def test_footer_contains_unsub_link_and_sender_info(self):
        footer = build_compliance_footer("tid123", "주식회사 테스트\n서울시 강남구\n02-1234-5678")
        assert "/api/t/unsub/tid123" in footer
        assert "주식회사 테스트" in footer
        assert "수신거부" in footer
        assert "광고성 정보" in footer

    def test_footer_injected_before_body_close(self):
        html = "<html><body><p>hi</p></body></html>"
        out = inject_compliance_footer(html, "<div>FOOTER</div>")
        assert out.index("FOOTER") < out.index("</body>")

    def test_footer_appended_without_body_tag(self):
        out = inject_compliance_footer("<p>hi</p>", "<div>FOOTER</div>")
        assert out.endswith("<div>FOOTER</div>")

    def test_list_unsubscribe_headers(self):
        headers = build_list_unsubscribe_headers("tid123")
        assert "/api/t/unsub/tid123" in headers["List-Unsubscribe"]
        assert headers["List-Unsubscribe-Post"] == "List-Unsubscribe=One-Click"


# ──────────────────────────────────────
# 발송 차단 (블랙리스트 + 전역 수신거부 풀)
# ──────────────────────────────────────

class TestSuppression:
    def test_user_blacklist_suppresses(self, client, auth_headers, db_session):
        user = db_session.query(User).first()
        db_session.add(Blacklist(user_id=user.id, email="bad@example.com"))
        db_session.commit()
        assert is_email_suppressed(db_session, user.id, "bad@example.com") is True
        assert is_email_suppressed(db_session, user.id, "BAD@example.com") is True

    def test_global_unsubscribe_suppresses_for_all_users(self, client, auth_headers, db_session):
        user = db_session.query(User).first()
        db_session.add(GlobalUnsubscribe(email="optout@example.com"))
        db_session.commit()
        assert is_email_suppressed(db_session, user.id, "optout@example.com") is True

    def test_clean_email_not_suppressed(self, client, auth_headers, db_session):
        user = db_session.query(User).first()
        assert is_email_suppressed(db_session, user.id, "ok@example.com") is False


# ──────────────────────────────────────
# 수신거부 엔드포인트
# ──────────────────────────────────────

def _make_prospect_with_log(db_session, project_id, tracking_id="unsub-tid-1", email="target@corp.com"):
    user = db_session.query(User).first()
    prospect = Prospect(project_id=project_id, name="타깃", email=email, status="email_sent")
    db_session.add(prospect)
    db_session.flush()
    log = EmailLog(
        prospect_id=prospect.id, user_id=user.id, status="success", tracking_id=tracking_id,
    )
    db_session.add(log)
    db_session.commit()
    return prospect, log


class TestUnsubscribeEndpoint:
    def test_get_shows_confirmation_page(self, client, auth_headers, project_id):
        res = client.get("/api/t/unsub/whatever")
        assert res.status_code == 200
        assert "수신거부" in res.text

    def test_post_registers_blacklist_and_global_pool(self, client, auth_headers, project_id, db_session):
        _make_prospect_with_log(db_session, project_id)
        res = client.post("/api/t/unsub/unsub-tid-1")
        assert res.status_code == 200
        assert "수신거부 완료" in res.text

        user = db_session.query(User).first()
        bl = db_session.query(Blacklist).filter(Blacklist.user_id == user.id).all()
        assert any(b.email == "target@corp.com" for b in bl)
        gu = db_session.query(GlobalUnsubscribe).filter(
            GlobalUnsubscribe.email == "target@corp.com"
        ).first()
        assert gu is not None

    def test_post_idempotent(self, client, auth_headers, project_id, db_session):
        _make_prospect_with_log(db_session, project_id)
        client.post("/api/t/unsub/unsub-tid-1")
        client.post("/api/t/unsub/unsub-tid-1")
        assert db_session.query(GlobalUnsubscribe).count() == 1

    def test_post_invalid_tracking_id(self, client):
        res = client.post("/api/t/unsub/nonexistent")
        assert res.status_code == 200
        assert "처리 불가" in res.text


# ──────────────────────────────────────
# 발송 파이프라인 (컴플라이언스 적용 + 차단 + 과금)
# ──────────────────────────────────────

class TestBulkSendCompliance:
    def test_bulk_send_applies_compliance_and_skips_suppressed(
        self, client, auth_headers, project_id, db_session, monkeypatch
    ):
        from app.services.sender import email as email_mod

        user = db_session.query(User).first()
        start_credits = user.credits

        p1 = Prospect(project_id=project_id, name="A사", email="a@corp.com", status="approved")
        p2 = Prospect(project_id=project_id, name="B사", email="optout@corp.com", status="approved")
        db_session.add_all([p1, p2])
        db_session.add(GlobalUnsubscribe(email="optout@corp.com"))
        db_session.commit()

        sent_calls = []

        def fake_send_email(gmail_email, gmail_app_password, to_email, subject, html_body, extra_headers=None):
            sent_calls.append({
                "to": to_email, "subject": subject,
                "html": html_body, "headers": extra_headers or {},
            })
            return True

        monkeypatch.setattr(email_mod, "send_email", fake_send_email)

        result = email_mod.send_bulk_emails(
            db=db_session,
            gmail_email="me@gmail.com",
            gmail_app_password="pw",
            prospects=[p1, p2],
            user_id=user.id,
            sender_name="김우진",
            daily_limit=10,
            min_delay=0,
            max_delay=0,
        )

        # 수신거부 대상은 발송 안 됨
        assert result["sent"] == 1
        assert result["skipped"] == 1
        assert len(sent_calls) == 1
        call = sent_calls[0]
        assert call["to"] == "a@corp.com"
        # (광고) 표기 + 수신거부 링크 + 추적 픽셀 + One-Click 헤더
        assert call["subject"].startswith("(광고) ")
        assert "/api/t/unsub/" in call["html"]
        assert "/api/t/open/" in call["html"]
        assert "List-Unsubscribe" in call["headers"]
        # 성공 1건 = 2크레딧 차감
        db_session.refresh(user)
        assert user.credits == start_credits - 2

    def test_bulk_send_respects_ad_prefix_disabled(
        self, client, auth_headers, project_id, db_session, monkeypatch
    ):
        from app.services.sender import email as email_mod

        user = db_session.query(User).first()
        p = Prospect(project_id=project_id, name="A사", email="a@corp.com", status="approved")
        db_session.add(p)
        db_session.commit()

        sent_calls = []
        monkeypatch.setattr(
            email_mod, "send_email",
            lambda **kw: sent_calls.append(kw) or True,
        )

        email_mod.send_bulk_emails(
            db=db_session, gmail_email="me@gmail.com", gmail_app_password="pw",
            prospects=[p], user_id=user.id, sender_name="김우진",
            daily_limit=10, min_delay=0, max_delay=0,
            ad_prefix_enabled=False,
        )
        assert not sent_calls[0]["subject"].startswith("(광고)")


# ──────────────────────────────────────
# 워밍업 강제 한도
# ──────────────────────────────────────

class TestWarmupEnforcement:
    def test_day_zero_capped_at_warmup_start(self):
        assert get_enforced_daily_limit("email", 0, 80) == 5

    def test_mid_warmup_follows_curve(self):
        # 10일차: 5 + 10*3 = 35
        assert get_enforced_daily_limit("email", 10, 80) == 35

    def test_warmup_curve_capped_by_user_limit(self):
        assert get_enforced_daily_limit("email", 10, 20) == 20

    def test_after_warmup_user_limit_wins(self):
        assert get_enforced_daily_limit("email", 60, 80) == 80

    def test_after_warmup_system_max_caps(self):
        assert get_enforced_daily_limit("email", 60, 9999) == 500


# ──────────────────────────────────────
# 반응 데이터 피드백 루프 (M1)
# ──────────────────────────────────────

class TestFeedbackLoop:
    def _setup(self, db_session, project_id, tracking_id="fb-tid-1"):
        user = db_session.query(User).first()
        gp = GlobalProspect(company_name="A사", email="a@corp.com", email_validity_score=0.3)
        db_session.add(gp)
        db_session.flush()
        prospect = Prospect(
            project_id=project_id, name="A사", email="a@corp.com",
            status="email_sent", global_prospect_id=gp.id,
        )
        db_session.add(prospect)
        db_session.flush()
        log = EmailLog(
            prospect_id=prospect.id, user_id=user.id, status="success", tracking_id=tracking_id,
        )
        db_session.add(log)
        db_session.commit()
        return gp, prospect, log

    def test_open_bumps_validity_and_score(self, client, auth_headers, project_id, db_session):
        gp, prospect, _ = self._setup(db_session, project_id)
        res = client.get("/api/t/open/fb-tid-1")
        assert res.status_code == 200
        db_session.refresh(gp)
        db_session.refresh(prospect)
        assert gp.times_opened == 1
        assert gp.email_validity_score >= 0.8
        assert gp.last_verified_at is not None
        assert prospect.score > 0

    def test_click_bumps_validity_higher(self, client, auth_headers, project_id, db_session):
        gp, _, _ = self._setup(db_session, project_id)
        res = client.get("/api/t/click/fb-tid-1", params={"url": "https://example.com"}, follow_redirects=False)
        assert res.status_code == 302
        db_session.refresh(gp)
        assert gp.times_clicked == 1
        assert gp.email_validity_score >= 0.95


# ──────────────────────────────────────
# 답장 감지 (M3)
# ──────────────────────────────────────

class TestReplyDetection:
    def test_reply_marks_prospect_and_stops_sequence(
        self, client, auth_headers, project_id, db_session, monkeypatch
    ):
        import app.services.reply_detector as rd

        user = db_session.query(User).first()
        gp = GlobalProspect(company_name="A사", email="a@corp.com", email_validity_score=0.5)
        db_session.add(gp)
        db_session.flush()
        prospect = Prospect(
            project_id=project_id, name="A사", email="a@corp.com",
            status="email_sent", global_prospect_id=gp.id,
        )
        db_session.add(prospect)
        db_session.flush()
        log = EmailLog(
            prospect_id=prospect.id, user_id=user.id, status="success", tracking_id="reply-tid",
        )
        seq = EmailSequence(user_id=user.id, project_id=project_id, name="시퀀스", status="active")
        db_session.add_all([log, seq])
        db_session.flush()
        enrollment = SequenceEnrollment(
            sequence_id=seq.id, prospect_id=prospect.id, status="active",
            next_send_at=datetime.now(timezone.utc),
        )
        db_session.add(enrollment)
        db_session.commit()

        monkeypatch.setattr(rd, "_fetch_recent_senders", lambda e, p: {"a@corp.com"})

        detected = rd.detect_replies_for_user(db_session, user.id, "me@gmail.com", "pw")
        db_session.commit()

        assert detected == 1
        db_session.refresh(prospect)
        db_session.refresh(enrollment)
        db_session.refresh(gp)
        db_session.refresh(log)
        assert prospect.status == "replied"
        assert enrollment.status == "stopped"
        assert gp.times_replied == 1
        assert gp.email_validity_score == 1.0
        assert log.replied_at is not None

    def test_no_reply_no_change(self, client, auth_headers, project_id, db_session, monkeypatch):
        import app.services.reply_detector as rd

        user = db_session.query(User).first()
        prospect = Prospect(project_id=project_id, name="A사", email="a@corp.com", status="email_sent")
        db_session.add(prospect)
        db_session.flush()
        db_session.add(EmailLog(
            prospect_id=prospect.id, user_id=user.id, status="success", tracking_id="nr-tid",
        ))
        db_session.commit()

        monkeypatch.setattr(rd, "_fetch_recent_senders", lambda e, p: {"other@corp.com"})
        assert rd.detect_replies_for_user(db_session, user.id, "me@gmail.com", "pw") == 0
        db_session.refresh(prospect)
        assert prospect.status == "email_sent"


# ──────────────────────────────────────
# Discover 과금 + 품질 정렬 (M1)
# ──────────────────────────────────────

class TestDiscoverBilling:
    def test_import_deducts_credits(self, client, auth_headers, project_id, db_session):
        user = db_session.query(User).first()
        start = user.credits
        gps = [
            GlobalProspect(company_name=f"업체{i}", email=f"c{i}@corp.com")
            for i in range(3)
        ]
        db_session.add_all(gps)
        db_session.commit()

        res = client.post(
            "/api/discover/import",
            json={"global_prospect_ids": [g.id for g in gps], "project_id": project_id},
            headers=auth_headers,
        )
        assert res.status_code == 200
        assert res.json()["imported"] == 3
        db_session.refresh(user)
        assert user.credits == start - 3
        tx = (
            db_session.query(CreditTransaction)
            .filter(CreditTransaction.user_id == user.id, CreditTransaction.amount == -3)
            .first()
        )
        assert tx is not None

    def test_import_insufficient_credits_rejected(self, client, auth_headers, project_id, db_session):
        user = db_session.query(User).first()
        user.credits = 2
        gps = [GlobalProspect(company_name=f"업체{i}", email=f"d{i}@corp.com") for i in range(3)]
        db_session.add_all(gps)
        db_session.commit()

        res = client.post(
            "/api/discover/import",
            json={"global_prospect_ids": [g.id for g in gps], "project_id": project_id},
            headers=auth_headers,
        )
        assert res.status_code == 402

    def test_quality_sort(self, client, auth_headers, db_session):
        low = GlobalProspect(company_name="저품질", email="low@corp.com", times_collected=99)
        high = GlobalProspect(
            company_name="고품질", email="high@corp.com",
            times_collected=1, times_replied=3, email_validity_score=1.0,
        )
        db_session.add_all([low, high])
        db_session.commit()

        res = client.get("/api/discover/", params={"sort": "quality"}, headers=auth_headers)
        assert res.status_code == 200
        items = res.json()["items"]
        assert items[0]["company_name"] == "고품질"
        assert items[0]["times_replied"] == 3

        res = client.get("/api/discover/", params={"sort": "popular"}, headers=auth_headers)
        assert res.json()["items"][0]["company_name"] == "저품질"


# ──────────────────────────────────────
# 설정 API 확장
# ──────────────────────────────────────

class TestComplianceSettings:
    def test_settings_roundtrip(self, client, auth_headers):
        res = client.put(
            "/api/settings/",
            json={"ad_prefix_enabled": False, "sender_info": "주식회사 테스트\n02-1234-5678"},
            headers=auth_headers,
        )
        assert res.status_code == 200
        body = res.json()
        assert body["ad_prefix_enabled"] is False
        assert "주식회사 테스트" in body["sender_info"]

        res = client.get("/api/settings/", headers=auth_headers)
        assert res.json()["ad_prefix_enabled"] is False

    def test_settings_default_ad_prefix_on(self, client, auth_headers):
        res = client.get("/api/settings/", headers=auth_headers)
        assert res.status_code == 200
        assert res.json()["ad_prefix_enabled"] is True
