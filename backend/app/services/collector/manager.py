import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.models.models import Keyword, Prospect
from app.services.collector.google import search_google
from app.services.collector.instagram import search_instagram
from app.services.collector.naver import search_naver, search_naver_map, search_naver_shopping

logger = logging.getLogger(__name__)

# In-memory status store for collection progress.
# In production, use Redis or a DB table.
collection_status_store: dict[str, dict] = {}

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

    def run_collection(self, project_id: int, user_id: int) -> None:
        """
        Run collection for all keywords in the project.
        Updates progress in collection_status_store.
        """
        key = f"{user_id}:{project_id}"

        keywords = (
            self.db.query(Keyword)
            .filter(Keyword.project_id == project_id)
            .all()
        )

        if not keywords:
            collection_status_store[key] = {
                "status": "completed",
                "total_keywords": 0,
                "processed_keywords": 0,
                "prospects_found": 0,
                "current_keyword": None,
                "error": None,
            }
            return

        total_prospects_found = 0

        for i, kw in enumerate(keywords):
            # Update progress
            collection_status_store[key] = {
                "status": "running",
                "total_keywords": len(keywords),
                "processed_keywords": i,
                "prospects_found": total_prospects_found,
                "current_keyword": f"{kw.keyword} ({kw.source})",
                "error": None,
            }

            try:
                collector_fn = SOURCE_COLLECTORS.get(kw.source)
                if not collector_fn:
                    logger.warning(f"Unknown source: {kw.source}")
                    continue

                raw_prospects = collector_fn(kw.keyword)

                # Deduplicate and save to DB
                saved = self._save_prospects(project_id, raw_prospects)
                total_prospects_found += saved

            except Exception as e:
                logger.error(f"Error collecting '{kw.keyword}' from {kw.source}: {e}")
                continue

        # Final status
        collection_status_store[key] = {
            "status": "completed",
            "total_keywords": len(keywords),
            "processed_keywords": len(keywords),
            "prospects_found": total_prospects_found,
            "current_keyword": None,
            "error": None,
        }

    def _save_prospects(self, project_id: int, raw_prospects: list[dict]) -> int:
        """Save prospects to DB, skipping duplicates. Returns count of newly saved."""
        saved_count = 0

        for data in raw_prospects:
            # Skip if no useful contact info
            if not data.get("email") and not data.get("phone") and not data.get("instagram"):
                continue

            # Check for duplicates (same project, same email or same website)
            existing = None
            if data.get("email"):
                existing = (
                    self.db.query(Prospect)
                    .filter(
                        Prospect.project_id == project_id,
                        Prospect.email == data["email"],
                    )
                    .first()
                )
            if not existing and data.get("website"):
                existing = (
                    self.db.query(Prospect)
                    .filter(
                        Prospect.project_id == project_id,
                        Prospect.website == data["website"],
                    )
                    .first()
                )
            if not existing and data.get("instagram"):
                existing = (
                    self.db.query(Prospect)
                    .filter(
                        Prospect.project_id == project_id,
                        Prospect.instagram == data["instagram"],
                    )
                    .first()
                )

            if existing:
                # Update existing with new info if available
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
