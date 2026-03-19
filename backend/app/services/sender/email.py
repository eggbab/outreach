import logging
import smtplib
import time
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from sqlalchemy.orm import Session

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
        # Replace template variables
        html = custom_template
        html = html.replace("{{company_name}}", company_name)
        html = html.replace("{{category}}", category)
        html = html.replace("{{sender_name}}", sender_name)
        return html

    # Generic outreach email template
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ font-size: 18px; font-weight: bold; margin-bottom: 16px; }}
        .body-text {{ font-size: 15px; margin-bottom: 12px; }}
        .signature {{ margin-top: 24px; font-size: 14px; color: #666; }}
    </style>
</head>
<body>
    <div class="container">
        <p class="header">Hello, {company_name}!</p>

        <p class="body-text">
            I came across your business in the <strong>{category}</strong> space
            and wanted to reach out about a potential partnership opportunity.
        </p>

        <p class="body-text">
            We operate a community platform with thousands of active members in your industry.
            We'd love to explore how we can help increase your brand's visibility
            and connect you with potential customers.
        </p>

        <p class="body-text">
            Would you be open to a brief conversation about how we could work together?
            I'd be happy to share more details about our platform and the results
            our current partners are seeing.
        </p>

        <p class="body-text">
            Looking forward to hearing from you!
        </p>

        <div class="signature">
            <p>Best regards,<br><strong>{sender_name}</strong></p>
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
) -> dict:
    """
    Send emails to a list of approved prospects with rate limiting.
    Returns summary stats.
    """
    import random

    sent = 0
    failed = 0

    for prospect in prospects[:daily_limit]:
        if not prospect.email:
            continue

        company_name = prospect.name or "Business"
        category = prospect.category or "your industry"

        html_body = make_default_email_html(
            company_name=company_name,
            category=category,
            sender_name=sender_name,
            custom_template=email_template,
        )

        subject = f"Partnership Opportunity - {company_name}"

        success = send_email(
            gmail_email=gmail_email,
            gmail_app_password=gmail_app_password,
            to_email=prospect.email,
            subject=subject,
            html_body=html_body,
        )

        # Log the result
        log = EmailLog(
            prospect_id=prospect.id,
            user_id=user_id,
            status="success" if success else "failed",
            error_message=None if success else "SMTP send failed",
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
