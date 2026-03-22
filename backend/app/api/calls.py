from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import Activity, CallLog, Project, User

router = APIRouter(prefix="/api/projects/{project_id}/calls", tags=["calls"])


class CallCreate(BaseModel):
    prospect_id: int
    call_type: str = "outbound"
    duration_seconds: int = 0
    notes: Optional[str] = None
    outcome: Optional[str] = None
    callback_at: Optional[datetime] = None


class CallResponse(BaseModel):
    id: int
    prospect_id: int
    project_id: int
    call_type: str
    duration_seconds: int
    notes: Optional[str] = None
    outcome: Optional[str] = None
    callback_at: Optional[datetime] = None
    called_at: datetime

    model_config = {"from_attributes": True}


def _get_project_or_404(project_id: int, user_id: int, db: Session) -> Project:
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("/", response_model=list[CallResponse])
def list_calls(
    project_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_project_or_404(project_id, current_user.id, db)
    return (
        db.query(CallLog)
        .filter(CallLog.project_id == project_id, CallLog.user_id == current_user.id)
        .order_by(CallLog.called_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )


@router.post("/", response_model=CallResponse, status_code=status.HTTP_201_CREATED)
def create_call(
    project_id: int,
    req: CallCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_project_or_404(project_id, current_user.id, db)
    call = CallLog(
        user_id=current_user.id,
        prospect_id=req.prospect_id,
        project_id=project_id,
        call_type=req.call_type,
        duration_seconds=req.duration_seconds,
        notes=req.notes,
        outcome=req.outcome,
        callback_at=req.callback_at,
    )
    db.add(call)

    activity = Activity(
        user_id=current_user.id,
        prospect_id=req.prospect_id,
        activity_type="call",
        reference_id=None,
        description=f"통화 ({req.call_type}): {req.outcome or '기록 없음'}",
    )
    db.add(activity)
    db.commit()
    db.refresh(call)
    return call


@router.get("/callbacks", response_model=list[CallResponse])
def list_callbacks(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_project_or_404(project_id, current_user.id, db)
    return (
        db.query(CallLog)
        .filter(
            CallLog.project_id == project_id,
            CallLog.user_id == current_user.id,
            CallLog.callback_at.isnot(None),
        )
        .order_by(CallLog.callback_at)
        .all()
    )


@router.delete("/{call_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_call(
    project_id: int,
    call_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    call = (
        db.query(CallLog)
        .filter(CallLog.id == call_id, CallLog.project_id == project_id, CallLog.user_id == current_user.id)
        .first()
    )
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    db.delete(call)
    db.commit()
