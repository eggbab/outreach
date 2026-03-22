from sqlalchemy.orm import Session

from app.models.models import EmailLog, DmLog, Prospect


def calculate_score(db: Session, prospect: Prospect) -> int:
    """Calculate a prospect score based on available data and engagement."""
    score = 0

    # Contact info availability
    if prospect.email:
        score += 10
    if prospect.phone:
        score += 10
    if prospect.instagram:
        score += 5
    if prospect.website:
        score += 5

    # Email engagement
    email_logs = (
        db.query(EmailLog)
        .filter(EmailLog.prospect_id == prospect.id, EmailLog.status == "success")
        .all()
    )
    for log in email_logs:
        score += 5  # email was sent
        if log.opened_at:
            score += 15
        if log.clicked_at:
            score += 25

    # DM engagement
    dm_count = (
        db.query(DmLog)
        .filter(DmLog.prospect_id == prospect.id, DmLog.status == "success")
        .count()
    )
    score += dm_count * 10

    return min(score, 100)
