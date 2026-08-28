from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.plans import (
    CREDIT_COSTS,
    CREDIT_PACKAGES,
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
    service_key: str | None = None        # 현재 등록해 쓰고 있는 키
    service_key_memo: str | None = None

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
    from app.models.models import ServiceKey
    sk = (db.query(ServiceKey).filter(ServiceKey.id == current_user.service_key_id).first()
          if current_user.service_key_id else None)
    return SubscriptionResponse(
        plan=sub.plan if sub else current_user.plan,
        status=sub.status if sub else "active",
        credits=current_user.credits,
        current_period_start=sub.current_period_start if sub else None,
        current_period_end=sub.current_period_end if sub else None,
        cancel_at_period_end=sub.cancel_at_period_end if sub else False,
        trial_ends_at=current_user.trial_ends_at,
        service_key=sk.key if sk else None,
        service_key_memo=sk.memo if sk else None,
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
        overage_rates=CREDIT_COSTS,
    )


@router.get("/credit-packages")
def get_credit_packages():
    return CREDIT_PACKAGES


# ⚠️ purchase-credits 라우트 제거 — 결제 검증 우회 취약점이었음.
# 정상 충전 흐름은 POST /api/payments/prepare → 토스 결제 → POST /api/payments/confirm.


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


# upgrade/downgrade 라우트 제거됨 — 결제 검증 없이 플랜을 바꿀 수 있던 권한 상승 경로.
# 플랜 변경은 관리자(PATCH /api/admin/users/:id) 또는 서비스 키 등록으로만 가능.
