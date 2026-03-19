import threading
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db, SessionLocal
from app.core.security import decrypt_value, get_current_user
from app.models.models import EmailLog, Prospect, Project, User, UserSettings
from app.services.sender.email import send_email, send_bulk_emails, make_default_email_html

router = APIRouter(
    prefix="/api/projects/{project_id}",
    tags=["email"],
)


class SendEmailResponse(BaseModel):
    message: str
    target_count: int


class TestEmailRequest(BaseModel):
    to_email: Optional[str] = None  # If None, send to user's gmail


class EmailLogResponse(BaseModel):
    id: int
    prospect_id: int
    sent_at: datetime
    status: str
    error_message: Optional[str] = None

    model_config = {"from_attributes": True}


def _get_project_or_404(project_id: int, user_id: int, db: Session) -> Project:
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.user_id == user_id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _get_user_settings_or_error(user_id: int, db: Session) -> UserSettings:
    settings = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
    if not settings or not settings.gmail_email or not settings.gmail_app_password_encrypted:
        raise HTTPException(
            status_code=400,
            detail="Gmail settings not configured. Set up gmail_email and app password in settings first.",
        )
    return settings


def _run_email_sending_in_background(project_id: int, user_id: int):
    db = SessionLocal()
    try:
        settings = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
        project = db.query(Project).filter(Project.id == project_id).first()
        prospects = (
            db.query(Prospect)
            .filter(Prospect.project_id == project_id, Prospect.status == "approved")
            .filter(Prospect.email.isnot(None), Prospect.email != "")
            .all()
        )

        if settings and project and prospects:
            gmail_pw = decrypt_value(settings.gmail_app_password_encrypted)
            send_bulk_emails(
                db=db,
                gmail_email=settings.gmail_email,
                gmail_app_password=gmail_pw,
                prospects=prospects,
                user_id=user_id,
                sender_name=settings.gmail_email.split("@")[0],
                email_template=settings.email_template,
                daily_limit=settings.daily_email_limit,
            )
    except Exception:
        pass
    finally:
        db.close()


@router.post("/send-email", response_model=SendEmailResponse)
def start_email_sending(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_project_or_404(project_id, current_user.id, db)
    _get_user_settings_or_error(current_user.id, db)

    target_count = (
        db.query(Prospect)
        .filter(
            Prospect.project_id == project_id,
            Prospect.status == "approved",
            Prospect.email.isnot(None),
            Prospect.email != "",
        )
        .count()
    )

    if target_count == 0:
        raise HTTPException(
            status_code=400,
            detail="No approved prospects with email addresses found",
        )

    thread = threading.Thread(
        target=_run_email_sending_in_background,
        args=(project_id, current_user.id),
        daemon=True,
    )
    thread.start()

    return SendEmailResponse(
        message=f"Email sending started for {target_count} prospects",
        target_count=target_count,
    )


@router.post("/send-test-email", response_model=dict)
def send_test_email(
    project_id: int,
    req: TestEmailRequest = TestEmailRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_project_or_404(project_id, current_user.id, db)
    settings = _get_user_settings_or_error(current_user.id, db)

    to_email = req.to_email or settings.gmail_email
    gmail_pw = decrypt_value(settings.gmail_app_password_encrypted)

    html_body = make_default_email_html(
        company_name="Test Company",
        category="Test Category",
        sender_name=current_user.name,
    )

    success = send_email(
        gmail_email=settings.gmail_email,
        gmail_app_password=gmail_pw,
        to_email=to_email,
        subject="[Test] Outreach Email Test",
        html_body=html_body,
    )

    if success:
        return {"message": f"Test email sent successfully to {to_email}"}
    else:
        raise HTTPException(status_code=500, detail="Failed to send test email")


@router.get("/email-logs", response_model=list[EmailLogResponse])
def get_email_logs(
    project_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_project_or_404(project_id, current_user.id, db)

    logs = (
        db.query(EmailLog)
        .join(Prospect, EmailLog.prospect_id == Prospect.id)
        .filter(
            Prospect.project_id == project_id,
            EmailLog.user_id == current_user.id,
        )
        .order_by(EmailLog.sent_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return logs
