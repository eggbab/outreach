from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import DmLog, Project, Prospect, User, UserSettings
from app.services.collector.extract import normalize_instagram
from app.services.compliance import is_email_suppressed
from app.services.dm_compose import render_dm

router = APIRouter(prefix="/api/chrome", tags=["chrome"])

DEFAULT_DM_TEMPLATE = (
    "{안녕하세요|반갑습니다} {company}님, 좋은 기회로 연락드립니다.\n\n"
    "{협업 가능성을 논의드리고 싶어|함께 할 수 있는 부분이 있을 것 같아} 메시지 드립니다. "
    "관심 있으시면 편하게 회신 부탁드립니다."
)


class DmTarget(BaseModel):
    # 확장이 이 형태를 그대로 소비 — 필드명 변경 시 content script도 함께 수정
    prospect_id: int
    username: str
    instagram_pk: Optional[str] = None  # 캐시된 값 (없으면 확장이 해석)
    message: str                         # 개인화 + 변형 완료된 최종 문구
    name: Optional[str] = None


class DmQueueResponse(BaseModel):
    targets: list[DmTarget]
    total: int
    daily_limit: int
    sent_today: int
    hourly_limit: int          # 시간당 발송 상한 (인스타 밴 방지)
    min_delay_seconds: int     # 발송 간 최소 간격
    max_delay_seconds: int
    night_block: bool          # 야간(21~08시) 발송 금지 여부 — 정보통신망법 §50③
    max_consecutive_failures: int  # 연속 실패 시 중단 임계


class DmResultRequest(BaseModel):
    prospect_id: int
    status: str  # success or failed
    error_message: Optional[str] = None
    message_body: Optional[str] = None
    instagram_pk: Optional[str] = None  # 확장이 해석한 PK — 캐싱용
    stop_reason: Optional[str] = None   # feedback_required/checkpoint 등 — 전체 중단 신호


def _dm_daily_limit(user: User, settings: UserSettings | None) -> int:
    """DM 일일 한도 — 사용자 설정을 계정 나이 기반 워밍업으로 캡 (서버 강제)."""
    from app.core.plans import get_enforced_daily_limit

    user_limit = settings.daily_dm_limit if settings else 15
    created = user.created_at
    if created and created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    age_days = (datetime.now(timezone.utc) - created).days if created else 0
    return get_enforced_daily_limit("dm", age_days, user_limit)


def _sent_today(db: Session, user_id: int) -> int:
    start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    return (
        db.query(func.count(DmLog.id))
        .filter(
            DmLog.user_id == user_id,
            DmLog.status == "success",
            DmLog.sent_at >= start.replace(tzinfo=None),
        )
        .scalar()
        or 0
    )


