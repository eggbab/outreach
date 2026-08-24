"""사장님 전용 관리자 API.

기능:
- 서비스 키 발급/관리 (기존)
- 사용자 목록·검색·정지·크레딧 부여
- 매출 통계 / MRR 추정
"""
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.plans import add_credits, deduct_credits
from app.core.security import get_current_user
from app.models.models import (
    CreditTransaction, EmailLog, Project, ServiceKey, User,
)

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _require_admin(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다")
    return current_user


# ──────────────────────────────────────
# 1. 서비스 키 (기존)
# ──────────────────────────────────────

class CreateKeyRequest(BaseModel):
    memo: Optional[str] = None
    expires_at: Optional[datetime] = None


class ServiceKeyResponse(BaseModel):
    id: int
    key: str
    memo: Optional[str] = None
    is_active: bool
    activated_by_user_id: Optional[int] = None
    activated_by_email: Optional[str] = None
    created_at: datetime
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


@router.post("/service-keys", response_model=ServiceKeyResponse)
def create_service_key(
    req: CreateKeyRequest = CreateKeyRequest(),
    db: Session = Depends(get_db),
    admin: User = Depends(_require_admin),
):
    key = f"sk_{secrets.token_hex(24)}"
    sk = ServiceKey(key=key, memo=req.memo, expires_at=req.expires_at)
    db.add(sk)
    db.commit()
    db.refresh(sk)
    return _key_to_response(sk, db)


@router.get("/service-keys", response_model=list[ServiceKeyResponse])
def list_service_keys(
    db: Session = Depends(get_db),
    admin: User = Depends(_require_admin),
):
    keys = db.query(ServiceKey).order_by(ServiceKey.created_at.desc()).all()
    return [_key_to_response(sk, db) for sk in keys]


@router.patch("/service-keys/{key_id}")
def toggle_service_key(
    key_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(_require_admin),
):
    sk = db.query(ServiceKey).filter(ServiceKey.id == key_id).first()
    if not sk:
        raise HTTPException(status_code=404, detail="서비스 키를 찾을 수 없습니다")
    sk.is_active = not sk.is_active
    db.commit()
    return {"id": sk.id, "is_active": sk.is_active}


@router.delete("/service-keys/{key_id}")
def delete_service_key(
    key_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(_require_admin),
):
    sk = db.query(ServiceKey).filter(ServiceKey.id == key_id).first()
    if not sk:
        raise HTTPException(status_code=404, detail="서비스 키를 찾을 수 없습니다")
    db.delete(sk)
    db.commit()
    return {"message": "삭제되었습니다"}


def _key_to_response(sk: ServiceKey, db: Session) -> ServiceKeyResponse:
    activated_email = None
    if sk.activated_by_user_id:
        u = db.query(User).filter(User.id == sk.activated_by_user_id).first()
        if u:
            activated_email = u.email
    return ServiceKeyResponse(
        id=sk.id, key=sk.key, memo=sk.memo, is_active=sk.is_active,
        activated_by_user_id=sk.activated_by_user_id,
        activated_by_email=activated_email,
        created_at=sk.created_at, expires_at=sk.expires_at,
        last_used_at=sk.last_used_at,
    )


# ──────────────────────────────────────
# 2. 사용자 관리
# ──────────────────────────────────────

class AdminUserSummary(BaseModel):
    id: int
    email: str
    name: str
    plan: str
    is_admin: bool
    is_active: bool
    credits: int
    created_at: datetime
    project_count: int = 0
    total_emails_sent: int = 0
    last_active: Optional[datetime] = None


class AdminUserListResponse(BaseModel):
    items: list[AdminUserSummary]
    total: int
    page: int
    page_size: int
    total_pages: int


class GrantCreditsRequest(BaseModel):
    amount: int  # 양수 = 부여, 음수 = 차감
    reason: str


class UpdateUserRequest(BaseModel):
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None
    plan: Optional[str] = None


@router.get("/users", response_model=AdminUserListResponse)
def list_users(
    q: Optional[str] = Query(None, description="이메일/이름 검색"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: User = Depends(_require_admin),
):
    query = db.query(User)
    if q:
        like = f"%{q}%"
        query = query.filter((User.email.ilike(like)) | (User.name.ilike(like)))

    total = query.count()
    users = (
        query.order_by(User.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = []
    for u in users:
        proj_count = db.query(func.count(Project.id)).filter(Project.user_id == u.id).scalar() or 0
        emails = (
            db.query(func.count(EmailLog.id))
            .filter(EmailLog.user_id == u.id, EmailLog.status == "success")
            .scalar() or 0
        )
        last_email = (
            db.query(func.max(EmailLog.sent_at))
            .filter(EmailLog.user_id == u.id)
            .scalar()
        )
        items.append(AdminUserSummary(
            id=u.id, email=u.email, name=u.name, plan=u.plan,
            is_admin=u.is_admin, is_active=u.is_active, credits=u.credits,
            created_at=u.created_at, project_count=proj_count,
            total_emails_sent=emails, last_active=last_email,
        ))

    return AdminUserListResponse(
        items=items, total=total, page=page, page_size=page_size,
        total_pages=max(1, (total + page_size - 1) // page_size),
    )


@router.get("/users/{user_id}", response_model=AdminUserSummary)
def get_user_detail(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(_require_admin),
):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")
    proj_count = db.query(func.count(Project.id)).filter(Project.user_id == u.id).scalar() or 0
    emails = (
        db.query(func.count(EmailLog.id))
        .filter(EmailLog.user_id == u.id, EmailLog.status == "success")
        .scalar() or 0
    )
    last_email = (
        db.query(func.max(EmailLog.sent_at))
        .filter(EmailLog.user_id == u.id)
        .scalar()
    )
    return AdminUserSummary(
        id=u.id, email=u.email, name=u.name, plan=u.plan,
        is_admin=u.is_admin, is_active=u.is_active, credits=u.credits,
        created_at=u.created_at, project_count=proj_count,
        total_emails_sent=emails, last_active=last_email,
    )


@router.patch("/users/{user_id}")
def update_user(
    user_id: int,
    req: UpdateUserRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(_require_admin),
):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")

    # 본인을 admin에서 해제하는 것은 막음 (마지막 admin 보호)
    if req.is_admin is False and u.id == admin.id:
        raise HTTPException(status_code=400, detail="본인의 관리자 권한은 해제할 수 없습니다")

    if req.is_active is not None:
        u.is_active = req.is_active
    if req.is_admin is not None:
        u.is_admin = req.is_admin
    if req.plan is not None:
        if req.plan not in ("free", "personal", "pro", "agency"):
            raise HTTPException(status_code=400, detail="유효하지 않은 플랜입니다")
        u.plan = req.plan

    db.commit()
    return {"message": "수정되었습니다"}


@router.post("/users/{user_id}/grant-credits")
def grant_credits(
    user_id: int,
    req: GrantCreditsRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(_require_admin),
):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")

    if req.amount == 0:
        raise HTTPException(status_code=400, detail="크레딧 변경량이 0입니다")

    if not req.reason.strip():
        raise HTTPException(status_code=400, detail="사유를 입력하세요")

    description = f"[관리자] {req.reason.strip()} (by {admin.email})"
    if req.amount > 0:
        add_credits(db, user_id, req.amount, description, tx_type="admin_grant")
    else:
        # 차감: 잔액보다 많이 차감하지 않음
        actual = min(abs(req.amount), u.credits)
        if actual > 0:
            deduct_credits(db, user_id, actual, description)
    db.commit()
    db.refresh(u)
    return {"message": "변경되었습니다", "credits": u.credits}


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(_require_admin),
):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")
    if u.id == admin.id:
        raise HTTPException(status_code=400, detail="본인 계정은 삭제할 수 없습니다")
    if u.is_admin:
        raise HTTPException(status_code=400, detail="다른 관리자는 삭제할 수 없습니다. 먼저 권한을 해제하세요.")
    db.delete(u)
    db.commit()
    return {"message": "삭제되었습니다"}


# ──────────────────────────────────────
# 3. 매출 / 통계
# ──────────────────────────────────────

class RevenueResponse(BaseModel):
    total_revenue: int           # 누적 매출 (원)
    revenue_this_month: int      # 이번 달 매출
    revenue_last_month: int      # 지난 달 매출
    paid_users_count: int        # 한 번이라도 결제한 사용자 수
    total_users: int
    active_users_30d: int        # 최근 30일 이메일 발송 한 사용자
    new_users_this_month: int
    avg_revenue_per_paid_user: int  # ARPU (paid only)


@router.get("/stats", response_model=RevenueResponse)
def get_admin_stats(
    db: Session = Depends(get_db),
    admin: User = Depends(_require_admin),
):
    # SQLAlchemy DateTime 컬럼은 naive로 저장되므로 비교 기준도 naive UTC
    now = datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_month_start = (month_start - timedelta(days=1)).replace(day=1)

    def _naive(dt):
        return dt.replace(tzinfo=None) if dt and dt.tzinfo else dt

    # 매출 = purchase 트랜잭션의 amount * 평균 단가? — 간단히 패키지에서 역산
    # CREDIT_PACKAGES에 가격 매핑 필요. 여기서는 description에 가격이 없으니
    # 가장 정확한 방법: tx_type='purchase'인 거래의 credits로 패키지 가격 역산
    from app.core.plans import CREDIT_PACKAGES

    def _credits_to_price(credits: int) -> int:
        # 가장 가까운 패키지 가격 (보너스 미반영). 실 운영에선 결제 테이블이 따로 있어야 정확.
        for p in sorted(CREDIT_PACKAGES, key=lambda x: x["credits"], reverse=True):
            if credits >= p["credits"]:
                return p["price"]
        return 0

    purchases = db.query(CreditTransaction).filter(
        CreditTransaction.tx_type == "purchase"
    ).all()

    total_revenue = sum(_credits_to_price(p.amount) for p in purchases)
    revenue_this_month = sum(
        _credits_to_price(p.amount) for p in purchases
        if _naive(p.created_at) >= month_start
    )
    revenue_last_month = sum(
        _credits_to_price(p.amount) for p in purchases
        if last_month_start <= _naive(p.created_at) < month_start
    )

    paid_user_ids = {p.user_id for p in purchases}
    paid_users_count = len(paid_user_ids)

    total_users = db.query(func.count(User.id)).scalar() or 0
    active_users_30d = (
        db.query(func.count(func.distinct(EmailLog.user_id)))
        .filter(EmailLog.sent_at >= now - timedelta(days=30))
        .scalar() or 0
    )
    new_users_this_month = (
        db.query(func.count(User.id))
        .filter(User.created_at >= month_start)
        .scalar() or 0
    )

    arpu = total_revenue // paid_users_count if paid_users_count else 0

    return RevenueResponse(
        total_revenue=total_revenue,
        revenue_this_month=revenue_this_month,
        revenue_last_month=revenue_last_month,
        paid_users_count=paid_users_count,
        total_users=total_users,
        active_users_30d=active_users_30d,
        new_users_this_month=new_users_this_month,
        avg_revenue_per_paid_user=arpu,
    )


# ──────────────────────────────────────
# 4. 자기 자신을 admin으로 승격 (최초 1회만 — 관리자가 한 명도 없을 때)
# ──────────────────────────────────────

@router.post("/bootstrap-first-admin")
def bootstrap_first_admin(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    관리자가 한 명도 없을 때만 호출 가능 — 호출한 사용자를 관리자로 승격.
    최초 배포 후 사장님이 본인 계정을 관리자로 만드는 용도.
    """
    existing_admin = db.query(User).filter(User.is_admin == True).first()
    if existing_admin:
        raise HTTPException(
            status_code=403,
            detail="이미 관리자가 존재합니다. 기존 관리자에게 권한을 받으세요.",
        )
    # ADMIN_EMAIL 환경변수가 설정되어 있으면 그 계정만 승격 가능 (신규 배포 레이스 방지)
    import os
    admin_email = os.getenv("ADMIN_EMAIL", "").strip().lower()
    if admin_email and current_user.email.lower() != admin_email:
        raise HTTPException(
            status_code=403,
            detail="관리자 승격이 허용되지 않은 계정입니다.",
        )
    current_user.is_admin = True
    db.commit()
    return {"message": "관리자로 승격되었습니다", "user_id": current_user.id}
