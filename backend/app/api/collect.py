import threading
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db, SessionLocal
from app.core.security import get_current_user
from app.models.models import Project, User
from app.services.collector.manager import CollectionManager, collection_status_store

router = APIRouter(
    prefix="/api/projects/{project_id}",
    tags=["collect"],
)


class CollectResponse(BaseModel):
    message: str
    status: str


class CollectionStatusResponse(BaseModel):
    status: str  # idle, running, completed, failed
    total_keywords: int = 0
    processed_keywords: int = 0
    prospects_found: int = 0
    current_keyword: Optional[str] = None
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


def _run_collection_in_background(project_id: int, user_id: int):
    """Run collection in a background thread with its own DB session."""
    db = SessionLocal()
    try:
        manager = CollectionManager(db)
        manager.run_collection(project_id, user_id)
    except Exception as e:
        key = f"{user_id}:{project_id}"
        collection_status_store[key] = {
            "status": "failed",
            "error": str(e),
            "total_keywords": 0,
            "processed_keywords": 0,
            "prospects_found": 0,
            "current_keyword": None,
        }
    finally:
        db.close()


@router.post("/collect", response_model=CollectResponse)
def start_collection(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _get_project_or_404(project_id, current_user.id, db)

    key = f"{current_user.id}:{project_id}"
    current = collection_status_store.get(key, {})
    if current.get("status") == "running":
        raise HTTPException(
            status_code=400,
            detail="Collection is already running for this project",
        )

    keywords = project.keywords
    if not keywords:
        raise HTTPException(
            status_code=400,
            detail="No keywords configured for this project. Add keywords first.",
        )

    # Initialize status
    collection_status_store[key] = {
        "status": "running",
        "total_keywords": len(keywords),
        "processed_keywords": 0,
        "prospects_found": 0,
        "current_keyword": None,
        "error": None,
    }

    thread = threading.Thread(
        target=_run_collection_in_background,
        args=(project_id, current_user.id),
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

    key = f"{current_user.id}:{project_id}"
    status_data = collection_status_store.get(key)

    if not status_data:
        return CollectionStatusResponse(status="idle")

    return CollectionStatusResponse(**status_data)
