"""정보통신망법 §50 컴플라이언스 — 광고성 이메일 필수 표기 자동화.

- 제목 `(광고)` 표기
- 본문 하단 전송자 정보 + 수신거부 링크 푸터
- 발송 차단 대상 확인 (유저 블랙리스트 + 전역 수신거부 풀)
"""
from sqlalchemy.orm import Session

from app.core.config import settings as app_settings

AD_PREFIX = "(광고) "


def apply_ad_prefix(subject: str, enabled: bool = True) -> str:
    """광고성 메일 제목에 (광고) 표기. 이미 있으면 중복 삽입하지 않음."""
    if not enabled:
        return subject
    if subject.lstrip().startswith("(광고)"):
        return subject
    return f"{AD_PREFIX}{subject}"


def build_unsubscribe_url(tracking_id: str) -> str:
    return f"{app_settings.BASE_URL}/api/t/unsub/{tracking_id}"


def build_compliance_footer(tracking_id: str, sender_info: str | None = None) -> str:
    """전송자 정보 + 수신거부 방법 명시 푸터 HTML."""
    unsub_url = build_unsubscribe_url(tracking_id)
    sender_block = ""
    if sender_info:
        lines = "<br>".join(
            line.strip() for line in sender_info.strip().splitlines() if line.strip()
        )
        sender_block = f'<p style="margin:0 0 6px 0;">{lines}</p>'
    return (
        '<div style="margin-top:32px;padding-top:12px;border-top:1px solid #e5e5e5;'
        'font-size:12px;color:#999;line-height:1.6;">'
        f"{sender_block}"
        f'<p style="margin:0;">본 메일은 영리목적의 광고성 정보를 포함하고 있습니다. '
        f'수신을 원치 않으시면 <a href="{unsub_url}" style="color:#666;">수신거부</a>를 눌러주세요. '
        f"수신거부 시 향후 메일이 발송되지 않습니다.</p>"
        "</div>"
    )


def inject_compliance_footer(html_body: str, footer_html: str) -> str:
    """본문 </body> 직전(없으면 끝)에 푸터 삽입."""
    if "</body>" in html_body:
        return html_body.replace("</body>", f"{footer_html}\n</body>", 1)
    return html_body + footer_html


def build_list_unsubscribe_headers(tracking_id: str) -> dict:
    """RFC 2369 + RFC 8058 One-Click 수신거부 헤더 — Gmail/네이버 스팸 필터 신뢰도 상승."""
    unsub_url = build_unsubscribe_url(tracking_id)
    return {
        "List-Unsubscribe": f"<{unsub_url}>",
        "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
    }


def is_email_suppressed(db: Session, user_id: int, email: str | None) -> bool:
    """발송 금지 대상인지 확인 — 유저 블랙리스트 또는 전역 수신거부 풀."""
    if not email:
        return False
    from app.models.models import Blacklist, GlobalUnsubscribe

    normalized = email.strip().lower()
    blacklisted = (
        db.query(Blacklist.id)
        .filter(Blacklist.user_id == user_id, Blacklist.email.ilike(normalized))
        .first()
    )
    if blacklisted:
        return True
    unsubscribed = (
        db.query(GlobalUnsubscribe.id)
        .filter(GlobalUnsubscribe.email == normalized)
        .first()
    )
    return unsubscribed is not None


def record_unsubscribe(db: Session, tracking_id: str) -> bool:
    """수신거부 처리: 발송 로그로 대상 이메일을 찾아 유저 블랙리스트 + 전역 풀에 등록.

    커밋은 호출자가 수행. 대상을 찾으면 True.
    """
    from app.models.models import Blacklist, EmailLog, GlobalUnsubscribe, Prospect

    log = db.query(EmailLog).filter(EmailLog.tracking_id == tracking_id).first()
    if not log:
        return False
    prospect = db.query(Prospect).filter(Prospect.id == log.prospect_id).first()
    if not prospect or not prospect.email:
        return False

    email = prospect.email.strip().lower()

    existing_bl = (
        db.query(Blacklist)
        .filter(Blacklist.user_id == log.user_id, Blacklist.email.ilike(email))
        .first()
    )
    if not existing_bl:
        db.add(Blacklist(user_id=log.user_id, email=email, reason="수신거부 (이메일 링크)"))

    existing_gu = db.query(GlobalUnsubscribe).filter(GlobalUnsubscribe.email == email).first()
    if not existing_gu:
        db.add(GlobalUnsubscribe(email=email, source_user_id=log.user_id, tracking_id=tracking_id))

    return True
