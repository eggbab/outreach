import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.models import CollectionJob, Keyword, Prospect
from app.services.collector.google import search_google
from app.services.collector.instagram import search_instagram
from app.services.collector.naver import search_naver, search_naver_map, search_naver_shopping

logger = logging.getLogger(__name__)

# Map source types to their collector functions
SOURCE_COLLECTORS = {
    "naver": search_naver,
    "naver_shopping": search_naver_shopping,
    "naver_map": search_naver_map,
    "google": search_google,
    "instagram": search_instagram,
}


class CollectionManager:
    """Orchestrates prospect collection across all configured sources."""

    def __init__(self, db: Session):
        self.db = db

    def run_collection(self, project_id: int, user_id: int, sources: list[str] | None = None) -> None:
        """
        Run collection for all keywords in the project.
        If sources is provided, each keyword is collected from each specified source.
        Otherwise, falls back to the keyword's own source field.
        Updates progress in CollectionJob DB table.
        """
        keywords = (
            self.db.query(Keyword)
            .filter(Keyword.project_id == project_id)
            .all()
        )

        # Build task list: (keyword_text, source)
        tasks = []
        if sources:
            for kw in keywords:
                for src in sources:
                    tasks.append((kw.keyword, src))
        else:
            for kw in keywords:
                tasks.append((kw.keyword, kw.source))

        # Create or update job record
        job = (
            self.db.query(CollectionJob)
            .filter(CollectionJob.project_id == project_id, CollectionJob.user_id == user_id)
            .order_by(CollectionJob.started_at.desc())
            .first()
        )
        if not job or job.status != "running":
            job = CollectionJob(
                project_id=project_id,
                user_id=user_id,
                status="running",
                total_tasks=len(tasks),
                processed_tasks=0,
                prospects_found=0,
            )
            self.db.add(job)
            self.db.commit()
            self.db.refresh(job)

        if not tasks:
            job.status = "completed"
            job.completed_at = datetime.now(timezone.utc)
            self.db.commit()
            return

        total_prospects_found = 0

        for i, (keyword_text, source) in enumerate(tasks):
            job.processed_tasks = i
            job.current_task = f"{keyword_text} ({source})"
            job.prospects_found = total_prospects_found
            self.db.commit()

            try:
                collector_fn = SOURCE_COLLECTORS.get(source)
                if not collector_fn:
                    logger.warning(f"Unknown source: {source}")
                    continue

                raw_prospects = collector_fn(keyword_text)
                saved = self._save_prospects(project_id, raw_prospects)
                total_prospects_found += saved

            except Exception as e:
                logger.error(f"Error collecting '{keyword_text}' from {source}: {e}")
                continue

        job.status = "completed"
        job.processed_tasks = len(tasks)
        job.prospects_found = total_prospects_found
        job.current_task = None
        job.completed_at = datetime.now(timezone.utc)
        self.db.commit()

    def _save_prospects(self, project_id: int, raw_prospects: list[dict]) -> int:
        """Save prospects to DB, skipping duplicates. Returns count of newly saved."""
        saved_count = 0

        for data in raw_prospects:
            if not data.get("email") and not data.get("phone") and not data.get("instagram"):
                continue

            existing = None
            if data.get("email"):
                existing = (
                    self.db.query(Prospect)
                    .filter(Prospect.project_id == project_id, Prospect.email == data["email"])
                    .first()
                )
            if not existing and data.get("website"):
                existing = (
                    self.db.query(Prospect)
                    .filter(Prospect.project_id == project_id, Prospect.website == data["website"])
                    .first()
                )
            if not existing and data.get("instagram"):
                existing = (
                    self.db.query(Prospect)
                    .filter(Prospect.project_id == project_id, Prospect.instagram == data["instagram"])
                    .first()
                )

            if existing:
                if data.get("email") and not existing.email:
                    existing.email = data["email"]
                if data.get("phone") and not existing.phone:
                    existing.phone = data["phone"]
                if data.get("instagram") and not existing.instagram:
                    existing.instagram = data["instagram"]
                continue

            prospect = Prospect(
                project_id=project_id,
                name=data.get("name"),
                email=data.get("email"),
                phone=data.get("phone"),
                instagram=data.get("instagram"),
                website=data.get("website"),
                source=data.get("source"),
                category=data.get("category"),
                status="collected",
            )
            self.db.add(prospect)
            saved_count += 1

        self.db.commit()
        return saved_count
