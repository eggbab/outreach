from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.plans import (
    CREDIT_PACKAGES,
    OVERAGE_CREDITS,
    add_credits,
    get_or_create_usage,
    get_plan_limits,
)
from app.core.security import get_current_user
from app.models.models import CreditTransaction, Subscription, User

router = APIRouter(prefix="/api/subscription", tags=["subscription"])


class SubscriptionResponse(BaseModel):
    plan: str
    status: str
    credits: int = 0
    current_period_start: datetime | None = None
    current_period_end: datetime | None = None
    cancel_at_period_end: bool = False
    trial_ends_at: datetime | None = None

    model_config = {"from_attributes": True}


class UsageResponse(BaseModel):
    emails_sent: int = 0
    dms_sent: int = 0
    prospects_collected: int = 0
    limits: dict
    credits: int = 0
    overage_rates: dict


class PlanChangeRequest(BaseModel):
    plan: str


class CreditPurchaseRequest(BaseModel):
    package_id: str


class CreditTransactionResponse(BaseModel):
    id: int
    amount: int
    balance_after: int
    description: str
    tx_type: str
    created_at: datetime

    model_config = {"from_attributes": True}


@router.get("/", response_model=SubscriptionResponse)
def get_subscription(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sub = db.query(Subscription).filter(Subscription.user_id == current_user.id).first()
    return SubscriptionResponse(
        plan=sub.plan if sub else current_user.plan,
        status=sub.status if sub else "active",
        credits=current_user.credits,
        current_period_start=sub.current_period_start if sub else None,
        current_period_end=sub.current_period_end if sub else None,
        cancel_at_period_end=sub.cancel_at_period_end if sub else False,
        trial_ends_at=current_user.trial_ends_at,
    )


@router.get("/usage", response_model=UsageResponse)
def get_usage(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = get_or_create_usage(db, current_user.id)
    db.commit()
    limits = get_plan_limits(current_user.plan)
    return UsageResponse(
        emails_sent=record.emails_sent,
        dms_sent=record.dms_sent,
        prospects_collected=record.prospects_collected,
        limits=limits,
        credits=current_user.credits,
        overage_rates=OVERAGE_CREDITS,
    )


@router.get("/credit-packages")
def get_credit_packages():
    return CREDIT_PACKAGES


@router.post("/purchase-credits", response_model=SubscriptionResponse)
def purchase_credits(
    req: CreditPurchaseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.plan in ("free", "personal"):
        raise HTTPException(status_code=400, detail="유료 플랜에서만 크레딧을 충전할 수 있습니다.")

    package = next((p for p in CREDIT_PACKAGES if p["id"] == req.package_id), None)
    if not package:
        raise HTTPException(status_code=400, detail="Invalid package")

    bonus = 0
    if "bonus" in package:
        # 20% bonus
        bonus = int(package["credits"] * 0.2)

    total = package["credits"] + bonus
    add_credits(db, current_user.id, total, f"크레딧 충전: {package['label']}" + (f" (+{bonus} 보너스)" if bonus else ""), tx_type="purchase")
    db.commit()
    db.refresh(current_user)

    sub = db.query(Subscription).filter(Subscription.user_id == current_user.id).first()
    return SubscriptionResponse(
        plan=current_user.plan,
        status=sub.status if sub else "active",
        credits=current_user.credits,
        trial_ends_at=current_user.trial_ends_at,
    )


@router.get("/credit-history", response_model=list[CreditTransactionResponse])
def get_credit_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(CreditTransaction)
        .filter(CreditTransaction.user_id == current_user.id)
        .order_by(CreditTransaction.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )


@router.post("/upgrade", response_model=SubscriptionResponse)
def upgrade_plan(
    req: PlanChangeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    plan_order = {"free": 0, "personal": 0, "pro": 1, "agency": 2}
    if plan_order.get(req.plan, 0) <= plan_order.get(current_user.plan, 0):
        raise HTTPException(status_code=400, detail="Can only upgrade to a higher plan")

    now = datetime.now(timezone.utc)
    current_user.plan = req.plan
    current_user.plan_changed_at = now
    current_user.trial_started_at = None
    current_user.trial_ends_at = None

    sub = db.query(Subscription).filter(Subscription.user_id == current_user.id).first()
    if not sub:
        sub = Subscription(user_id=current_user.id)
        db.add(sub)
    sub.plan = req.plan
    sub.status = "active"
    sub.current_period_start = now
    sub.cancel_at_period_end = False

    db.commit()
    return SubscriptionResponse(
        plan=sub.plan,
        status=sub.status,
        credits=current_user.credits,
        current_period_start=sub.current_period_start,
        current_period_end=sub.current_period_end,
        cancel_at_period_end=sub.cancel_at_period_end,
        trial_ends_at=current_user.trial_ends_at,
    )


@router.post("/downgrade", response_model=SubscriptionResponse)
def downgrade_plan(
    req: PlanChangeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    plan_order = {"free": 0, "personal": 0, "pro": 1, "agency": 2}
    if plan_order.get(req.plan, 0) >= plan_order.get(current_user.plan, 0):
        raise HTTPException(status_code=400, detail="Can only downgrade to a lower plan")

    now = datetime.now(timezone.utc)
    current_user.plan = req.plan
    current_user.plan_changed_at = now

    sub = db.query(Subscription).filter(Subscription.user_id == current_user.id).first()
    if sub:
        sub.plan = req.plan
        sub.cancel_at_period_end = False
    db.commit()

    return SubscriptionResponse(
        plan=current_user.plan,
        status=sub.status if sub else "active",
        credits=current_user.credits,
        current_period_start=sub.current_period_start if sub else None,
        current_period_end=sub.current_period_end if sub else None,
        cancel_at_period_end=sub.cancel_at_period_end if sub else False,
        trial_ends_at=current_user.trial_ends_at,
    )
