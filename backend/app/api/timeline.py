from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import Activity, Prospect, Project, User

router = APIRouter(prefix="/api/projects/{project_id}/prospects/{prospect_id}/timeline", tags=["timeline"])


class ActivityResponse(BaseModel):
    id: int
    activity_type: str
    reference_id: int | None = None
    description: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


@router.get("/", response_model=list[ActivityResponse])
def get_timeline(
    project_id: int,
    prospect_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    prospect = db.query(Prospect).filter(Prospect.id == prospect_id, Prospect.project_id == project_id).first()
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")

    return (
        db.query(Activity)
        .filter(Activity.prospect_id == prospect_id, Activity.user_id == current_user.id)
        .order_by(Activity.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
