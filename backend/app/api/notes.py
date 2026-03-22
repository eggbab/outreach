from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import Prospect, ProspectNote, Project, User

router = APIRouter(
    prefix="/api/projects/{project_id}/prospects/{prospect_id}/notes",
    tags=["notes"],
)


class NoteCreate(BaseModel):
    content: str


class NoteResponse(BaseModel):
    id: int
    prospect_id: int
    user_id: int
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


def _verify_access(project_id: int, prospect_id: int, user_id: int, db: Session) -> Prospect:
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.user_id == user_id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    prospect = (
        db.query(Prospect)
        .filter(Prospect.id == prospect_id, Prospect.project_id == project_id)
        .first()
    )
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")
    return prospect


@router.get("/", response_model=list[NoteResponse])
def list_notes(
    project_id: int,
    prospect_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _verify_access(project_id, prospect_id, current_user.id, db)
    return (
        db.query(ProspectNote)
        .filter(ProspectNote.prospect_id == prospect_id, ProspectNote.user_id == current_user.id)
        .order_by(ProspectNote.created_at.desc())
        .all()
    )


@router.post("/", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
def create_note(
    project_id: int,
    prospect_id: int,
    req: NoteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _verify_access(project_id, prospect_id, current_user.id, db)
    note = ProspectNote(
        prospect_id=prospect_id,
        user_id=current_user.id,
        content=req.content,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(
    project_id: int,
    prospect_id: int,
    note_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _verify_access(project_id, prospect_id, current_user.id, db)
    note = (
        db.query(ProspectNote)
        .filter(ProspectNote.id == note_id, ProspectNote.user_id == current_user.id)
        .first()
    )
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    db.delete(note)
    db.commit()
