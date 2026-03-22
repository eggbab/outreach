from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import DmLog, Prospect, User

router = APIRouter(
    prefix="/api/projects/{project_id}/dm",
    tags=["dm"],
)

# Track last extension ping per user
_extension_pings: dict[int, datetime] = {}


class DmStatusResponse(BaseModel):
    connected: bool


class DmQueueItem(BaseModel):
    prospect_id: int
    name: Optional[str] = None
    instagram: str
    category: Optional[str] = None

    model_config = {"from_attributes": True}


class DmLogItem(BaseModel):
    prospect_id: int
    name: Optional[str] = None
    instagram: Optional[str] = None
    status: str
    sent_at: datetime
    error_message: Optional[str] = None


@router.get("/status", response_model=DmStatusResponse)
def get_dm_status(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Check if Chrome extension has recently pinged."""
    last_ping = _extension_pings.get(current_user.id)
    connected = (
        last_ping is not None
        and (datetime.now(timezone.utc) - last_ping) < timedelta(minutes=10)
    )
    return DmStatusResponse(connected=connected)


@router.post("/ping")
def ping_extension(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Called by Chrome extension to indicate it's alive."""
    _extension_pings[current_user.id] = datetime.now(timezone.utc)
    return {"status": "ok"}


@router.get("/queue", response_model=list[DmQueueItem])
def get_dm_queue(
    project_id: int,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get approved prospects with Instagram that haven't been DM'd yet."""
    dm_sent_ids = (
        db.query(DmLog.prospect_id)
        .filter(DmLog.user_id == current_user.id, DmLog.status == "success")
        .subquery()
    )

    prospects = (
        db.query(Prospect)
        .filter(
            Prospect.project_id == project_id,
            Prospect.status.in_(["approved", "email_sent"]),
            Prospect.instagram.isnot(None),
            Prospect.instagram != "",
            ~Prospect.id.in_(db.query(dm_sent_ids.c.prospect_id)),
        )
        .order_by(Prospect.collected_at)
        .limit(limit)
        .all()
    )

    return [
        DmQueueItem(
            prospect_id=p.id,
            name=p.name,
            instagram=p.instagram,
            category=p.category,
        )
        for p in prospects
    ]


@router.get("/log", response_model=list[DmLogItem])
def get_dm_log(
    project_id: int,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get DM send history for this project."""
    logs = (
        db.query(DmLog, Prospect)
        .join(Prospect, DmLog.prospect_id == Prospect.id)
        .filter(
            Prospect.project_id == project_id,
            DmLog.user_id == current_user.id,
        )
        .order_by(DmLog.sent_at.desc())
        .limit(limit)
        .all()
    )

    return [
        DmLogItem(
            prospect_id=log.prospect_id,
            name=prospect.name,
            instagram=prospect.instagram,
            status=log.status,
            sent_at=log.sent_at,
            error_message=log.error_message,
        )
        for log, prospect in logs
    ]
