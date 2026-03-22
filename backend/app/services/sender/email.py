import logging
import smtplib
import time
import uuid
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import EmailLog, Prospect

logger = logging.getLogger(__name__)


def send_email(
    gmail_email: str,
    gmail_app_password: str,
    to_email: str,
    subject: str,
    html_body: str,
) -> bool:
    """Send a single email via Gmail SMTP. Returns True on success."""
    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = gmail_email
        msg["To"] = to_email
        msg["Subject"] = subject

        msg.attach(MIMEText(html_body, "html", "utf-8"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as server:
            server.login(gmail_email, gmail_app_password)
            server.sendmail(gmail_email, to_email, msg.as_string())

        logger.info(f"Email sent successfully to {to_email}")
        return True

    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False


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
        # Replace template variables — support both {var} and {{var}} formats
        html = custom_template
        for old, new in [
            ("{company_name}", company_name),
            ("{{company_name}}", company_name),
            ("{category}", category),
            ("{{category}}", category),
            ("{sender_name}", sender_name),
            ("{{sender_name}}", sender_name),
        ]:
            html = html.replace(old, new)
        return html

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
    daily_limit: int = 80,
    job=None,
) -> dict:
    """
    Send emails to a list of approved prospects with rate limiting.
    Returns summary stats. Optionally updates an EmailSendJob for progress tracking.
    """
    import random

    sent = 0
    failed = 0

    for prospect in prospects[:daily_limit]:
        if not prospect.email:
            continue

        # Update job progress
        if job:
            job.current_email = prospect.email
            job.sent_count = sent
            job.failed_count = failed
            db.commit()

        company_name = prospect.name or "Business"
        category = prospect.category or "your industry"

        # Generate unique tracking ID for this email
        tracking_id = uuid.uuid4().hex

        html_body = make_default_email_html(
            company_name=company_name,
            category=category,
            sender_name=sender_name,
            custom_template=email_template,
        )

        # Inject tracking pixel before </body>
        tracking_pixel = (
            f'<img src="{settings.BASE_URL}/api/t/open/{tracking_id}" '
            f'width="1" height="1" style="display:none">'
        )
        if "</body>" in html_body:
            html_body = html_body.replace("</body>", f"{tracking_pixel}\n</body>")
        else:
            html_body += tracking_pixel

        subject = f"Partnership Opportunity - {company_name}"

        success = send_email(
            gmail_email=gmail_email,
            gmail_app_password=gmail_app_password,
            to_email=prospect.email,
            subject=subject,
            html_body=html_body,
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
        else:
            failed += 1

        db.commit()

        # Rate limiting: 25-45 seconds between sends
        delay = random.uniform(25, 45)
        time.sleep(delay)

    return {"sent": sent, "failed": failed, "total": sent + failed}
