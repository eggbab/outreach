from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import EmailLog, DmLog, Prospect, Project, User

router = APIRouter(prefix="/api/projects/{project_id}/analytics", tags=["analytics"])


class EmailStatsResponse(BaseModel):
    total_sent: int = 0
    total_opened: int = 0
    total_clicked: int = 0
    open_rate: float = 0.0
    click_rate: float = 0.0


class DailyStatResponse(BaseModel):
    date: str
    sent: int = 0
    opened: int = 0
    clicked: int = 0


class FunnelResponse(BaseModel):
    collected: int = 0
    approved: int = 0
    email_sent: int = 0
    dm_sent: int = 0
    opened: int = 0
    clicked: int = 0


def _get_project_or_404(project_id: int, user_id: int, db: Session) -> Project:
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.user_id == user_id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("/email-stats", response_model=EmailStatsResponse)
def get_email_stats(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_project_or_404(project_id, current_user.id, db)

    prospect_ids = (
        db.query(Prospect.id).filter(Prospect.project_id == project_id).subquery()
    )

    total_sent = (
        db.query(func.count(EmailLog.id))
        .filter(EmailLog.prospect_id.in_(prospect_ids), EmailLog.status == "success")
        .scalar() or 0
    )
    total_opened = (
        db.query(func.count(EmailLog.id))
        .filter(
            EmailLog.prospect_id.in_(prospect_ids),
            EmailLog.status == "success",
            EmailLog.opened_at.isnot(None),
        )
        .scalar() or 0
    )
    total_clicked = (
        db.query(func.count(EmailLog.id))
        .filter(
            EmailLog.prospect_id.in_(prospect_ids),
            EmailLog.status == "success",
            EmailLog.clicked_at.isnot(None),
        )
        .scalar() or 0
    )

    open_rate = (total_opened / total_sent * 100) if total_sent > 0 else 0
    click_rate = (total_clicked / total_sent * 100) if total_sent > 0 else 0

    return EmailStatsResponse(
        total_sent=total_sent,
        total_opened=total_opened,
        total_clicked=total_clicked,
        open_rate=round(open_rate, 1),
        click_rate=round(click_rate, 1),
    )


@router.get("/email-stats/daily", response_model=list[DailyStatResponse])
def get_daily_email_stats(
    project_id: int,
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_project_or_404(project_id, current_user.id, db)

    since = datetime.now(timezone.utc) - timedelta(days=days)
    prospect_ids = (
        db.query(Prospect.id).filter(Prospect.project_id == project_id).subquery()
    )

    logs = (
        db.query(EmailLog)
        .filter(
            EmailLog.prospect_id.in_(prospect_ids),
            EmailLog.status == "success",
            EmailLog.sent_at >= since,
        )
        .all()
    )

    daily = {}
    for log in logs:
        day = log.sent_at.strftime("%Y-%m-%d")
        if day not in daily:
            daily[day] = {"date": day, "sent": 0, "opened": 0, "clicked": 0}
        daily[day]["sent"] += 1
        if log.opened_at:
            daily[day]["opened"] += 1
        if log.clicked_at:
            daily[day]["clicked"] += 1

    return sorted(daily.values(), key=lambda x: x["date"])


@router.get("/funnel", response_model=FunnelResponse)
def get_funnel(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_project_or_404(project_id, current_user.id, db)

    collected = db.query(func.count(Prospect.id)).filter(Prospect.project_id == project_id).scalar() or 0
    approved = (
        db.query(func.count(Prospect.id))
        .filter(Prospect.project_id == project_id, Prospect.status.in_(["approved", "email_sent", "dm_sent"]))
        .scalar() or 0
    )
    email_sent = (
        db.query(func.count(Prospect.id))
        .filter(Prospect.project_id == project_id, Prospect.status == "email_sent")
        .scalar() or 0
    )
    dm_sent = (
        db.query(func.count(Prospect.id))
        .filter(Prospect.project_id == project_id, Prospect.status == "dm_sent")
        .scalar() or 0
    )

    prospect_ids = db.query(Prospect.id).filter(Prospect.project_id == project_id).subquery()
    opened = (
        db.query(func.count(func.distinct(EmailLog.prospect_id)))
        .filter(EmailLog.prospect_id.in_(prospect_ids), EmailLog.opened_at.isnot(None))
        .scalar() or 0
    )
    clicked = (
        db.query(func.count(func.distinct(EmailLog.prospect_id)))
        .filter(EmailLog.prospect_id.in_(prospect_ids), EmailLog.clicked_at.isnot(None))
        .scalar() or 0
    )

    return FunnelResponse(
        collected=collected,
        approved=approved,
        email_sent=email_sent,
        dm_sent=dm_sent,
        opened=opened,
        clicked=clicked,
    )
