from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import Keyword, Project, User

router = APIRouter(
    prefix="/api/projects/{project_id}/keywords",
    tags=["keywords"],
)

VALID_SOURCES = {"naver", "google", "instagram", "naver_shopping", "naver_map"}


class KeywordResponse(BaseModel):
    id: int
    keyword: str
    source: str
    created_at: datetime

    model_config = {"from_attributes": True}


def _get_project_or_404(project_id: int, user_id: int, db: Session) -> Project:
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.user_id == user_id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("/", response_model=KeywordResponse, status_code=status.HTTP_201_CREATED)
def add_keyword(
    project_id: int,
    keyword: str = Body(..., embed=True),
    source: str = Body("naver", embed=True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a single keyword. Accepts { keyword: "text" } or { keyword: "text", source: "naver" }."""
    _get_project_or_404(project_id, current_user.id, db)

    if source not in VALID_SOURCES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid source: {source}. Must be one of {VALID_SOURCES}",
        )

    kw = Keyword(project_id=project_id, keyword=keyword, source=source)
    db.add(kw)
    db.commit()
    db.refresh(kw)
    return kw


@router.get("/", response_model=list[KeywordResponse])
def list_keywords(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_project_or_404(project_id, current_user.id, db)
    return (
        db.query(Keyword)
        .filter(Keyword.project_id == project_id)
        .order_by(Keyword.created_at.desc())
        .all()
    )


@router.delete("/{keyword_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_keyword(
    project_id: int,
    keyword_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_project_or_404(project_id, current_user.id, db)
    kw = (
        db.query(Keyword)
        .filter(Keyword.id == keyword_id, Keyword.project_id == project_id)
        .first()
    )
    if not kw:
        raise HTTPException(status_code=404, detail="Keyword not found")
    db.delete(kw)
    db.commit()
