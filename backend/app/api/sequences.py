from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import (
    EmailSequence, EmailSequenceStep, Prospect,
    Project, SequenceEnrollment, User,
)

router = APIRouter(prefix="/api/projects/{project_id}/sequences", tags=["sequences"])


class SequenceCreate(BaseModel):
    name: str


class SequenceResponse(BaseModel):
    id: int
    name: str
    status: str
    created_at: datetime
    step_count: int = 0
    enrollment_count: int = 0

    model_config = {"from_attributes": True}


class StepCreate(BaseModel):
    step_number: int
    delay_days: int = 1
    subject: str
    body: str
    send_condition: str = "always"


class StepResponse(BaseModel):
    id: int
    sequence_id: int
    step_number: int
    delay_days: int
    subject: str
    body: str
    send_condition: str

    model_config = {"from_attributes": True}


class EnrollRequest(BaseModel):
    prospect_ids: list[int]


class EnrollmentResponse(BaseModel):
    id: int
    sequence_id: int
    prospect_id: int
    current_step: int
    status: str
    next_send_at: Optional[datetime] = None
    enrolled_at: datetime

    model_config = {"from_attributes": True}


def _get_project_or_404(project_id: int, user_id: int, db: Session) -> Project:
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _get_sequence_or_404(sequence_id: int, project_id: int, user_id: int, db: Session) -> EmailSequence:
    seq = (
        db.query(EmailSequence)
        .filter(
            EmailSequence.id == sequence_id,
            EmailSequence.project_id == project_id,
            EmailSequence.user_id == user_id,
        )
        .first()
    )
    if not seq:
        raise HTTPException(status_code=404, detail="Sequence not found")
    return seq


@router.get("/", response_model=list[SequenceResponse])
def list_sequences(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_project_or_404(project_id, current_user.id, db)
    sequences = (
        db.query(EmailSequence)
        .filter(EmailSequence.project_id == project_id, EmailSequence.user_id == current_user.id)
        .order_by(EmailSequence.created_at.desc())
        .all()
    )
    results = []
    for seq in sequences:
        step_count = db.query(EmailSequenceStep).filter(EmailSequenceStep.sequence_id == seq.id).count()
        enrollment_count = db.query(SequenceEnrollment).filter(SequenceEnrollment.sequence_id == seq.id).count()
        results.append(SequenceResponse(
            id=seq.id, name=seq.name, status=seq.status,
            created_at=seq.created_at, step_count=step_count,
            enrollment_count=enrollment_count,
        ))
    return results


@router.post("/", response_model=SequenceResponse, status_code=status.HTTP_201_CREATED)
def create_sequence(
    project_id: int,
    req: SequenceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_project_or_404(project_id, current_user.id, db)
    seq = EmailSequence(
        user_id=current_user.id,
        project_id=project_id,
        name=req.name,
    )
    db.add(seq)
    db.commit()
    db.refresh(seq)
    return SequenceResponse(id=seq.id, name=seq.name, status=seq.status, created_at=seq.created_at)


@router.put("/{sequence_id}/status")
def update_sequence_status(
    project_id: int,
    sequence_id: int,
    new_status: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    seq = _get_sequence_or_404(sequence_id, project_id, current_user.id, db)
    if new_status not in ("active", "paused", "draft"):
        raise HTTPException(status_code=400, detail="Invalid status")
    seq.status = new_status
    db.commit()
    return {"status": seq.status}


@router.delete("/{sequence_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_sequence(
    project_id: int,
    sequence_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    seq = _get_sequence_or_404(sequence_id, project_id, current_user.id, db)
    db.delete(seq)
    db.commit()


# ── Steps ──

@router.get("/{sequence_id}/steps", response_model=list[StepResponse])
def list_steps(
    project_id: int,
    sequence_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_sequence_or_404(sequence_id, project_id, current_user.id, db)
    return (
        db.query(EmailSequenceStep)
        .filter(EmailSequenceStep.sequence_id == sequence_id)
        .order_by(EmailSequenceStep.step_number)
        .all()
    )


@router.post("/{sequence_id}/steps", response_model=StepResponse, status_code=status.HTTP_201_CREATED)
def create_step(
    project_id: int,
    sequence_id: int,
    req: StepCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_sequence_or_404(sequence_id, project_id, current_user.id, db)
    step = EmailSequenceStep(
        sequence_id=sequence_id,
        step_number=req.step_number,
        delay_days=req.delay_days,
        subject=req.subject,
        body=req.body,
        send_condition=req.send_condition,
    )
    db.add(step)
    db.commit()
    db.refresh(step)
    return step


@router.delete("/{sequence_id}/steps/{step_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_step(
    project_id: int,
    sequence_id: int,
    step_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_sequence_or_404(sequence_id, project_id, current_user.id, db)
    step = db.query(EmailSequenceStep).filter(EmailSequenceStep.id == step_id, EmailSequenceStep.sequence_id == sequence_id).first()
    if not step:
        raise HTTPException(status_code=404, detail="Step not found")
    db.delete(step)
    db.commit()


# ── Enrollments ──

@router.post("/{sequence_id}/enroll", response_model=list[EnrollmentResponse])
def enroll_prospects(
    project_id: int,
    sequence_id: int,
    req: EnrollRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    seq = _get_sequence_or_404(sequence_id, project_id, current_user.id, db)
    first_step = (
        db.query(EmailSequenceStep)
        .filter(EmailSequenceStep.sequence_id == sequence_id, EmailSequenceStep.step_number == 1)
        .first()
    )
    if not first_step:
        raise HTTPException(status_code=400, detail="Sequence has no steps")

    now = datetime.now(timezone.utc)
    enrollments = []
    for pid in req.prospect_ids:
        existing = (
            db.query(SequenceEnrollment)
            .filter(SequenceEnrollment.sequence_id == sequence_id, SequenceEnrollment.prospect_id == pid)
            .first()
        )
        if existing:
            continue
        enrollment = SequenceEnrollment(
            sequence_id=sequence_id,
            prospect_id=pid,
            current_step=1,
            next_send_at=now + timedelta(days=first_step.delay_days),
        )
        db.add(enrollment)
        enrollments.append(enrollment)

    db.commit()
    for e in enrollments:
        db.refresh(e)
    return enrollments


@router.get("/{sequence_id}/enrollments", response_model=list[EnrollmentResponse])
def list_enrollments(
    project_id: int,
    sequence_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_sequence_or_404(sequence_id, project_id, current_user.id, db)
    return (
        db.query(SequenceEnrollment)
        .filter(SequenceEnrollment.sequence_id == sequence_id)
        .order_by(SequenceEnrollment.enrolled_at.desc())
        .all()
    )
