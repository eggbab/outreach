import logging
import re
import smtplib
import time
import uuid
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional
from urllib.parse import quote

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import EmailLog

logger = logging.getLogger(__name__)


def send_system_email(to_email: str, subject: str, body: str) -> bool:
    """
    시스템 메일(비밀번호 재설정 등) 발송.
    환경변수 SYSTEM_GMAIL_EMAIL / SYSTEM_GMAIL_APP_PASSWORD를 사용.
    설정이 없으면 False 반환 (호출자가 로그로 fallback).
    """
    import os
    sender = os.getenv("SYSTEM_GMAIL_EMAIL", "")
    app_pw = os.getenv("SYSTEM_GMAIL_APP_PASSWORD", "")
    if not sender or not app_pw:
        logger.warning("SYSTEM_GMAIL_EMAIL/PASSWORD 미설정 — 시스템 메일 발송 스킵")
        return False

    return send_email(
        gmail_email=sender,
        gmail_app_password=app_pw,
        to_email=to_email,
        subject=subject,
        html_body=body.replace("\n", "<br>"),
    )


def send_email(
    gmail_email: str,
    gmail_app_password: str,
    to_email: str,
    subject: str,
    html_body: str,
    extra_headers: Optional[dict] = None,
) -> bool:
    """Send a single email via Gmail SMTP. Returns True on success."""
    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = gmail_email
        msg["To"] = to_email
        msg["Subject"] = subject
        for key, value in (extra_headers or {}).items():
            msg[key] = value

        msg.attach(MIMEText(html_body, "html", "utf-8"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as server:
            server.login(gmail_email, gmail_app_password)
            server.sendmail(gmail_email, to_email, msg.as_string())

        logger.info(f"Email sent successfully to {to_email}")
        return True

    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False


def render_template(text: str, company_name: str, category: str, sender_name: str) -> str:
    """변수 치환 — {name}, {company_name}, {category}, {sender_name} 모두 지원."""
    if not text:
        return text
    out = text
    for old, new in [
        ("{name}", company_name),
        ("{{name}}", company_name),
        ("{company_name}", company_name),
        ("{{company_name}}", company_name),
        ("{category}", category),
        ("{{category}}", category),
        ("{sender_name}", sender_name),
        ("{{sender_name}}", sender_name),
    ]:
        out = out.replace(old, new)
    return out


def make_default_email_html(
    company_name: str,
    category: str,
    sender_name: str,
    custom_template: Optional[str] = None,
) -> str:
    """
    Generate the outreach email HTML body.
    If custom_template is provided, use it with variable substitution.
    Otherwise use a generic outreach template.
    """
    if custom_template:
        return render_template(custom_template, company_name, category, sender_name)

    # Generic outreach email template (Korean)
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif; line-height: 1.7; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ font-size: 18px; font-weight: bold; margin-bottom: 16px; }}
        .body-text {{ font-size: 15px; margin-bottom: 12px; }}
        .signature {{ margin-top: 24px; font-size: 14px; color: #666; }}
    </style>
</head>
<body>
    <div class="container">
        <p class="header">안녕하세요, {company_name} 담당자님!</p>

        <p class="body-text">
            <strong>{category}</strong> 분야에서 활동하고 계신 것을 보고 연락드립니다.
        </p>

        <p class="body-text">
            저희는 해당 업종의 수천 명의 활성 회원이 있는 커뮤니티 플랫폼을 운영하고 있습니다.
            귀사의 브랜드 인지도를 높이고 잠재 고객과 연결해드릴 수 있는 방법을 함께 모색하고 싶습니다.
        </p>

        <p class="body-text">
            짧은 통화나 미팅을 통해 협업 가능성을 논의해보실 의향이 있으신지요?
            현재 파트너분들의 성과 사례도 공유드릴 수 있습니다.
        </p>

        <p class="body-text">
            회신 기다리겠습니다. 감사합니다!
        </p>

        <div class="signature">
            <p>{sender_name} 드림</p>
        </div>
    </div>
</body>
</html>"""


def send_bulk_emails(
    db: Session,
    gmail_email: str,
    gmail_app_password: str,
    prospects: list,
    user_id: int,
    sender_name: str,
    email_template: Optional[str] = None,
    email_subject: Optional[str] = None,
    daily_limit: int = 80,
    min_delay: int = 30,
    max_delay: int = 120,
    job=None,
    ad_prefix_enabled: bool = True,
    sender_info: Optional[str] = None,
) -> dict:
    """
    Send emails to a list of approved prospects with rate limiting.
    매 건마다 크레딧 차감. 잔액 부족 시 즉시 중단.
    블랙리스트/전역 수신거부 대상은 건너뜀 (과금 없음).
    """
    import random
    from datetime import datetime, timezone

    from app.core.plans import CREDIT_COSTS, deduct_credits, check_credits
    from app.models.models import GlobalProspect
    from app.services.compliance import (
        apply_ad_prefix,
        build_compliance_footer,
        build_list_unsubscribe_headers,
        inject_compliance_footer,
        is_email_suppressed,
    )

    sent = 0
    failed = 0
    skipped = 0

    for prospect in prospects[:daily_limit]:
        if not prospect.email:
            continue

        # ─── 수신거부/블랙리스트 차단 (정보통신망법 §50) ───
        if is_email_suppressed(db, user_id, prospect.email):
            skipped += 1
            continue

        # ─── MX 검증 실패 주소 스킵 — 반송률 상승은 Gmail 평판 하락 직행 ───
        if getattr(prospect, "email_valid", None) is False:
            skipped += 1
            continue

        # ─── 크레딧 사전 확인 ─── 부족하면 중단
        check = check_credits(db, user_id, "email", 1)
        if not check["allowed"]:
            if job:
                job.error = f"크레딧 부족 — {sent}건 발송 후 중단 (잔액: {check.get('balance', 0)})"
                db.commit()
            break

        # Update job progress
        if job:
            job.current_email = prospect.email
            job.sent_count = sent
            job.failed_count = failed
            db.commit()

        company_name = prospect.name or "고객"
        category = prospect.category or "귀사 업종"

        # Generate unique tracking ID for this email
        tracking_id = uuid.uuid4().hex

        html_body = make_default_email_html(
            company_name=company_name,
            category=category,
            sender_name=sender_name,
            custom_template=email_template,
        )

        # 스핀택스 변형 — 수신자마다 문구를 조금씩 다르게(동일 문구 대량발송 = 스팸 패턴)
        from app.services.dm_compose import expand_spintax
        html_body = expand_spintax(html_body, prospect.id)

        # Wrap links for click tracking
        def _wrap_link(match):
            original_url = match.group(1)
            # Skip tracking URLs and mailto links
            if '/api/t/' in original_url or original_url.startswith('mailto:'):
                return match.group(0)
            encoded = quote(original_url, safe='')
            return f'href="{settings.BASE_URL}/api/t/click/{tracking_id}?url={encoded}"'

        html_body = re.sub(r'href="(https?://[^"]+)"', _wrap_link, html_body)

        # Inject tracking pixel before </body>
        tracking_pixel = (
            f'<img src="{settings.BASE_URL}/api/t/open/{tracking_id}" '
            f'width="1" height="1" style="display:none">'
        )
        # 컴플라이언스 푸터 (전송자 정보 + 수신거부 링크) — 픽셀보다 먼저 삽입
        footer = build_compliance_footer(tracking_id, sender_info)
        html_body = inject_compliance_footer(html_body, footer)

        if "</body>" in html_body:
            html_body = html_body.replace("</body>", f"{tracking_pixel}\n</body>")
        else:
            html_body += tracking_pixel

        # 사용자 설정 제목 (없으면 한국어 기본) + 변수 치환 + 스핀택스 변형 + (광고) 표기
        raw_subject = email_subject or "안녕하세요, {company_name}님께 제안 드립니다"
        subject = render_template(raw_subject, company_name, category, sender_name)
        subject = expand_spintax(subject, prospect.id)
        subject = apply_ad_prefix(subject, ad_prefix_enabled)

        success = send_email(
            gmail_email=gmail_email,
            gmail_app_password=gmail_app_password,
            to_email=prospect.email,
            subject=subject,
            html_body=html_body,
            extra_headers=build_list_unsubscribe_headers(tracking_id),
        )

        log = EmailLog(
            prospect_id=prospect.id,
            user_id=user_id,
            status="success" if success else "failed",
            error_message=None if success else "SMTP send failed",
            tracking_id=tracking_id,
        )
        db.add(log)

        if success:
            prospect.status = "email_sent"
            sent += 1
            # 성공한 발송만 크레딧 차감 — 차감 실패(동시 사용 등으로 잔액 소진) 시 중단
            remaining = deduct_credits(db, user_id, CREDIT_COSTS["email"], f"이메일 발송: {prospect.email}")
            if remaining is None:
                logger.warning(f"크레딧 차감 실패 (user={user_id}) — 발송 중단")
                if job:
                    job.error = f"크레딧 부족 — {sent}건 발송 후 중단"
                db.commit()
                break
            # SMTP 수락 = 주소 실존의 약한 증거 → 전역 풀 검증 점수 갱신
            if prospect.global_prospect_id:
                gp = db.query(GlobalProspect).filter(
                    GlobalProspect.id == prospect.global_prospect_id
                ).first()
                if gp:
                    gp.email_validity_score = max(gp.email_validity_score or 0.0, 0.5)
                    gp.last_verified_at = datetime.now(timezone.utc)
        else:
            failed += 1

        db.commit()

        # 사용자 설정 간격 (기본 30~120초)
        delay = random.uniform(min_delay, max_delay)
        time.sleep(delay)

    return {"sent": sent, "failed": failed, "skipped": skipped, "total": sent + failed}
