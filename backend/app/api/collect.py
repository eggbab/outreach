import threading
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

limiter = Limiter(key_func=get_remote_address)

from app.core.database import get_db, SessionLocal
from app.core.security import get_current_user
from app.models.models import CollectionJob, Project, User
from app.services.collector.manager import CollectionManager

router = APIRouter(
    prefix="/api/projects/{project_id}",
    tags=["collect"],
)


class CollectRequest(BaseModel):
    sources: list[str] | None = None  # e.g. ["naver", "google"]


class CollectResponse(BaseModel):
    message: str
    status: str


class CollectionStatusResponse(BaseModel):
    status: str  # idle, running, completed, error
    current: int = 0
    total: int = 0
    message: Optional[str] = None
    prospects_found: int = 0
    error: Optional[str] = None


def _get_project_or_404(project_id: int, user_id: int, db: Session) -> Project:
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.user_id == user_id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _run_collection_in_background(project_id: int, user_id: int, sources: list[str] | None = None):
    """Run collection in a background thread with its own DB session."""
    db = SessionLocal()
    try:
        manager = CollectionManager(db)
        manager.run_collection(project_id, user_id, sources=sources)
    except Exception as e:
        # Update job status on failure
        job = (
            db.query(CollectionJob)
            .filter(CollectionJob.project_id == project_id, CollectionJob.user_id == user_id)
            .order_by(CollectionJob.started_at.desc())
            .first()
        )
        if job:
            job.status = "failed"
            job.error = str(e)
            db.commit()
    finally:
        db.close()


@router.post("/collect", response_model=CollectResponse)
@limiter.limit("5/minute")
def start_collection(
    request: Request,
    project_id: int,
    req: CollectRequest = CollectRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _get_project_or_404(project_id, current_user.id, db)

    # Check if collection is already running
    running_job = (
        db.query(CollectionJob)
        .filter(
            CollectionJob.project_id == project_id,
            CollectionJob.user_id == current_user.id,
            CollectionJob.status == "running",
        )
        .first()
    )
    if running_job:
        raise HTTPException(
            status_code=400,
            detail="Collection is already running for this project",
        )

    # Check usage limit
    from app.core.plans import check_usage_limit, deduct_credits
    usage_check = check_usage_limit(db, current_user.id, current_user.plan, "daily_prospects")
    if not usage_check["allowed"]:
        if usage_check.get("reason") == "free_limit":
            raise HTTPException(status_code=429, detail="무료 플랜의 일일 수집 한도에 도달했습니다. 유료 플랜으로 업그레이드해주세요.")
        else:
            raise HTTPException(status_code=429, detail=f"일일 수집 한도 초과. 크레딧이 부족합니다. (필요: {usage_check.get('credits_needed', 0)} 크레딧)")
    if not usage_check.get("within_plan", True):
        deduct_credits(db, current_user.id, usage_check["credits_needed"], "수집 한도 초과 — 건당 과금")
        db.commit()

    keywords = project.keywords
    if not keywords:
        raise HTTPException(
            status_code=400,
            detail="No keywords configured for this project. Add keywords first.",
        )

    sources = req.sources or ["naver", "google"]

    thread = threading.Thread(
        target=_run_collection_in_background,
        args=(project_id, current_user.id, sources),
        daemon=True,
    )
    thread.start()

    return CollectResponse(
        message=f"Collection started for {len(keywords)} keywords x {len(sources)} sources",
        status="running",
    )


@router.get("/collect/status", response_model=CollectionStatusResponse)
def get_collection_status(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_project_or_404(project_id, current_user.id, db)

    job = (
        db.query(CollectionJob)
        .filter(
            CollectionJob.project_id == project_id,
            CollectionJob.user_id == current_user.id,
        )
        .order_by(CollectionJob.started_at.desc())
        .first()
    )

    if not job:
        return CollectionStatusResponse(status="idle")

    st = job.status
    if st == "failed":
        st = "error"

    return CollectionStatusResponse(
        status=st,
        current=job.processed_tasks,
        total=job.total_tasks,
        message=job.current_task,
        prospects_found=job.prospects_found,
        error=job.error,
    )
