from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import Project, Prospect, User

router = APIRouter(
    prefix="/api/projects/{project_id}/prospects",
    tags=["prospects"],
)


class ProspectResponse(BaseModel):
    id: int
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    instagram: Optional[str] = None
    website: Optional[str] = None
    source: Optional[str] = None
    category: Optional[str] = None
    status: str
    collected_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProspectListResponse(BaseModel):
    prospects: list[ProspectResponse]
    total: int
    page: int
    page_size: int


class ProspectStatusUpdate(BaseModel):
    status: str  # approved, rejected


class StatsResponse(BaseModel):
    collected: int = 0
    approved: int = 0
    rejected: int = 0
    email_sent: int = 0
    dm_sent: int = 0
    total: int = 0


def _get_project_or_404(project_id: int, user_id: int, db: Session) -> Project:
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.user_id == user_id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("/", response_model=ProspectListResponse)
def list_prospects(
    project_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_project_or_404(project_id, current_user.id, db)

    query = db.query(Prospect).filter(Prospect.project_id == project_id)
    if status_filter:
        query = query.filter(Prospect.status == status_filter)

    total = query.count()
    prospects = (
        query.order_by(Prospect.collected_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return ProspectListResponse(
        prospects=prospects,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.patch("/{prospect_id}", response_model=ProspectResponse)
def update_prospect_status(
    project_id: int,
    prospect_id: int,
    req: ProspectStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_project_or_404(project_id, current_user.id, db)

    valid_statuses = {"approved", "rejected", "collected"}
    if req.status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {valid_statuses}",
        )

    prospect = (
        db.query(Prospect)
        .filter(Prospect.id == prospect_id, Prospect.project_id == project_id)
        .first()
    )
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")

    prospect.status = req.status
    db.commit()
    db.refresh(prospect)
    return prospect


@router.post("/approve-all", response_model=dict)
def approve_all_prospects(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_project_or_404(project_id, current_user.id, db)

    count = (
        db.query(Prospect)
        .filter(Prospect.project_id == project_id, Prospect.status == "collected")
        .update({"status": "approved"})
    )
    db.commit()
    return {"approved_count": count}


@router.get("/stats", response_model=StatsResponse)
def get_prospect_stats(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_project_or_404(project_id, current_user.id, db)

    rows = (
        db.query(Prospect.status, func.count(Prospect.id))
        .filter(Prospect.project_id == project_id)
        .group_by(Prospect.status)
        .all()
    )

    stats = {row[0]: row[1] for row in rows}
    total = sum(stats.values())

    return StatsResponse(
        collected=stats.get("collected", 0),
        approved=stats.get("approved", 0),
        rejected=stats.get("rejected", 0),
        email_sent=stats.get("email_sent", 0),
        dm_sent=stats.get("dm_sent", 0),
        total=total,
    )
