import logging

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.models import (
    Deal, EmailLog, Keyword, KeywordPerformance,
    PipelineStage, Project, Prospect,
)

logger = logging.getLogger(__name__)


def compute_keyword_performances(db: Session):
    """Compute ROI metrics for each keyword per user."""

    keywords = db.query(Keyword).all()

    for kw in keywords:
        project = db.query(Project).filter(Project.id == kw.project_id).first()
        if not project:
            continue
        user_id = project.user_id

        # Count prospects collected with this keyword
        prospect_ids_q = (
            db.query(Prospect.id)
            .filter(Prospect.keyword_id == kw.id)
        )
        prospect_ids = [r[0] for r in prospect_ids_q.all()]
        total_collected = len(prospect_ids)

        if total_collected == 0:
            continue

        # Email stats
        total_emailed = 0
        total_opened = 0
        total_clicked = 0
        if prospect_ids:
            email_stats = (
                db.query(
                    func.count(EmailLog.id),
                    func.count(EmailLog.opened_at),
                    func.count(EmailLog.clicked_at),
                )
                .filter(
                    EmailLog.prospect_id.in_(prospect_ids),
                    EmailLog.status == "success",
                )
                .first()
            )
            if email_stats:
                total_emailed = email_stats[0] or 0
                total_opened = email_stats[1] or 0
                total_clicked = email_stats[2] or 0

        # Deal stats
        total_deals = 0
        total_deal_value = 0
        if prospect_ids:
            # Only count won deals
            won_stage_ids = (
                db.query(PipelineStage.id)
                .filter(PipelineStage.user_id == user_id, PipelineStage.is_won.is_(True))
                .subquery()
            )
            deal_stats = (
                db.query(func.count(Deal.id), func.coalesce(func.sum(Deal.value), 0))
                .filter(
                    Deal.prospect_id.in_(prospect_ids),
                    Deal.stage_id.in_(won_stage_ids),
                )
                .first()
            )
            if deal_stats:
                total_deals = deal_stats[0] or 0
                total_deal_value = deal_stats[1] or 0

        conversion_rate = (total_deals / total_collected) if total_collected > 0 else 0
        roi_score = (total_deal_value / total_collected) if total_collected > 0 else 0

        # Upsert
        existing = (
            db.query(KeywordPerformance)
            .filter(KeywordPerformance.keyword_id == kw.id, KeywordPerformance.user_id == user_id)
            .first()
        )
        if existing:
            existing.keyword_text = kw.keyword
            existing.source = kw.source
            existing.total_collected = total_collected
            existing.total_emailed = total_emailed
            existing.total_opened = total_opened
            existing.total_clicked = total_clicked
            existing.total_deals = total_deals
            existing.total_deal_value = total_deal_value
            existing.conversion_rate = round(conversion_rate, 4)
            existing.roi_score = round(roi_score, 2)
        else:
            kp = KeywordPerformance(
                keyword_id=kw.id,
                user_id=user_id,
                keyword_text=kw.keyword,
                source=kw.source,
                total_collected=total_collected,
                total_emailed=total_emailed,
                total_opened=total_opened,
                total_clicked=total_clicked,
                total_deals=total_deals,
                total_deal_value=total_deal_value,
                conversion_rate=round(conversion_rate, 4),
                roi_score=round(roi_score, 2),
            )
            db.add(kp)

    logger.info(f"Computed keyword performances for {len(keywords)} keywords")
