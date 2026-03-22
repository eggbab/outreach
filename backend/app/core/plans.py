from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

PLAN_LIMITS = {
    "free": {"projects": 1, "daily_emails": 3, "daily_dms": 2, "daily_prospects": 10},
    "personal": {"projects": 1, "daily_emails": 3, "daily_dms": 2, "daily_prospects": 10},
    "pro": {"projects": 10, "daily_emails": 100, "daily_dms": 30, "daily_prospects": 500},
    "agency": {"projects": -1, "daily_emails": 500, "daily_dms": 100, "daily_prospects": 2000},
}

# 건당 크레딧 차감 (유료 플랜만, 한도 초과 시)
OVERAGE_CREDITS = {
    "email": 5,      # 이메일 1건 = 5 크레딧
    "dm": 10,         # DM 1건 = 10 크레딧
    "prospect": 2,    # 수집 1건 = 2 크레딧
}

# 크레딧 충전 패키지
CREDIT_PACKAGES = [
    {"id": "credits_500", "credits": 500, "price": 5000, "label": "500 크레딧", "price_label": "5,000원"},
    {"id": "credits_2000", "credits": 2000, "price": 15000, "label": "2,000 크레딧", "price_label": "15,000원", "popular": True},
    {"id": "credits_5000", "credits": 5000, "price": 30000, "label": "5,000 크레딧", "price_label": "30,000원", "bonus": "20% 보너스"},
]


def get_plan_limits(plan: str) -> dict:
    return PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])


def get_or_create_usage(db: Session, user_id: int):
    from app.models.models import UsageRecord
    from sqlalchemy.exc import IntegrityError

    today = date.today()
    record = (
        db.query(UsageRecord)
        .filter(UsageRecord.user_id == user_id, UsageRecord.date == today)
        .first()
    )
    if not record:
        try:
            record = UsageRecord(user_id=user_id, date=today)
            db.add(record)
            db.flush()
        except IntegrityError:
            db.rollback()
            record = (
                db.query(UsageRecord)
                .filter(UsageRecord.user_id == user_id, UsageRecord.date == today)
                .first()
            )
    return record


def check_usage_limit(db: Session, user_id: int, plan: str, resource: str) -> dict:
    """Check if user is within their plan limit for the given resource.
    Returns dict:
      {"allowed": True, "within_plan": True} — 플랜 한도 내
      {"allowed": True, "within_plan": False, "credits_needed": N} — 한도 초과, 크레딧 차감 가능 (유료)
      {"allowed": False, "reason": "..."} — 사용 불가
    resource: 'daily_emails', 'daily_dms', 'daily_prospects'
    """
    limits = get_plan_limits(plan)
    limit = limits.get(resource, 0)
    if limit == -1:
        return {"allowed": True, "within_plan": True}

    record = get_or_create_usage(db, user_id)
    field_map = {
        "daily_emails": record.emails_sent,
        "daily_dms": record.dms_sent,
        "daily_prospects": record.prospects_collected,
    }
    current = field_map.get(resource, 0)

    if current < limit:
        return {"allowed": True, "within_plan": True}

    # 한도 초과 — 무료 플랜은 차단, 유료 플랜은 크레딧 사용
    if plan in ("free", "personal"):
        return {"allowed": False, "reason": "free_limit"}

    # 유료 플랜: 크레딧 확인
    overage_key = {"daily_emails": "email", "daily_dms": "dm", "daily_prospects": "prospect"}.get(resource)
    credits_needed = OVERAGE_CREDITS.get(overage_key, 5)

    from app.models.models import User
    user = db.query(User).filter(User.id == user_id).first()
    if user and user.credits >= credits_needed:
        return {"allowed": True, "within_plan": False, "credits_needed": credits_needed}

    return {"allowed": False, "reason": "no_credits", "credits_needed": credits_needed}


def deduct_credits(db: Session, user_id: int, amount: int, description: str):
    """Deduct credits and record transaction. Returns remaining credits."""
    from app.models.models import CreditTransaction, User

    user = db.query(User).filter(User.id == user_id).first()
    if not user or user.credits < amount:
        return None

    user.credits -= amount
    tx = CreditTransaction(
        user_id=user_id,
        amount=-amount,
        balance_after=user.credits,
        description=description,
        tx_type="deduct",
    )
    db.add(tx)
    db.flush()
    return user.credits


def add_credits(db: Session, user_id: int, amount: int, description: str, tx_type: str = "purchase"):
    """Add credits and record transaction. Returns new balance."""
    from app.models.models import CreditTransaction, User

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None

    user.credits += amount
    tx = CreditTransaction(
        user_id=user_id,
        amount=amount,
        balance_after=user.credits,
        description=description,
        tx_type=tx_type,
    )
    db.add(tx)
    db.flush()
    return user.credits


def check_project_limit(db: Session, user_id: int, plan: str) -> bool:
    from app.models.models import Project

    limits = get_plan_limits(plan)
    max_projects = limits["projects"]
    if max_projects == -1:
        return True
    count = db.query(Project).filter(Project.user_id == user_id).count()
    return count < max_projects


def increment_usage(db: Session, user_id: int, resource: str, amount: int = 1):
    """Increment usage counter. resource: 'emails_sent', 'dms_sent', 'prospects_collected'"""
    record = get_or_create_usage(db, user_id)
    current = getattr(record, resource, 0)
    setattr(record, resource, current + amount)
    db.flush()
