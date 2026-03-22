import base64
import uuid
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.plans import CREDIT_PACKAGES, add_credits
from app.core.security import get_current_user
from app.models.models import CreditTransaction, User

router = APIRouter(prefix="/api/payments", tags=["payments"])

TOSS_CONFIRM_URL = "https://api.tosspayments.com/v1/payments/confirm"


class PaymentConfirmRequest(BaseModel):
    paymentKey: str
    orderId: str
    amount: int


class PrepareResponse(BaseModel):
    orderId: str
    clientKey: str
    amount: int
    packageId: str


class PrepareRequest(BaseModel):
    package_id: str


class PaymentHistoryResponse(BaseModel):
    id: int
    amount: int
    balance_after: int
    description: str
    tx_type: str
    created_at: datetime

    model_config = {"from_attributes": True}


@router.post("/prepare", response_model=PrepareResponse)
def prepare_payment(
    req: PrepareRequest,
    current_user: User = Depends(get_current_user),
):
    """Generate orderId and return client key for frontend Toss widget."""
    if current_user.plan in ("free", "personal"):
        raise HTTPException(status_code=400, detail="유료 플랜에서만 크레딧을 충전할 수 있습니다.")

    package = next((p for p in CREDIT_PACKAGES if p["id"] == req.package_id), None)
    if not package:
        raise HTTPException(status_code=400, detail="Invalid package")

    order_id = f"credit-{current_user.id}-{uuid.uuid4().hex[:12]}"

    return PrepareResponse(
        orderId=order_id,
        clientKey=settings.TOSS_CLIENT_KEY,
        amount=package["price"],
        packageId=package["id"],
    )


@router.post("/confirm")
def confirm_payment(
    req: PaymentConfirmRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Confirm payment with Toss API and add credits to user."""
    if current_user.plan in ("free", "personal"):
        raise HTTPException(status_code=400, detail="유료 플랜에서만 크레딧을 충전할 수 있습니다.")

    # Find matching package by amount
    package = next((p for p in CREDIT_PACKAGES if p["price"] == req.amount), None)
    if not package:
        raise HTTPException(status_code=400, detail="Invalid payment amount")

    # Call Toss API to confirm payment
    secret_b64 = base64.b64encode(f"{settings.TOSS_SECRET_KEY}:".encode()).decode()

    try:
        with httpx.Client(timeout=30) as client:
            response = client.post(
                TOSS_CONFIRM_URL,
                headers={
                    "Authorization": f"Basic {secret_b64}",
                    "Content-Type": "application/json",
                },
                json={
                    "paymentKey": req.paymentKey,
                    "orderId": req.orderId,
                    "amount": req.amount,
                },
            )
    except httpx.RequestError:
        raise HTTPException(status_code=502, detail="결제 서버 연결 실패")

    if response.status_code != 200:
        error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
        raise HTTPException(
            status_code=400,
            detail=error_data.get("message", "결제 확인 실패"),
        )

    # Payment confirmed — add credits
    bonus = 0
    if "bonus" in package:
        bonus = int(package["credits"] * 0.2)

    total = package["credits"] + bonus
    description = f"크레딧 충전: {package['label']}" + (f" (+{bonus} 보너스)" if bonus else "")
    add_credits(db, current_user.id, total, description, tx_type="purchase")
    db.commit()
    db.refresh(current_user)

    return {
        "status": "success",
        "credits": current_user.credits,
        "added": total,
    }


@router.get("/history", response_model=list[PaymentHistoryResponse])
def get_payment_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return user's credit transaction history (purchases only)."""
    return (
        db.query(CreditTransaction)
        .filter(
            CreditTransaction.user_id == current_user.id,
            CreditTransaction.tx_type == "purchase",
        )
        .order_by(CreditTransaction.created_at.desc())
        .limit(50)
        .all()
    )
