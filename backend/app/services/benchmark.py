import logging
from collections import defaultdict

from sqlalchemy.orm import Session

from app.models.models import EmailLog, IndustryBenchmark, Prospect
from app.services.collector.manager import _classify_industry

logger = logging.getLogger(__name__)


def compute_benchmarks(db: Session):
    """Aggregate email stats by industry and upsert IndustryBenchmark records."""

    # Get all successful email logs with prospect info
    rows = (
        db.query(
            Prospect.category,
            EmailLog.user_id,
            EmailLog.opened_at,
            EmailLog.clicked_at,
            EmailLog.sent_at,
        )
        .join(Prospect, EmailLog.prospect_id == Prospect.id)
        .filter(EmailLog.status == "success")
        .all()
    )

    # Aggregate by industry
    industry_data = defaultdict(lambda: {
        "total_sent": 0, "total_opened": 0, "total_clicked": 0,
        "users": set(), "hour_opens": defaultdict(int), "day_opens": defaultdict(int),
    })

    for category, user_id, opened_at, clicked_at, sent_at in rows:
        industry = _classify_industry(category)
        if not industry:
            continue

        d = industry_data[industry]
        d["total_sent"] += 1
        d["users"].add(user_id)
        if opened_at:
            d["total_opened"] += 1
            d["hour_opens"][opened_at.hour] += 1
            d["day_opens"][opened_at.weekday()] += 1
        if clicked_at:
            d["total_clicked"] += 1

    # Upsert benchmarks (only for industries with 50+ sends)
    for industry, data in industry_data.items():
        if data["total_sent"] < 50:
            continue

        avg_open = (data["total_opened"] / data["total_sent"] * 100) if data["total_sent"] > 0 else 0
        avg_click = (data["total_clicked"] / data["total_sent"] * 100) if data["total_sent"] > 0 else 0

        best_hour = max(data["hour_opens"], key=data["hour_opens"].get) if data["hour_opens"] else None
        best_day = max(data["day_opens"], key=data["day_opens"].get) if data["day_opens"] else None

        existing = db.query(IndustryBenchmark).filter(IndustryBenchmark.industry == industry).first()
        if existing:
            existing.total_sent = data["total_sent"]
            existing.total_opened = data["total_opened"]
            existing.total_clicked = data["total_clicked"]
            existing.avg_open_rate = round(avg_open, 1)
            existing.avg_click_rate = round(avg_click, 1)
            existing.best_send_hour = best_hour
            existing.best_send_day = best_day
            existing.sample_size = len(data["users"])
        else:
            bm = IndustryBenchmark(
                industry=industry,
                total_sent=data["total_sent"],
                total_opened=data["total_opened"],
                total_clicked=data["total_clicked"],
                avg_open_rate=round(avg_open, 1),
                avg_click_rate=round(avg_click, 1),
                best_send_hour=best_hour,
                best_send_day=best_day,
                sample_size=len(data["users"]),
            )
            db.add(bm)

    logger.info(f"Computed benchmarks for {len(industry_data)} industries")
