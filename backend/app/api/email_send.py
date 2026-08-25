import logging
import threading
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.rate_limit import limiter
from app.core.database import get_db, SessionLocal
from app.core.security import decrypt_value, get_current_user
from app.models.models import EmailLog, EmailSendJob, GlobalProspect, Prospect, Project, User, UserSettings
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


class StartEmailRequest(BaseModel):
    scheduled_at: Optional[datetime] = None
    template_id: Optional[int] = None  # A/B: 이 템플릿의 변형들을 weight로 발송
    smart_send: bool = False           # 업종 최적 시각에 자동 예약


class TestEmailRequest(BaseModel):
    to_email: Optional[str] = None


class PreviewEmailRequest(BaseModel):
    prospect_id: int


class PreviewEmailResponse(BaseModel):
    subject: str
    html_body: str
    to_email: str
    from_email: str


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
            user = db.query(User).filter(User.id == user_id).first()
            sender_name = user.name if user else settings.gmail_email.split("@")[0]

            # 워밍업 강제: 계정 나이 기반 안전 한도로 캡 + 오늘 이미 보낸 건수 차감
            from datetime import timezone as tz
            from sqlalchemy import func as sa_func
            from app.core.plans import get_enforced_daily_limit

            created = user.created_at if user else None
            if created and created.tzinfo is None:
                created = created.replace(tzinfo=tz.utc)
            account_age = (datetime.now(tz.utc) - created).days if created else 0
            enforced_limit = get_enforced_daily_limit("email", account_age, settings.daily_email_limit)

            today_start = datetime.now(tz.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            sent_today = (
                db.query(sa_func.count(EmailLog.id))
                .filter(
                    EmailLog.user_id == user_id,
                    EmailLog.status == "success",
                    EmailLog.sent_at >= today_start.replace(tzinfo=None),
                )
                .scalar()
                or 0
            )
            remaining_today = max(0, enforced_limit - sent_today)
            if remaining_today == 0:
                job.status = "completed"
                job.error = (
                    f"오늘의 안전 발송 한도({enforced_limit}건)에 도달했습니다. "
                    "내일 다시 시도하세요. (계정 보호를 위한 워밍업/안전 한도)"
                )
                job.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
                db.commit()
                return

            # A/B: 지정된 템플릿의 변형들을 로드 (2개 이상일 때만 A/B 활성)
            variants = None
            if job.template_id:
                from app.models.models import EmailTemplate, EmailVariant
                tmpl = (
                    db.query(EmailTemplate)
                    .filter(EmailTemplate.id == job.template_id, EmailTemplate.user_id == user_id)
                    .first()
                )
                if tmpl:
                    vs = db.query(EmailVariant).filter(EmailVariant.template_id == tmpl.id).all()
                    if len(vs) >= 2:
                        variants = vs

            result = send_bulk_emails(
                db=db,
                gmail_email=settings.gmail_email,
                gmail_app_password=gmail_pw,
                prospects=prospects,
                user_id=user_id,
                sender_name=sender_name,
                email_template=settings.email_template,
                email_subject=settings.email_subject,
                daily_limit=remaining_today,
                job=job,
                ad_prefix_enabled=settings.ad_prefix_enabled,
                sender_info=settings.sender_info,
                variants=variants,
            )
            job.status = "completed"
            job.sent_count = result["sent"]
            job.failed_count = result["failed"]
            job.current_email = None
            job.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
            # Update GlobalProspect.times_emailed for successfully sent emails only
            if result["sent"] > 0:
                sent_logs = (
                    db.query(EmailLog.prospect_id)
                    .join(Prospect, EmailLog.prospect_id == Prospect.id)
                    .filter(
                        Prospect.project_id == project_id,
                        EmailLog.user_id == user_id,
                        EmailLog.status == "success",
                        Prospect.global_prospect_id.isnot(None),
                    )
                    .distinct()
                    .all()
                )
                sent_prospect_ids = {row[0] for row in sent_logs}
                for p in prospects:
                    if p.id in sent_prospect_ids and p.global_prospect_id:
                        gp = db.query(GlobalProspect).filter(GlobalProspect.id == p.global_prospect_id).first()
                        if gp:
                            gp.times_emailed += 1
            db.commit()
    except Exception as e:
        logger.error(f"Email sending failed: {e}")
        if job:
            job.status = "failed"
            job.error = str(e)
            job.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
            db.commit()
    finally:
        db.close()


@router.post("/send-email/preview", response_model=PreviewEmailResponse)
def preview_email(
    project_id: int,
    req: PreviewEmailRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Preview email with prospect data filled in."""
    _get_project_or_404(project_id, current_user.id, db)
    settings = _get_user_settings_or_error(current_user.id, db)

    prospect = (
        db.query(Prospect)
        .filter(Prospect.id == req.prospect_id, Prospect.project_id == project_id)
        .first()
    )
    if not prospect:
        raise HTTPException(status_code=404, detail="잠재고객을 찾을 수 없습니다.")

    from app.services.sender.email import render_template
    company_name = prospect.name or "고객"
    category = prospect.category or "귀사 업종"

    html_body = make_default_email_html(
        company_name=company_name,
        category=category,
        sender_name=current_user.name,
        custom_template=settings.email_template,
    )

    raw_subject = settings.email_subject or "안녕하세요, {company_name}님께 제안 드립니다"
    subject = render_template(raw_subject, company_name, category, current_user.name)

    return PreviewEmailResponse(
        subject=subject,
        html_body=html_body,
        to_email=prospect.email or "",
        from_email=settings.gmail_email,
    )


@router.post("/send-email", response_model=SendEmailResponse)
@limiter.limit("3/minute")
def start_email_sending(
    request: Request,
    project_id: int,
    req: StartEmailRequest = StartEmailRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_project_or_404(project_id, current_user.id, db)
    _get_user_settings_or_error(current_user.id, db)

    # 크레딧 사전 확인 — 1건 보낼 만큼은 있어야 시작 가능
    # (실제 차감은 send_bulk_emails 안에서 매 건 발송 성공 시 진행)
    from app.core.plans import check_credits
    if not check_credits(db, current_user.id, "email", 1)["allowed"]:
        raise HTTPException(
            status_code=402,
            detail=f"크레딧이 부족합니다. 충전 후 다시 시도하세요. (이메일 1건 = {2} 크레딧)",
        )

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

    # 스마트 발송: 업종 최적 시각 자동 예약 (명시적 scheduled_at 없을 때만)
    scheduled_at = req.scheduled_at
    smart_reason = None
    if not scheduled_at and req.smart_send:
        from app.services.smart_send import compute_smart_send_at
        scheduled_at, smart_reason = compute_smart_send_at(db, project_id)

    # If scheduled_at is provided (or smart-computed), create a scheduled job
    if scheduled_at:
        job = EmailSendJob(
            project_id=project_id,
            user_id=current_user.id,
            status="scheduled",
            total_targets=target_count,
            scheduled_at=scheduled_at,
            template_id=req.template_id,
        )
        db.add(job)
        db.commit()
        msg = f"{target_count}명에게 {scheduled_at:%m월 %d일 %H시} 발송 예약됨"
        if smart_reason:
            msg += f" ({smart_reason})"
        return SendEmailResponse(message=msg, target_count=target_count)

    # Create job record
    job = EmailSendJob(
        project_id=project_id,
        user_id=current_user.id,
        status="running",
        total_targets=target_count,
        template_id=req.template_id,
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
