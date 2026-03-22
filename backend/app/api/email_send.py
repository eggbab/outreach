import logging
import threading
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

limiter = Limiter(key_func=get_remote_address)

from app.core.database import get_db, SessionLocal
from app.core.security import decrypt_value, get_current_user
from app.models.models import EmailLog, EmailSendJob, Prospect, Project, User, UserSettings
from app.services.sender.email import send_email, send_bulk_emails, make_default_email_html

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/projects/{project_id}",
    tags=["email"],
)


class SendEmailResponse(BaseModel):
    message: str
    target_count: int


class SendStatusResponse(BaseModel):
    status: str  # idle, running, completed, failed
    total: int = 0
    sent: int = 0
    failed: int = 0
    current_email: Optional[str] = None
    error: Optional[str] = None


class TestEmailRequest(BaseModel):
    to_email: Optional[str] = None


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

        job = (
            db.query(EmailSendJob)
            .filter(EmailSendJob.project_id == project_id, EmailSendJob.user_id == user_id, EmailSendJob.status == "running")
            .order_by(EmailSendJob.started_at.desc())
            .first()
        )

        if settings and project and prospects and job:
            gmail_pw = decrypt_value(settings.gmail_app_password_encrypted)
            result = send_bulk_emails(
                db=db,
                gmail_email=settings.gmail_email,
                gmail_app_password=gmail_pw,
                prospects=prospects,
                user_id=user_id,
                sender_name=settings.gmail_email.split("@")[0],
                email_template=settings.email_template,
                daily_limit=settings.daily_email_limit,
                job=job,
            )
            job.status = "completed"
            job.sent_count = result["sent"]
            job.failed_count = result["failed"]
            job.current_email = None
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
    except Exception as e:
        logger.error(f"Email sending failed: {e}")
        if job:
            job.status = "failed"
            job.error = str(e)
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
    finally:
        db.close()


@router.post("/send-email", response_model=SendEmailResponse)
@limiter.limit("3/minute")
def start_email_sending(
    request: Request,
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_project_or_404(project_id, current_user.id, db)
    _get_user_settings_or_error(current_user.id, db)

    # Check usage limit
    from app.core.plans import check_usage_limit, deduct_credits
    usage_check = check_usage_limit(db, current_user.id, current_user.plan, "daily_emails")
    if not usage_check["allowed"]:
        if usage_check.get("reason") == "free_limit":
            raise HTTPException(status_code=429, detail="무료 플랜의 일일 이메일 한도에 도달했습니다. 유료 플랜으로 업그레이드해주세요.")
        else:
            raise HTTPException(status_code=429, detail=f"일일 이메일 한도 초과. 크레딧이 부족합니다. (필요: {usage_check.get('credits_needed', 0)} 크레딧)")
    if not usage_check.get("within_plan", True):
        deduct_credits(db, current_user.id, usage_check["credits_needed"], "이메일 한도 초과 — 건당 과금")
        db.commit()

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

    # Create job record
    job = EmailSendJob(
        project_id=project_id,
        user_id=current_user.id,
        status="running",
        total_targets=target_count,
    )
    db.add(job)
    db.commit()

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


@router.get("/send-email/status", response_model=SendStatusResponse)
def get_email_send_status(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_project_or_404(project_id, current_user.id, db)

    job = (
        db.query(EmailSendJob)
        .filter(EmailSendJob.project_id == project_id, EmailSendJob.user_id == current_user.id)
        .order_by(EmailSendJob.started_at.desc())
        .first()
    )

    if not job:
        return SendStatusResponse(status="idle")

    return SendStatusResponse(
        status=job.status,
        total=job.total_targets,
        sent=job.sent_count,
        failed=job.failed_count,
        current_email=job.current_email,
        error=job.error,
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
