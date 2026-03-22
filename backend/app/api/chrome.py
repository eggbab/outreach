from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import DmLog, Project, Prospect, User

router = APIRouter(prefix="/api/chrome", tags=["chrome"])


class DmTarget(BaseModel):
    prospect_id: int
    name: Optional[str] = None
    instagram: str
    category: Optional[str] = None

    model_config = {"from_attributes": True}


class DmQueueResponse(BaseModel):
    targets: list[DmTarget]
    total: int


class DmResultRequest(BaseModel):
    prospect_id: int
    status: str  # success or failed
    error_message: Optional[str] = None


@router.get("/dm-queue", response_model=DmQueueResponse)
def get_dm_queue(
    project_id: int = Query(..., description="Project ID to get DM targets from"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get DM targets for chrome extension - approved prospects with instagram, not yet DM'd."""
    # Subquery: prospect IDs that already have successful DM logs
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

    targets = [
        DmTarget(
            prospect_id=p.id,
            name=p.name,
            instagram=p.instagram,
            category=p.category,
        )
        for p in prospects
    ]

    total_count = (
        db.query(Prospect)
        .filter(
            Prospect.project_id == project_id,
            Prospect.status.in_(["approved", "email_sent"]),
            Prospect.instagram.isnot(None),
            Prospect.instagram != "",
            ~Prospect.id.in_(db.query(dm_sent_ids.c.prospect_id)),
        )
        .count()
    )

    return DmQueueResponse(targets=targets, total=total_count)


@router.post("/dm-result", response_model=dict)
def report_dm_result(
    req: DmResultRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Report DM send result from chrome extension."""
    prospect = (
        db.query(Prospect)
        .join(Project, Prospect.project_id == Project.id)
        .filter(Prospect.id == req.prospect_id, Project.user_id == current_user.id)
        .first()
    )
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")

    if req.status not in ("success", "failed"):
        raise HTTPException(status_code=400, detail="Status must be 'success' or 'failed'")

    log = DmLog(
        prospect_id=req.prospect_id,
        user_id=current_user.id,
        status=req.status,
        error_message=req.error_message,
    )
    db.add(log)

    if req.status == "success":
        prospect.status = "dm_sent"

    db.commit()
    return {"message": "DM result recorded", "status": req.status}
