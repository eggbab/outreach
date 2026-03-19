from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import Keyword, Project, User

router = APIRouter(
    prefix="/api/projects/{project_id}/keywords",
    tags=["keywords"],
)


class KeywordItem(BaseModel):
    keyword: str
    source: str  # naver, google, instagram, naver_shopping, naver_map


class KeywordCreate(BaseModel):
    keywords: list[KeywordItem]


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


@router.post("/", response_model=list[KeywordResponse], status_code=status.HTTP_201_CREATED)
def add_keywords(
    project_id: int,
    req: KeywordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_project_or_404(project_id, current_user.id, db)

    valid_sources = {"naver", "google", "instagram", "naver_shopping", "naver_map"}
    created = []
    for item in req.keywords:
        if item.source not in valid_sources:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid source: {item.source}. Must be one of {valid_sources}",
            )
        kw = Keyword(project_id=project_id, keyword=item.keyword, source=item.source)
        db.add(kw)
        created.append(kw)

    db.commit()
    for kw in created:
        db.refresh(kw)
    return created


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
