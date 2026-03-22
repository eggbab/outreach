import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import OnboardingProgress, User

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])

ONBOARDING_STEPS = [
    {"id": "create_project", "label": "첫 프로젝트 만들기"},
    {"id": "add_keyword", "label": "키워드 추가하기"},
    {"id": "collect_prospects", "label": "잠재고객 수집하기"},
    {"id": "setup_email", "label": "Gmail 설정하기"},
    {"id": "send_email", "label": "첫 이메일 보내기"},
]


class OnboardingResponse(BaseModel):
    steps: list[dict]
    steps_completed: list[str]
    is_completed: bool
    dismissed: bool


class StepCompleteRequest(BaseModel):
    step_id: str


@router.get("/", response_model=OnboardingResponse)
def get_onboarding(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    progress = db.query(OnboardingProgress).filter(OnboardingProgress.user_id == current_user.id).first()
    completed = json.loads(progress.steps_completed) if progress else []
    return OnboardingResponse(
        steps=ONBOARDING_STEPS,
        steps_completed=completed,
        is_completed=progress.completed_at is not None if progress else False,
        dismissed=progress.dismissed if progress else False,
    )


@router.post("/complete-step")
def complete_step(
    req: StepCompleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    progress = db.query(OnboardingProgress).filter(OnboardingProgress.user_id == current_user.id).first()
    if not progress:
        progress = OnboardingProgress(user_id=current_user.id)
        db.add(progress)
        db.flush()

    completed = json.loads(progress.steps_completed)
    if req.step_id not in completed:
        completed.append(req.step_id)
        progress.steps_completed = json.dumps(completed)

        if len(completed) >= len(ONBOARDING_STEPS):
            from datetime import datetime, timezone
            progress.completed_at = datetime.now(timezone.utc)

    db.commit()
    return {"steps_completed": completed}


@router.post("/dismiss")
def dismiss_onboarding(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    progress = db.query(OnboardingProgress).filter(OnboardingProgress.user_id == current_user.id).first()
    if not progress:
        progress = OnboardingProgress(user_id=current_user.id, dismissed=True)
        db.add(progress)
    else:
        progress.dismissed = True
    db.commit()
    return {"dismissed": True}
