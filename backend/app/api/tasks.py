"""영업 할 일(태스크) — 마감일 있는 후속 작업 관리."""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import Prospect, TaskItem, User

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


class TaskCreate(BaseModel):
    title: str
    memo: Optional[str] = None
    due_at: Optional[datetime] = None
    prospect_id: Optional[int] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    memo: Optional[str] = None
    due_at: Optional[datetime] = None
    done: Optional[bool] = None


class TaskResponse(BaseModel):
    id: int
    title: str
    memo: Optional[str] = None
    due_at: Optional[datetime] = None
    done: bool
    prospect_id: Optional[int] = None
    prospect_name: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


def _to_response(db: Session, t: TaskItem) -> TaskResponse:
    name = None
    if t.prospect_id:
        p = db.query(Prospect.name).filter(Prospect.id == t.prospect_id).first()
        name = p[0] if p else None
    return TaskResponse(
        id=t.id, title=t.title, memo=t.memo, due_at=t.due_at, done=t.done,
        prospect_id=t.prospect_id, prospect_name=name, created_at=t.created_at,
    )


@router.get("/", response_model=list[TaskResponse])
def list_tasks(
    done: Optional[bool] = Query(None, description="완료 여부 필터"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(TaskItem).filter(TaskItem.user_id == current_user.id)
    if done is not None:
        q = q.filter(TaskItem.done == done)
    # 미완료는 마감 임박 순, 완료는 최근 순
    tasks = q.order_by(TaskItem.done, TaskItem.due_at.is_(None), TaskItem.due_at).limit(200).all()
    return [_to_response(db, t) for t in tasks]


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    req: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not req.title.strip():
        raise HTTPException(status_code=400, detail="제목을 입력하세요")
    # prospect_id가 있으면 소유 확인
    if req.prospect_id:
        from app.models.models import Project
        owned = (
            db.query(Prospect.id)
            .join(Project, Prospect.project_id == Project.id)
            .filter(Prospect.id == req.prospect_id, Project.user_id == current_user.id)
            .first()
        )
        if not owned:
            raise HTTPException(status_code=404, detail="잠재고객을 찾을 수 없습니다")

    t = TaskItem(
        user_id=current_user.id, title=req.title.strip()[:300],
        memo=req.memo, due_at=req.due_at, prospect_id=req.prospect_id,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return _to_response(db, t)


@router.patch("/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: int,
    req: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    t = db.query(TaskItem).filter(TaskItem.id == task_id, TaskItem.user_id == current_user.id).first()
    if not t:
        raise HTTPException(status_code=404, detail="할 일을 찾을 수 없습니다")
    if req.title is not None:
        t.title = req.title.strip()[:300]
    if req.memo is not None:
        t.memo = req.memo
    if req.due_at is not None:
        t.due_at = req.due_at
    if req.done is not None:
        t.done = req.done
        t.completed_at = datetime.now(timezone.utc) if req.done else None
    db.commit()
    db.refresh(t)
    return _to_response(db, t)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    t = db.query(TaskItem).filter(TaskItem.id == task_id, TaskItem.user_id == current_user.id).first()
    if not t:
        raise HTTPException(status_code=404, detail="할 일을 찾을 수 없습니다")
    db.delete(t)
    db.commit()
