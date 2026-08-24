"""
계좌이체 기반 결제.

흐름:
1. 사용자가 패키지 선택 → GET /api/payments/bank-info 로 계좌 정보 받음
2. 사용자가 직접 계좌이체 후 → POST /api/payments/request 로 입금자명 알림
3. 관리자가 통장 확인 후 → POST /api/admin/payment-requests/:id/approve → 크레딧 자동 충전
4. 또는 거절 → POST /api/admin/payment-requests/:id/reject (사유 포함)
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import settings as app_settings
from app.core.database import get_db
from app.core.plans import CREDIT_PACKAGES, add_credits
from app.core.security import get_current_user
from app.models.models import PaymentRequest, User

router = APIRouter(prefix="/api/payments", tags=["payments"])


class BankInfoResponse(BaseModel):
    bank_name: str
    bank_account: str
    bank_holder: str
    configured: bool


class PaymentRequestCreate(BaseModel):
    package_id: str
    depositor_name: str = Field(..., min_length=1, max_length=100)
    memo: Optional[str] = Field(None, max_length=500)


class PaymentRequestResponse(BaseModel):
    id: int
    package_id: str
    package_label: str
    credits: int
    amount: int
    depositor_name: str
    memo: Optional[str] = None
    status: str
    rejection_reason: Optional[str] = None
    created_at: datetime
    approved_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


@router.get("/bank-info", response_model=BankInfoResponse)
def get_bank_info():
    """입금받을 계좌 정보 (관리자가 .env에서 설정). 누구나 조회 가능."""
    return BankInfoResponse(
        bank_name=app_settings.BANK_NAME,
        bank_account=app_settings.BANK_ACCOUNT,
        bank_holder=app_settings.BANK_HOLDER,
        configured=bool(app_settings.BANK_NAME and app_settings.BANK_ACCOUNT),
    )


@router.post("/request", response_model=PaymentRequestResponse, status_code=201)
def create_payment_request(
    req: PaymentRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """사용자가 입금 완료 후 호출 — 관리자에게 승인 요청을 만듦."""
    package = next((p for p in CREDIT_PACKAGES if p["id"] == req.package_id), None)
    if not package:
        raise HTTPException(status_code=400, detail="유효하지 않은 패키지입니다")

    # 같은 사용자의 pending 요청이 너무 많으면 거부 (스팸 방지)
    pending_count = (
        db.query(PaymentRequest)
        .filter(PaymentRequest.user_id == current_user.id, PaymentRequest.status == "pending")
        .count()
    )
    if pending_count >= 5:
        raise HTTPException(
            status_code=429,
            detail="처리되지 않은 결제 요청이 5건 있습니다. 관리자 승인을 기다려주세요.",
        )

    pr = PaymentRequest(
        user_id=current_user.id,
        package_id=package["id"],
        package_label=package["label"],
        credits=package["credits"],
        amount=package["price"],
        depositor_name=req.depositor_name.strip(),
        memo=(req.memo or "").strip() or None,
        status="pending",
    )
    db.add(pr)
    db.commit()
    db.refresh(pr)
    return pr


@router.get("/my-requests", response_model=list[PaymentRequestResponse])
def my_payment_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(PaymentRequest)
        .filter(PaymentRequest.user_id == current_user.id)
        .order_by(PaymentRequest.created_at.desc())
        .limit(50)
        .all()
    )


# ──────────────────────────────────────
# 관리자 — 결제 요청 승인/거절
# ──────────────────────────────────────

class AdminPaymentRequestSummary(PaymentRequestResponse):
    user_email: str
    user_name: str


class RejectRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500)


def _require_admin(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다")
    return current_user


admin_router = APIRouter(prefix="/api/admin/payment-requests", tags=["admin-payments"])


@admin_router.get("/", response_model=list[AdminPaymentRequestSummary])
def list_payment_requests(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    admin: User = Depends(_require_admin),
):
    query = db.query(PaymentRequest)
    if status:
        if status not in ("pending", "approved", "rejected"):
            raise HTTPException(status_code=400, detail="유효하지 않은 상태입니다")
        query = query.filter(PaymentRequest.status == status)
    items = query.order_by(PaymentRequest.created_at.desc()).limit(200).all()

    out = []
    for pr in items:
        u = db.query(User).filter(User.id == pr.user_id).first()
        out.append(AdminPaymentRequestSummary(
            id=pr.id, package_id=pr.package_id, package_label=pr.package_label,
            credits=pr.credits, amount=pr.amount, depositor_name=pr.depositor_name,
            memo=pr.memo, status=pr.status, rejection_reason=pr.rejection_reason,
            created_at=pr.created_at, approved_at=pr.approved_at,
            user_email=u.email if u else "삭제된 사용자",
            user_name=u.name if u else "-",
        ))
    return out


@admin_router.post("/{request_id}/approve")
def approve_payment_request(
    request_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(_require_admin),
):
    pr = db.query(PaymentRequest).filter(PaymentRequest.id == request_id).first()
    if not pr:
        raise HTTPException(status_code=404, detail="결제 요청을 찾을 수 없습니다")
    if pr.status != "pending":
        raise HTTPException(status_code=400, detail=f"이미 {pr.status} 처리된 요청입니다")

    add_credits(
        db, pr.user_id, pr.credits,
        f"계좌이체 충전: {pr.package_label} (입금자: {pr.depositor_name})",
        tx_type="purchase",
    )
    pr.status = "approved"
    pr.approved_by_admin_id = admin.id
    pr.approved_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": "승인되었습니다", "credits_added": pr.credits}


@admin_router.post("/{request_id}/reject")
def reject_payment_request(
    request_id: int,
    req: RejectRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(_require_admin),
):
    pr = db.query(PaymentRequest).filter(PaymentRequest.id == request_id).first()
    if not pr:
        raise HTTPException(status_code=404, detail="결제 요청을 찾을 수 없습니다")
    if pr.status != "pending":
        raise HTTPException(status_code=400, detail=f"이미 {pr.status} 처리된 요청입니다")
    pr.status = "rejected"
    pr.rejection_reason = req.reason
    pr.approved_by_admin_id = admin.id
    pr.approved_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": "거절되었습니다"}
