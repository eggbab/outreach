"""미팅 예약 확인 + 리마인더 메일.

발송 계정 우선순위:
1. 호스트(user)의 Gmail 설정이 있으면 그 계정으로 (예약자 입장에서 발신자가 담당자)
2. 없으면 시스템 메일(SYSTEM_GMAIL_*)로 폴백
Gmail 설정도 시스템 메일도 없으면 조용히 스킵 (예약 자체는 성공).
"""
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def _fmt_kst(dt: datetime) -> str:
    """미팅 시각을 사람이 읽는 한국어로. (naive-UTC 저장이지만 표시는 그대로 — 사용자가 입력한 값)"""
    try:
        return dt.strftime("%Y년 %m월 %d일 %H:%M")
    except Exception:
        return str(dt)


def _send_via_best_channel(db, host_user_id: int, to_email: str, subject: str, html: str) -> bool:
    from app.core.security import decrypt_value
    from app.models.models import UserSettings
    from app.services.sender.email import send_email, send_system_email

    settings = db.query(UserSettings).filter(UserSettings.user_id == host_user_id).first()
    if settings and settings.gmail_email and settings.gmail_app_password_encrypted:
        try:
            pw = decrypt_value(settings.gmail_app_password_encrypted)
            return send_email(
                gmail_email=settings.gmail_email, gmail_app_password=pw,
                to_email=to_email, subject=subject, html_body=html,
            )
        except Exception as e:
            logger.warning(f"미팅 메일(호스트 Gmail) 실패, 시스템 메일로 폴백: {e}")
    return send_system_email(to_email, subject, html)


def send_booking_confirmation(db, meeting) -> None:
    """예약 직후 예약자(+호스트)에게 확인 메일."""
    from app.models.models import User

    host = db.query(User).filter(User.id == meeting.user_id).first()
    host_name = host.name if host else "담당자"
    when = _fmt_kst(meeting.scheduled_at)

    if meeting.booker_email:
        html = (
            f"<p>{meeting.booker_name or '고객'}님, 미팅이 예약되었습니다.</p>"
            f"<ul>"
            f"<li><b>일정</b>: {when}</li>"
            f"<li><b>주제</b>: {meeting.title}</li>"
            f"<li><b>담당</b>: {host_name}</li>"
            f"</ul>"
            f"<p>변경이 필요하시면 이 메일에 회신해주세요.</p>"
        )
        _send_via_best_channel(db, meeting.user_id, meeting.booker_email,
                               f"[미팅 예약 확인] {meeting.title} — {when}", html)

    # 호스트에게도 알림 (Gmail 설정된 본인 주소로)
    if host and host.email:
        html = (
            f"<p>새 미팅이 예약되었습니다.</p>"
            f"<ul>"
            f"<li><b>일정</b>: {when}</li>"
            f"<li><b>주제</b>: {meeting.title}</li>"
            f"<li><b>예약자</b>: {meeting.booker_name or '-'} ({meeting.booker_email or '-'})</li>"
            f"</ul>"
        )
        _send_via_best_channel(db, meeting.user_id, host.email,
                               f"[새 미팅] {meeting.title} — {when}", html)


def send_due_reminders(db) -> int:
    """24시간 이내 예정이면서 아직 리마인더 안 보낸 미팅에 리마인더 발송. 발송 건수 반환."""
    from datetime import timedelta, timezone
    from app.models.models import Meeting

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    window_end = now + timedelta(hours=24)

    due = (
        db.query(Meeting)
        .filter(
            Meeting.status == "scheduled",
            Meeting.reminder_sent_at.is_(None),
            Meeting.scheduled_at > now,
            Meeting.scheduled_at <= window_end,
            Meeting.booker_email.isnot(None),
        )
        .limit(100)
        .all()
    )

    sent = 0
    for m in due:
        when = _fmt_kst(m.scheduled_at)
        html = (
            f"<p>{m.booker_name or '고객'}님, 내일 미팅 일정을 안내드립니다.</p>"
            f"<ul><li><b>일정</b>: {when}</li><li><b>주제</b>: {m.title}</li></ul>"
            f"<p>참석이 어려우시면 미리 알려주세요.</p>"
        )
        try:
            _send_via_best_channel(db, m.user_id, m.booker_email,
                                   f"[미팅 리마인더] 내일 {when}", html)
            m.reminder_sent_at = now
            sent += 1
        except Exception as e:
            logger.warning(f"미팅 리마인더 실패 (meeting={m.id}): {e}")

    if sent:
        db.commit()
        logger.info(f"미팅 리마인더 {sent}건 발송")
    return sent
