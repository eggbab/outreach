import threading
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.rate_limit import limiter
from app.core.database import get_db, SessionLocal
from app.core.security import get_current_user
from app.models.models import CollectionJob, Project, User
from app.services.collector.manager import CollectionManager

router = APIRouter(
    prefix="/api/projects/{project_id}",
    tags=["collect"],
)


class CollectRequest(BaseModel):
    max_results: int = 20  # 키워드당 최대 수집 건수
    match_level: str = "medium"  # loose | medium | strict — 키워드 매칭 정밀도


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


def _run_collection_in_background(project_id: int, user_id: int, max_results: int = 20, match_level: str = "medium"):
    """Run collection in a background thread with its own DB session."""
    db = SessionLocal()
    try:
        manager = CollectionManager(db)
        manager.run_collection(project_id, user_id, max_results=max_results, match_level=match_level)
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

    # Check credits
    from app.core.plans import check_credits
    credit_check = check_credits(db, current_user.id, "prospect", 1)
    if not credit_check["allowed"]:
        raise HTTPException(status_code=402, detail=f"크레딧이 부족합니다. (잔액: {credit_check['balance']})")

    keywords = project.keywords
    if not keywords:
        raise HTTPException(
            status_code=400,
            detail="No keywords configured for this project. Add keywords first.",
        )

    max_results = max(1, min(req.max_results, 100))
    match_level = req.match_level if req.match_level in ("loose", "medium", "strict") else "medium"

    thread = threading.Thread(
        target=_run_collection_in_background,
        args=(project_id, current_user.id, max_results, match_level),
        daemon=True,
    )
    thread.start()

    return CollectResponse(
        message=f"Collection started for {len(keywords)} keywords",
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
