"""Gmail IMAP 답장 감지 — 발송한 잠재고객의 회신을 자동 인식.

- 잠재고객 상태를 'replied'로 갱신하고 진행 중인 시퀀스를 중단시킨다.
- GlobalProspect.times_replied를 올려 전역 품질 점수(데이터 해자)에 반영한다.
- Gmail 앱 비밀번호(IMAP)를 그대로 재사용 — 별도 설정 불필요.
"""
import email as email_lib
import imaplib
import logging
from datetime import datetime, timedelta, timezone
from email.utils import parseaddr

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

IMAP_HOST = "imap.gmail.com"
LOOKBACK_DAYS = 3  # 매 폴링마다 최근 3일치만 조회 (idempotent — replied는 재처리 안 함)


def _fetch_recent_senders(gmail_email: str, gmail_app_password: str) -> set[str]:
    """받은편지함에서 최근 LOOKBACK_DAYS일간의 발신자 주소 집합을 수집."""
    since = (datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)).strftime("%d-%b-%Y")
    senders: set[str] = set()

    imap = imaplib.IMAP4_SSL(IMAP_HOST, timeout=30)
    try:
        imap.login(gmail_email, gmail_app_password)
        imap.select("INBOX", readonly=True)
        status, data = imap.search(None, f'(SINCE "{since}")')
        if status != "OK" or not data or not data[0]:
            return senders

        message_ids = data[0].split()
        # 폭주 방지 — 한 번에 최대 300통까지만 헤더 조회
        for msg_id in message_ids[-300:]:
            status, msg_data = imap.fetch(msg_id, "(BODY.PEEK[HEADER.FIELDS (FROM)])")
            if status != "OK" or not msg_data or not msg_data[0]:
                continue
            raw = msg_data[0][1]
            if not isinstance(raw, (bytes, bytearray)):
                continue
            header = email_lib.message_from_bytes(raw)
            _, addr = parseaddr(header.get("From", ""))
            if addr:
                senders.add(addr.strip().lower())
    finally:
        try:
            imap.logout()
        except Exception:
            pass

    return senders


def detect_replies_for_user(db: Session, user_id: int, gmail_email: str, gmail_app_password: str) -> int:
    """한 유저의 받은편지함을 확인해 답장을 감지. 감지된 잠재고객 수를 반환."""
    from app.models.models import (
        EmailLog, GlobalProspect, Project, Prospect, SequenceEnrollment,
    )

    # 이 유저가 이메일을 보낸 (아직 replied 아닌) 잠재고객
    candidates = (
        db.query(Prospect)
        .join(Project, Prospect.project_id == Project.id)
        .filter(
            Project.user_id == user_id,
            Prospect.email.isnot(None),
            Prospect.email != "",
            Prospect.status.in_(["email_sent", "approved", "dm_sent"]),
        )
        .join(EmailLog, EmailLog.prospect_id == Prospect.id)
        .filter(EmailLog.status == "success")
        .distinct()
        .all()
    )
    if not candidates:
        return 0

    senders = _fetch_recent_senders(gmail_email, gmail_app_password)
    if not senders:
        return 0

    now = datetime.now(timezone.utc)
    detected = 0
    for prospect in candidates:
        if prospect.email.strip().lower() not in senders:
            continue

        prospect.status = "replied"
        detected += 1

        last_log = (
            db.query(EmailLog)
            .filter(EmailLog.prospect_id == prospect.id, EmailLog.status == "success")
            .order_by(EmailLog.sent_at.desc())
            .first()
        )
        if last_log and last_log.replied_at is None:
            last_log.replied_at = now

        # 진행 중인 시퀀스 중단 — 답장한 고객에게 후속 메일 금지
        db.query(SequenceEnrollment).filter(
            SequenceEnrollment.prospect_id == prospect.id,
            SequenceEnrollment.status == "active",
        ).update({"status": "stopped"}, synchronize_session=False)

        # 전역 풀 품질 반영 — 답장은 최상위 신호
        if prospect.global_prospect_id:
            gp = db.query(GlobalProspect).filter(
                GlobalProspect.id == prospect.global_prospect_id
            ).first()
            if gp:
                gp.times_replied = (gp.times_replied or 0) + 1
                gp.email_validity_score = 1.0
                gp.last_verified_at = now

    return detected


def detect_replies_all_users(db: Session) -> int:
    """Gmail 설정이 있고 최근 발송 이력이 있는 모든 유저의 답장을 감지."""
    from app.core.security import decrypt_value
    from app.models.models import EmailLog, UserSettings

    cutoff = datetime.now(timezone.utc) - timedelta(days=14)
    recent_sender_ids = {
        row[0]
        for row in db.query(EmailLog.user_id)
        .filter(EmailLog.sent_at >= cutoff.replace(tzinfo=None), EmailLog.status == "success")
        .distinct()
        .all()
    }
    if not recent_sender_ids:
        return 0

    total = 0
    settings_rows = (
        db.query(UserSettings)
        .filter(
            UserSettings.user_id.in_(recent_sender_ids),
            UserSettings.gmail_email.isnot(None),
            UserSettings.gmail_app_password_encrypted.isnot(None),
        )
        .all()
    )
    for settings in settings_rows:
        try:
            pw = decrypt_value(settings.gmail_app_password_encrypted)
            detected = detect_replies_for_user(db, settings.user_id, settings.gmail_email, pw)
            if detected:
                db.commit()
                logger.info(f"답장 감지: user={settings.user_id}, {detected}건")
                total += detected
        except Exception as e:
            # IMAP 미활성/비밀번호 오류 등 — 유저별 실패는 전체를 막지 않음
            logger.warning(f"답장 감지 실패 (user={settings.user_id}): {e}")
            db.rollback()

    return total