@router.get("/dm-queue", response_model=DmQueueResponse)
def get_dm_queue(
    project_id: int = Query(..., description="Project ID to get DM targets from"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """확장이 발송할 DM 대상 큐. 소유 프로젝트만, 워밍업 한도 잔여분만, 개인화+변형된 문구 포함."""
    # ─── 소유권 확인 (IDOR 방지) ───
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.user_id == current_user.id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다")

    settings = db.query(UserSettings).filter(UserSettings.user_id == current_user.id).first()
    daily_limit = _dm_daily_limit(current_user, settings)
    sent_today = _sent_today(db, current_user.id)
    remaining = max(0, daily_limit - sent_today)

    from app.core.plans import SAFETY_DEFAULTS
    dm_safety = SAFETY_DEFAULTS["dm"]
    safety = dict(
        daily_limit=daily_limit,
        sent_today=sent_today,
        hourly_limit=dm_safety["hourly_limit"],
        min_delay_seconds=dm_safety["min_delay_seconds"],
        max_delay_seconds=dm_safety["max_delay_seconds"],
        night_block=True,               # 콜드 광고성 DM은 야간(21~08시) 발송 금지
        max_consecutive_failures=3,     # 연속 3회 실패 시 계정 이상으로 보고 중단
    )

    # 크레딧 부족 또는 오늘 한도 소진 → 빈 큐 (안전 정책은 그대로 전달)
    from app.core.plans import check_credits
    if remaining == 0 or not check_credits(db, current_user.id, "dm", 1)["allowed"]:
        return DmQueueResponse(targets=[], total=0, **safety)

    # 발송 성공 = 재발송 안 함
    dm_sent_ids = select(DmLog.prospect_id).where(
        DmLog.user_id == current_user.id, DmLog.status == "success"
    )
    # 영구 실패(계정 없음/비공개) = 재시도 무의미 → 큐에서 제외 (무한 재시도 방지)
    from sqlalchemy import or_
    permanent_fail_ids = select(DmLog.prospect_id).where(
        DmLog.user_id == current_user.id,
        DmLog.status == "failed",
        or_(
            DmLog.error_message.ilike("%ACCOUNT_NOT_FOUND%"),
            DmLog.error_message.ilike("%private%"),
        ),
    )
    prospects = (
        db.query(Prospect)
        .filter(
            Prospect.project_id == project_id,
            Prospect.status.in_(["approved", "email_sent"]),
            Prospect.instagram.isnot(None),
            Prospect.instagram != "",
            ~Prospect.id.in_(dm_sent_ids),
            ~Prospect.id.in_(permanent_fail_ids),
        )
        .order_by(Prospect.collected_at)
        .limit(min(limit, remaining))
        .all()
    )

    template = (settings.dm_template if settings and settings.dm_template else DEFAULT_DM_TEMPLATE)

    targets = []
    for p in prospects:
        handle = normalize_instagram(p.instagram)
        if not handle:
            continue
        # 발송 차단: 블랙리스트/전역 수신거부 (이메일 기준 — DM도 동일 업체면 차단)
        if p.email and is_email_suppressed(db, current_user.id, p.email):
            continue
        message = render_dm(
            template,
            company_name=p.name or "",
            username=handle,
            prospect_id=p.id,
        )
        targets.append(DmTarget(
            prospect_id=p.id,
            username=handle,
            instagram_pk=p.instagram_pk,
            message=message,
            name=p.name,
        ))

    return DmQueueResponse(targets=targets, total=len(targets), **safety)


@router.post("/dm-result", response_model=dict)
def report_dm_result(
    req: DmResultRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """확장이 보고한 DM 발송 결과 기록 + 크레딧 차감 + PK 캐싱."""
    prospect = (
        db.query(Prospect)
        .join(Project, Prospect.project_id == Project.id)
        .filter(Prospect.id == req.prospect_id, Project.user_id == current_user.id)
        .first()
    )
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")

    if req.status not in ("success", "failed"):
        raise HTTPException(status_code=400, detail="Status must be 'success' or 'failed'")

    # 확장이 해석한 인스타 PK 캐싱 (다음부터 해석 생략 → 레이트리밋 절약)
    if req.instagram_pk and not prospect.instagram_pk:
        prospect.instagram_pk = req.instagram_pk[:50]

    effective_status = req.status
    error_message = req.error_message

    if req.status == "success":
        # 원자적 차감 — 성공하면 발송 확정, 실패(잔액 부족)면 무과금 발송을 인정하지 않음
        from app.core.plans import CREDIT_COSTS, deduct_credits
        remaining = deduct_credits(
            db, current_user.id, CREDIT_COSTS["dm"], f"DM 발송: @{prospect.instagram}"
        )
        if remaining is not None:
            prospect.status = "dm_sent"
        else:
            # 크레딧 부족 — success로 기록하지 않음(무과금 발송 방지). failed로 남겨 재큐잉 가능.
            effective_status = "failed"
            error_message = (error_message or "") + " 크레딧 부족으로 미확정"

    log = DmLog(
        prospect_id=req.prospect_id,
        user_id=current_user.id,
        status=effective_status,
        error_message=error_message,
        message_body=req.message_body,
    )
    db.add(log)
    db.commit()
    return {"message": "DM result recorded", "status": effective_status}
