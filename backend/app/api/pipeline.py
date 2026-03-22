from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import Activity, Deal, PipelineStage, User

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])


DEFAULT_STAGES = [
    {"name": "리드", "position": 0, "color": "#6B7280"},
    {"name": "컨택", "position": 1, "color": "#3B82F6"},
    {"name": "미팅", "position": 2, "color": "#8B5CF6"},
    {"name": "제안", "position": 3, "color": "#F59E0B"},
    {"name": "계약", "position": 4, "color": "#10B981"},
    {"name": "성사", "position": 5, "color": "#059669", "is_won": True},
    {"name": "실패", "position": 6, "color": "#EF4444", "is_lost": True},
]


# ── Schemas ──

class StageCreate(BaseModel):
    name: str
    position: int = 0
    color: str = "#3B82F6"
    is_won: bool = False
    is_lost: bool = False


class StageResponse(BaseModel):
    id: int
    name: str
    position: int
    color: str
    is_won: bool
    is_lost: bool
    deal_count: int = 0
    total_value: int = 0

    model_config = {"from_attributes": True}


class DealCreate(BaseModel):
    prospect_id: int
    project_id: int
    stage_id: int
    title: str
    value: int = 0
    notes: Optional[str] = None


class DealResponse(BaseModel):
    id: int
    prospect_id: int
    project_id: int
    stage_id: Optional[int] = None
    title: str
    value: int
    notes: Optional[str] = None
    created_at: datetime
    closed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class DealMoveRequest(BaseModel):
    stage_id: int


class PipelineStatsResponse(BaseModel):
    total_deals: int = 0
    total_value: int = 0
    won_deals: int = 0
    won_value: int = 0
    lost_deals: int = 0


# ── Helpers ──

def create_default_stages(db: Session, user_id: int):
    for s in DEFAULT_STAGES:
        stage = PipelineStage(
            user_id=user_id,
            name=s["name"],
            position=s["position"],
            color=s["color"],
            is_won=s.get("is_won", False),
            is_lost=s.get("is_lost", False),
        )
        db.add(stage)


# ── Stage endpoints ──

@router.get("/stages", response_model=list[StageResponse])
def list_stages(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stages = (
        db.query(PipelineStage)
        .filter(PipelineStage.user_id == current_user.id)
        .order_by(PipelineStage.position)
        .all()
    )
    results = []
    for stage in stages:
        deal_count = db.query(func.count(Deal.id)).filter(Deal.stage_id == stage.id).scalar() or 0
        total_value = db.query(func.coalesce(func.sum(Deal.value), 0)).filter(Deal.stage_id == stage.id).scalar()
        results.append(StageResponse(
            id=stage.id, name=stage.name, position=stage.position,
            color=stage.color, is_won=stage.is_won, is_lost=stage.is_lost,
            deal_count=deal_count, total_value=total_value,
        ))
    return results


@router.post("/stages", response_model=StageResponse, status_code=status.HTTP_201_CREATED)
def create_stage(
    req: StageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stage = PipelineStage(
        user_id=current_user.id,
        name=req.name,
        position=req.position,
        color=req.color,
        is_won=req.is_won,
        is_lost=req.is_lost,
    )
    db.add(stage)
    db.commit()
    db.refresh(stage)
    return StageResponse(
        id=stage.id, name=stage.name, position=stage.position,
        color=stage.color, is_won=stage.is_won, is_lost=stage.is_lost,
    )


@router.delete("/stages/{stage_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_stage(
    stage_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stage = (
        db.query(PipelineStage)
        .filter(PipelineStage.id == stage_id, PipelineStage.user_id == current_user.id)
        .first()
    )
    if not stage:
        raise HTTPException(status_code=404, detail="Stage not found")
    db.delete(stage)
    db.commit()


# ── Deal endpoints ──

@router.get("/deals", response_model=list[DealResponse])
def list_deals(
    stage_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Deal).filter(Deal.user_id == current_user.id)
    if stage_id is not None:
        q = q.filter(Deal.stage_id == stage_id)
    return q.order_by(Deal.created_at.desc()).all()


@router.post("/deals", response_model=DealResponse, status_code=status.HTTP_201_CREATED)
def create_deal(
    req: DealCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    deal = Deal(
        user_id=current_user.id,
        prospect_id=req.prospect_id,
        project_id=req.project_id,
        stage_id=req.stage_id,
        title=req.title,
        value=req.value,
        notes=req.notes,
    )
    db.add(deal)

    activity = Activity(
        user_id=current_user.id,
        prospect_id=req.prospect_id,
        activity_type="deal_created",
        description=f"딜 생성: {req.title}",
    )
    db.add(activity)
    db.commit()
    db.refresh(deal)
    return deal


@router.put("/deals/{deal_id}/move", response_model=DealResponse)
def move_deal(
    deal_id: int,
    req: DealMoveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    deal = db.query(Deal).filter(Deal.id == deal_id, Deal.user_id == current_user.id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    stage = db.query(PipelineStage).filter(PipelineStage.id == req.stage_id).first()
    if not stage:
        raise HTTPException(status_code=404, detail="Stage not found")

    deal.stage_id = req.stage_id
    if stage.is_won or stage.is_lost:
        deal.closed_at = datetime.now(timezone.utc)

    activity = Activity(
        user_id=current_user.id,
        prospect_id=deal.prospect_id,
        activity_type="deal_stage_changed",
        reference_id=deal.id,
        description=f"딜 스테이지 변경: {stage.name}",
    )
    db.add(activity)
    db.commit()
    db.refresh(deal)
    return deal


@router.delete("/deals/{deal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_deal(
    deal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    deal = db.query(Deal).filter(Deal.id == deal_id, Deal.user_id == current_user.id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    db.delete(deal)
    db.commit()


@router.get("/stats", response_model=PipelineStatsResponse)
def get_pipeline_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    deals = db.query(Deal).filter(Deal.user_id == current_user.id).all()
    won_stages = [s.id for s in db.query(PipelineStage).filter(PipelineStage.user_id == current_user.id, PipelineStage.is_won == True).all()]
    lost_stages = [s.id for s in db.query(PipelineStage).filter(PipelineStage.user_id == current_user.id, PipelineStage.is_lost == True).all()]

    return PipelineStatsResponse(
        total_deals=len(deals),
        total_value=sum(d.value for d in deals),
        won_deals=sum(1 for d in deals if d.stage_id in won_stages),
        won_value=sum(d.value for d in deals if d.stage_id in won_stages),
        lost_deals=sum(1 for d in deals if d.stage_id in lost_stages),
    )
