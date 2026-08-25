"""이메일 바운스 감지 테스트 (IMAP은 모킹)."""
from app.models.models import (
    EmailLog, GlobalProspect, GlobalUnsubscribe, Project, Prospect, User,
)
from app.services import bounce_detector


def _setup_sent(db, email="dead@corp.com", credits=100):
    u = db.query(User).first()
    u.credits = credits
    proj = db.query(Project).first()
    gp = GlobalProspect(company_name="A", email=email, email_validity_score=0.5)
    db.add(gp)
    db.flush()
    p = Prospect(project_id=proj.id, name="A", email=email, email_valid=True,
                 status="email_sent", global_prospect_id=gp.id)
    db.add(p)
    db.flush()
    db.add(EmailLog(prospect_id=p.id, user_id=u.id, status="success", tracking_id="t1"))
    db.commit()
    return u, p, gp


class TestBounceDetection:
    def test_hard_bounce_marks_invalid_refunds_and_blocks(self, client, auth_headers, project_id, db_session, monkeypatch):
        u, p, gp = _setup_sent(db_session)
        start = u.credits

        # 하드 바운스 1건 반환
        monkeypatch.setattr(
            bounce_detector, "_fetch_bounces",
            lambda e, pw: [("dead@corp.com", True)],
        )
        n = bounce_detector.detect_bounces_for_user(db_session, u.id, "me@gmail.com", "pw")
        db_session.commit()

        assert n == 1
        db_session.refresh(p)
        db_session.refresh(gp)
        db_session.refresh(u)
        assert p.email_valid is False              # 재발송 스킵 대상
        assert gp.email_validity_score == 0.0      # 전역 품질 0
        assert u.credits == start + 2              # 이메일 1건(2크레딧) 환불
        assert db_session.query(GlobalUnsubscribe).filter(
            GlobalUnsubscribe.email == "dead@corp.com").first() is not None

    def test_soft_bounce_no_refund_no_block(self, client, auth_headers, project_id, db_session, monkeypatch):
        u, p, gp = _setup_sent(db_session, email="full@corp.com")
        start = u.credits
        monkeypatch.setattr(
            bounce_detector, "_fetch_bounces",
            lambda e, pw: [("full@corp.com", False)],  # 소프트 바운스
        )
        bounce_detector.detect_bounces_for_user(db_session, u.id, "me@gmail.com", "pw")
        db_session.commit()
        db_session.refresh(p)
        db_session.refresh(u)
        assert p.email_valid is False       # 여전히 재발송은 막음
        assert u.credits == start           # 소프트는 환불 안 함
        assert db_session.query(GlobalUnsubscribe).count() == 0  # 차단 안 함

    def test_ignores_addresses_not_sent_by_user(self, client, auth_headers, project_id, db_session, monkeypatch):
        u, p, gp = _setup_sent(db_session)
        monkeypatch.setattr(
            bounce_detector, "_fetch_bounces",
            lambda e, pw: [("stranger@other.com", True)],  # 보낸 적 없는 주소
        )
        n = bounce_detector.detect_bounces_for_user(db_session, u.id, "me@gmail.com", "pw")
        assert n == 0  # 오탐 방지

    def test_no_bounces_noop(self, client, auth_headers, project_id, db_session, monkeypatch):
        _setup_sent(db_session)
        monkeypatch.setattr(bounce_detector, "_fetch_bounces", lambda e, pw: [])
        assert bounce_detector.detect_bounces_for_user(db_session, 1, "me@gmail.com", "pw") == 0
