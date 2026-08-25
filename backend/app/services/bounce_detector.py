"""이메일 반송(바운스) 감지 — Gmail IMAP으로 mailer-daemon 반송 메일을 읽어 처리.

반송 메일 특징:
- 발신자가 mailer-daemon@/postmaster@ 등
- 본문/헤더에 원래 수신 실패한 주소가 포함
- 하드 바운스(존재하지 않는 주소, 550 5.1.1 등)는 재발송 금지 대상

처리:
- 해당 Prospect.email_valid = False (재발송 시 스킵됨)
- GlobalProspect.email_validity_score 하향 + 전역 수신거부 풀 등록(하드 바운스)
- 소비된 크레딧 환불 (tx_type='refund') — 도달 못한 발송은 과금 취소

reply_detector와 동일한 per-user IMAP 패턴. Gmail 앱 비밀번호 재사용.
"""
import email as email_lib
import imaplib
import logging
import re
from datetime import datetime, timedelta, timezone
from email.utils import parseaddr

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

IMAP_HOST = "imap.gmail.com"
LOOKBACK_DAYS = 3

# 반송 발신자 패턴
_BOUNCE_SENDERS = re.compile(r"(mailer-daemon|postmaster|mail delivery|delivery status)", re.I)
# 하드 바운스 상태코드 (영구 실패) — 5.x.x
_HARD_BOUNCE = re.compile(r"\b5\.\d\.\d\b|status:\s*5\.\d\.\d|550[ -]5\.\d\.\d", re.I)
_EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")


def _fetch_bounces(gmail_email: str, gmail_app_password: str) -> list[tuple[str, bool]]:
    """최근 반송 메일에서 (실패한 수신 주소, 하드바운스 여부) 목록 추출."""
    since = (datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)).strftime("%d-%b-%Y")
    out: list[tuple[str, bool]] = []

    imap = imaplib.IMAP4_SSL(IMAP_HOST, timeout=30)
    try:
        imap.login(gmail_email, gmail_app_password)
        imap.select("INBOX", readonly=True)
        status, data = imap.search(None, f'(SINCE "{since}")')
        if status != "OK" or not data or not data[0]:
            return out

        for msg_id in data[0].split()[-300:]:
            status, msg_data = imap.fetch(msg_id, "(RFC822.HEADER BODY.PEEK[TEXT])")
            if status != "OK" or not msg_data:
                continue
            raw = b"".join(
                part[1] for part in msg_data
                if isinstance(part, tuple) and isinstance(part[1], (bytes, bytearray))
            )
            if not raw:
                continue
            msg = email_lib.message_from_bytes(raw)
            _, from_addr = parseaddr(msg.get("From", ""))
            subject = msg.get("Subject", "")
            if not (_BOUNCE_SENDERS.search(from_addr or "") or _BOUNCE_SENDERS.search(subject or "")):
                continue

            body = raw.decode("utf-8", errors="ignore")
            is_hard = bool(_HARD_BOUNCE.search(body))
            # 본문에서 실패 주소 후보 추출 (자기 자신·데몬 주소 제외)
            for cand in _EMAIL_RE.findall(body):
                c = cand.strip().lower()
                if c == gmail_email.lower() or _BOUNCE_SENDERS.search(c):
                    continue
                out.append((c, is_hard))
    finally:
        try:
            imap.logout()
        except Exception:
            pass

    return out


def detect_bounces_for_user(db: Session, user_id: int, gmail_email: str, gmail_app_password: str) -> int:
    """한 유저의 반송 메일을 처리. 처리한 잠재고객 수 반환."""
    from app.core.plans import CREDIT_COSTS, add_credits
    from app.models.models import (
        EmailLog, GlobalProspect, GlobalUnsubscribe, Project, Prospect,
    )

    bounces = _fetch_bounces(gmail_email, gmail_app_password)
    if not bounces:
        return 0

    # 이 유저가 실제로 발송한 주소만 대상 (오탐 방지)
    sent_emails = {
        (row[0] or "").strip().lower()
        for row in db.query(Prospect.email)
        .join(Project, Prospect.project_id == Project.id)
        .join(EmailLog, EmailLog.prospect_id == Prospect.id)
        .filter(Project.user_id == user_id, EmailLog.status == "success")
        .distinct()
        .all()
        if row[0]
    }

    now = datetime.now(timezone.utc)
    processed = 0
    seen = set()
    for addr, is_hard in bounces:
        if addr not in sent_emails or addr in seen:
            continue
        seen.add(addr)

        prospects = (
            db.query(Prospect)
            .join(Project, Prospect.project_id == Project.id)
            .filter(Project.user_id == user_id, Prospect.email.ilike(addr))
            .all()
        )
        if not prospects:
            continue
        processed += 1

        for p in prospects:
            p.email_valid = False  # 재발송 시 스킵
            if p.global_prospect_id:
                gp = db.query(GlobalProspect).filter(GlobalProspect.id == p.global_prospect_id).first()
                if gp:
                    gp.email_validity_score = 0.0 if is_hard else min(gp.email_validity_score or 0.0, 0.1)
                    gp.last_verified_at = now.replace(tzinfo=None)

            # 하드 바운스만 크레딧 환불 (성공 발송 EmailLog당 이메일 비용) + 전역 차단
            if is_hard:
                success_logs = (
                    db.query(EmailLog)
                    .filter(EmailLog.prospect_id == p.id, EmailLog.status == "success")
                    .count()
                )
                if success_logs:
                    add_credits(
                        db, user_id, CREDIT_COSTS["email"] * success_logs,
                        f"반송 환불: {addr}", tx_type="refund",
                    )
                if not db.query(GlobalUnsubscribe).filter(GlobalUnsubscribe.email == addr).first():
                    db.add(GlobalUnsubscribe(email=addr, source_user_id=user_id))

    return processed


def detect_bounces_all_users(db: Session) -> int:
    """Gmail 설정이 있고 최근 발송한 모든 유저의 반송을 처리."""
    from app.core.security import decrypt_value
    from app.models.models import EmailLog, UserSettings

    cutoff = datetime.now(timezone.utc) - timedelta(days=14)
    recent = {
        r[0] for r in db.query(EmailLog.user_id)
        .filter(EmailLog.sent_at >= cutoff.replace(tzinfo=None), EmailLog.status == "success")
        .distinct().all()
    }
    if not recent:
        return 0

    total = 0
    rows = (
        db.query(UserSettings)
        .filter(
            UserSettings.user_id.in_(recent),
            UserSettings.gmail_email.isnot(None),
            UserSettings.gmail_app_password_encrypted.isnot(None),
        )
        .all()
    )
    for s in rows:
        try:
            pw = decrypt_value(s.gmail_app_password_encrypted)
            n = detect_bounces_for_user(db, s.user_id, s.gmail_email, pw)
            if n:
                db.commit()
                logger.info(f"바운스 감지: user={s.user_id}, {n}건")
                total += n
        except Exception as e:
            logger.warning(f"바운스 감지 실패 (user={s.user_id}): {e}")
            db.rollback()
    return total
