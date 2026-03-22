from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import EmailLog, DmLog, Project, Prospect, User

router = APIRouter(prefix="/api/projects", tags=["projects"])


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None


class ProjectResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProjectDetailResponse(ProjectResponse):
    prospect_count: int = 0
    approved_count: int = 0
    email_sent_count: int = 0
    dm_sent_count: int = 0


@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    req: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.core.plans import check_project_limit
    if not check_project_limit(db, current_user.id, current_user.plan):
        raise HTTPException(
            status_code=429,
            detail="프로젝트 생성 한도에 도달했습니다. 플랜을 업그레이드해주세요.",
        )
    project = Project(name=req.name, description=req.description, user_id=current_user.id)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("/", response_model=list[ProjectResponse])
def list_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(Project)
        .filter(Project.user_id == current_user.id)
        .order_by(Project.created_at.desc())
        .all()
    )


@router.get("/{project_id}", response_model=ProjectDetailResponse)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.user_id == current_user.id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    counts = (
        db.query(
            func.count(Prospect.id).label("total"),
            func.sum(case((Prospect.status == "approved", 1), else_=0)).label("approved"),
            func.sum(case((Prospect.status == "email_sent", 1), else_=0)).label("email_sent"),
            func.sum(case((Prospect.status == "dm_sent", 1), else_=0)).label("dm_sent"),
        )
        .filter(Prospect.project_id == project_id)
        .first()
    )

    return ProjectDetailResponse(
        id=project.id,
        name=project.name,
        status=project.status,
        created_at=project.created_at,
        updated_at=project.updated_at,
        prospect_count=counts.total or 0,
        approved_count=int(counts.approved or 0),
        email_sent_count=int(counts.email_sent or 0),
        dm_sent_count=int(counts.dm_sent or 0),
    )


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.user_id == current_user.id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    db.delete(project)
    db.commit()
