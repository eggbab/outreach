"""미팅 확인·리마인더 메일 테스트 (SMTP는 모킹)."""
from datetime import datetime, timedelta, timezone

from app.models.models import Meeting, User
from app.services import meeting_notify


def _host(db):
    u = User(email="host@x.com", name="담당자", password_hash="x", credits=10)
    db.add(u)
    db.flush()
    return u


class TestBookingConfirmation:
    def test_confirmation_sent_to_booker_and_host(self, db_session, monkeypatch):
        host = _host(db_session)
        m = Meeting(
            user_id=host.id, booking_code="bc1", title="상담",
            scheduled_at=datetime(2026, 9, 1, 14, 0),
            booker_name="김고객", booker_email="booker@corp.com",
        )
        db_session.add(m)
        db_session.commit()

        calls = []
        monkeypatch.setattr(
            meeting_notify, "_send_via_best_channel",
            lambda db, uid, to, subj, html: calls.append((to, subj)) or True,
        )
        meeting_notify.send_booking_confirmation(db_session, m)

        recipients = [c[0] for c in calls]
        assert "booker@corp.com" in recipients  # 예약자
        assert "host@x.com" in recipients       # 호스트
        assert any("미팅 예약 확인" in c[1] for c in calls)

    def test_no_booker_email_only_host(self, db_session, monkeypatch):
        host = _host(db_session)
        m = Meeting(user_id=host.id, booking_code="bc2", title="상담",
                    scheduled_at=datetime(2026, 9, 1, 14, 0), booker_name="김고객")
        db_session.add(m)
        db_session.commit()
        calls = []
        monkeypatch.setattr(meeting_notify, "_send_via_best_channel",
                            lambda db, uid, to, subj, html: calls.append(to) or True)
        meeting_notify.send_booking_confirmation(db_session, m)
        assert calls == ["host@x.com"]


class TestReminders:
    def test_reminder_sent_within_24h(self, db_session, monkeypatch):
        host = _host(db_session)
        soon = (datetime.now(timezone.utc) + timedelta(hours=12)).replace(tzinfo=None)
        m = Meeting(user_id=host.id, booking_code="r1", title="미팅",
                    scheduled_at=soon, booker_email="b@corp.com")
        db_session.add(m)
        db_session.commit()

        calls = []
        monkeypatch.setattr(meeting_notify, "_send_via_best_channel",
                            lambda db, uid, to, subj, html: calls.append(subj) or True)
        n = meeting_notify.send_due_reminders(db_session)
        assert n == 1
        db_session.refresh(m)
        assert m.reminder_sent_at is not None
        # 두 번째 호출은 이미 발송됨 → 재발송 안 함
        assert meeting_notify.send_due_reminders(db_session) == 0

    def test_reminder_skips_far_future(self, db_session, monkeypatch):
        host = _host(db_session)
        far = (datetime.now(timezone.utc) + timedelta(days=5)).replace(tzinfo=None)
        m = Meeting(user_id=host.id, booking_code="r2", title="미팅",
                    scheduled_at=far, booker_email="b@corp.com")
        db_session.add(m)
        db_session.commit()
        monkeypatch.setattr(meeting_notify, "_send_via_best_channel",
                            lambda *a, **k: True)
        assert meeting_notify.send_due_reminders(db_session) == 0
        db_session.refresh(m)
        assert m.reminder_sent_at is None
