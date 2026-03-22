from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import DmLog, EmailLog, Project, Prospect, User

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


class DashboardStats(BaseModel):
    total_projects: int = 0
    total_prospects: int = 0
    emails_sent: int = 0
    dms_sent: int = 0
    emails_opened: int = 0
    emails_clicked: int = 0


@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    total_projects = (
        db.query(func.count(Project.id))
        .filter(Project.user_id == current_user.id)
        .scalar()
        or 0
    )

    project_ids = (
        db.query(Project.id).filter(Project.user_id == current_user.id).subquery()
    )

    total_prospects = (
        db.query(func.count(Prospect.id))
        .filter(Prospect.project_id.in_(db.query(project_ids.c.id)))
        .scalar()
        or 0
    )

    emails_sent = (
        db.query(func.count(EmailLog.id))
        .filter(EmailLog.user_id == current_user.id, EmailLog.status == "success")
        .scalar()
        or 0
    )

    dms_sent = (
        db.query(func.count(DmLog.id))
        .filter(DmLog.user_id == current_user.id, DmLog.status == "success")
        .scalar()
        or 0
    )

    emails_opened = (
        db.query(func.count(EmailLog.id))
        .filter(
            EmailLog.user_id == current_user.id,
            EmailLog.opened_at.isnot(None),
        )
        .scalar()
        or 0
    )

    emails_clicked = (
        db.query(func.count(EmailLog.id))
        .filter(
            EmailLog.user_id == current_user.id,
            EmailLog.clicked_at.isnot(None),
        )
        .scalar()
        or 0
    )

    return DashboardStats(
        total_projects=total_projects,
        total_prospects=total_prospects,
        emails_sent=emails_sent,
        dms_sent=dms_sent,
        emails_opened=emails_opened,
        emails_clicked=emails_clicked,
    )
