"""
크레딧 기반 수익 모델 + 발송 안전 시스템

- 모든 기능은 크레딧으로 과금 (수집, 이메일, DM)
- 신규 가입 시 무료 크레딧 지급
- 발송 속도/한도는 계정 안전을 위해 시스템이 제한하되 사용자가 조정 가능
- 벤 걸리면 사용자 책임, 크레딧은 소진된 것
"""
from datetime import date

from sqlalchemy.orm import Session

# ──────────────────────────────────────
# 크레딧 단가
# ──────────────────────────────────────
CREDIT_COSTS = {
    "prospect": 1,    # 업체 수집 1건 = 1 크레딧
    "email": 2,       # 이메일 발송 1건 = 2 크레딧
    "dm": 3,          # 인스타 DM 1건 = 3 크레딧
}

# 신규 가입 무료 크레딧 — 체험 가능한 최소량 (수집 10 + 이메일 2 + DM 3 + 여유)
FREE_SIGNUP_CREDITS = 30

# 크레딧 충전 패키지 — 무료 30cr이 체험용. 본격 사용자만 결제.
# examples: balanced=실 영업 funnel(수집→이메일→DM 비율), single_*=단일 사용 시 최대량
CREDIT_PACKAGES = [
    {"id": "credits_10000", "credits": 10000, "price": 590000, "label": "스탠다드 10,000 크레딧",
     "price_label": "590,000원", "per_credit": "59원",
     "examples": {
         "balanced": "업체 4,000곳 + 이메일 2,000통 + DM 666통",
         "single": {"scrape": "10,000건", "email": "5,000통", "dm": "3,333통"},
     }},
    {"id": "credits_30000", "credits": 30000, "price": 1590000, "label": "프로 30,000 크레딧",
     "price_label": "1,590,000원", "per_credit": "53원", "popular": True, "bonus": "10% 할인",
     "examples": {
         "balanced": "업체 12,000곳 + 이메일 6,000통 + DM 2,000통",
         "single": {"scrape": "30,000건", "email": "15,000통", "dm": "10,000통"},
     }},
    {"id": "credits_70000", "credits": 70000, "price": 3490000, "label": "비즈니스 70,000 크레딧",
     "price_label": "3,490,000원", "per_credit": "49.8원", "bonus": "16% 할인",
     "examples": {
         "balanced": "업체 28,000곳 + 이메일 14,000통 + DM 4,666통",
         "single": {"scrape": "70,000건", "email": "35,000통", "dm": "23,333통"},
     }},
    {"id": "credits_100000", "credits": 100000, "price": 4690000, "label": "엔터프라이즈 100,000 크레딧",
     "price_label": "4,690,000원", "per_credit": "46.9원", "bonus": "21% 할인",
     "examples": {
         "balanced": "업체 40,000곳 + 이메일 20,000통 + DM 6,666통",
         "single": {"scrape": "100,000건", "email": "50,000통", "dm": "33,333통"},
     }},
]

# 프로젝트 한도 (크레딧 보유량 기반이 아닌 고정)
MAX_PROJECTS = 50

# ──────────────────────────────────────
# 발송 안전 한도 (기본값 — 사용자 커스텀 가능)
# ──────────────────────────────────────
# ── Gmail 안전 가이드 (2025-2026 리서치 기반) ──
# 공식 한도: 무료 Gmail 500건/일, Workspace 2,000건/일
# 실질 안전선 (콜드 아웃리치): 메일박스당 30~50건/일
# 워밍업: 4~6주, 5건/일부터 시작 → 주당 증가
# 발송 간격: 30~120초 랜덤 / 배치 10~20건 후 5~10분 휴식
# 반송률: 3% 이상 경고, 5% 이상 스팸 판정, 10% 이상 정지 위험
# 스팸 신고율: 0.1% 이상이면 Google이 도메인 평판 하락 (공식 기준)
# 다중 메일박스 로테이션 권장 (5개 × 50건 = 250건/일)
#
# ── Instagram DM 안전 가이드 (2025-2026 리서치 기반) ──
# 신규 계정: 첫 2주 DM 금지, 일반 활동만 (팔로우/좋아요/댓글)
# 1~3개월 계정: 10~20건/일, 시간당 10~15건 이하
# 3~6개월 성숙 계정: 40~70건/일 (비팔로워 대상)
# 팔로워 DM은 150~200건/일 가능 (훨씬 느슨함)
# DM 간격: 3~8분 랜덤, 배치 5~10건 후 15~30분 휴식
# 동일 메시지 반복, 링크 포함 시 차단 위험 급증
# Action Block: 24시간~7일, 반복 시 30일 → 영구 정지
# Private API 직접 호출 시 영구 정지

SAFETY_DEFAULTS = {
    "email": {
        "daily_limit": 40,          # 일일 발송 한도 (안전 권장)
        "hourly_limit": 12,         # 시간당 한도
        "min_delay_seconds": 30,    # 최소 발송 간격 (초)
        "max_delay_seconds": 120,   # 최대 발송 간격 (초)
        "warmup_day1_limit": 5,     # 워밍업 1일차 한도
        "warmup_daily_increase": 3, # 매일 증가량
        "warmup_days": 28,          # 워밍업 기간 4주
        "max_bounce_rate": 3.0,     # 반송률 경고 (%) — 5% 넘으면 스팸
        "max_spam_rate": 0.1,       # 스팸 신고율 경고 (%) — Google 기준 0.1%
    },
    "dm": {
        "daily_limit": 15,          # 비팔로워 DM 안전선
        "hourly_limit": 5,          # 시간당 한도
        "min_delay_seconds": 180,   # 최소 3분 간격
        "max_delay_seconds": 480,   # 최대 8분 간격
        "warmup_day1_limit": 0,     # 첫 2주는 DM 안 보내기 권장
        "warmup_daily_increase": 1, # 매일 1건씩 증가
        "warmup_days": 42,          # 워밍업 6주 (인스타는 더 보수적)
    },
}

# 사용자 커스텀 가능 범위 (안전 한도를 넘어서는 "위험" 영역)
SAFETY_MAX_OVERRIDES = {
    "email": {
        "daily_limit": 500,         # Gmail 공식 한도 (무료), Workspace 2000
        "hourly_limit": 100,
        "min_delay_seconds": 10,    # 최소 10초까지 줄일 수 있음 (위험)
    },
    "dm": {
        "daily_limit": 70,          # 성숙 계정 최대
        "hourly_limit": 15,
        "min_delay_seconds": 60,    # 최소 1분까지 줄일 수 있음 (위험)
    },
}

# ──────────────────────────────────────
# 크레딧 함수
# ──────────────────────────────────────

def check_credits(db: Session, user_id: int, action: str, count: int = 1) -> dict:
    """크레딧 잔액 확인. action: 'prospect', 'email', 'dm'"""
    from app.models.models import User
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"allowed": False, "reason": "user_not_found"}

    cost = CREDIT_COSTS.get(action, 1) * count
    if user.credits >= cost:
        return {"allowed": True, "cost": cost, "balance": user.credits}
    return {"allowed": False, "reason": "insufficient_credits", "cost": cost, "balance": user.credits}


def deduct_credits(db: Session, user_id: int, amount: int, description: str):
    """크레딧 차감 + 거래 내역 기록"""
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
    """크레딧 추가 + 거래 내역 기록"""
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


# ──────────────────────────────────────
# 발송 안전 시스템
# ──────────────────────────────────────

def get_safe_daily_limit(channel: str, account_age_days: int, user_override: int | None = None) -> dict:
    """
    계정 나이 + 사용자 설정을 고려한 오늘의 안전 발송 한도 계산.
    Returns: {
        "recommended": 권장 한도,
        "actual": 실제 적용 한도 (사용자 오버라이드 반영),
        "max_allowed": 시스템 최대치,
        "risk_level": "safe" | "moderate" | "risky",
        "warning": 경고 메시지 (있으면),
    }
    """
    defaults = SAFETY_DEFAULTS.get(channel, SAFETY_DEFAULTS["email"])
    max_overrides = SAFETY_MAX_OVERRIDES.get(channel, {})

    # 워밍업 기간이면 권장 한도 낮춤
    if account_age_days < defaults["warmup_days"]:
        recommended = min(
            defaults["warmup_day1_limit"] + (account_age_days * defaults["warmup_daily_increase"]),
            defaults["daily_limit"],
        )
    else:
        recommended = defaults["daily_limit"]

    max_allowed = max_overrides.get("daily_limit", defaults["daily_limit"])

    # 사용자 오버라이드 적용
    if user_override is not None and user_override > 0:
        actual = min(user_override, max_allowed)
    else:
        actual = recommended

    # 위험도 판단 (recommended=0 — 워밍업 첫날 — 안전 분모 처리)
    if recommended <= 0:
        if actual <= 0:
            risk_level = "safe"
            warning = "워밍업 기간입니다. 오늘은 발송하지 마세요."
        else:
            risk_level = "risky"
            warning = "워밍업 기간(권장 0건)에 발송하면 계정 정지 위험이 매우 높습니다."
    elif actual <= recommended:
        risk_level = "safe"
        warning = None
    elif actual <= recommended * 2:
        risk_level = "moderate"
        warning = f"권장치({recommended}건)를 초과합니다. 계정 제한 가능성이 있습니다."
    else:
        risk_level = "risky"
        warning = f"권장치({recommended}건)의 {actual / recommended:.0f}배입니다. 계정 정지 위험이 높습니다."

    return {
        "recommended": recommended,
        "actual": actual,
        "max_allowed": max_allowed,
        "risk_level": risk_level,
        "warning": warning,
        "warmup_remaining_days": max(0, defaults["warmup_days"] - account_age_days),
    }


def get_enforced_daily_limit(channel: str, account_age_days: int, user_limit: int) -> int:
    """발송 시점에 실제 강제되는 일일 한도.

    - 워밍업 기간: 워밍업 곡선 한도로 캡 (최소 warmup_day1_limit 보장) — 계정 보호가 우선
    - 워밍업 이후: 시스템 최대치(SAFETY_MAX_OVERRIDES)로만 캡
    """
    defaults = SAFETY_DEFAULTS.get(channel, SAFETY_DEFAULTS["email"])
    max_overrides = SAFETY_MAX_OVERRIDES.get(channel, {})
    max_allowed = max_overrides.get("daily_limit", defaults["daily_limit"])

    if account_age_days < defaults["warmup_days"]:
        warmup_cap = min(
            defaults["warmup_day1_limit"] + (account_age_days * defaults["warmup_daily_increase"]),
            defaults["daily_limit"],
        )
        warmup_cap = max(warmup_cap, defaults["warmup_day1_limit"])
        return max(0, min(user_limit, warmup_cap, max_allowed))
    return max(0, min(user_limit, max_allowed))


def get_send_delay(channel: str, user_min_delay: int | None = None) -> dict:
    """발송 간격 계산"""
    defaults = SAFETY_DEFAULTS.get(channel, SAFETY_DEFAULTS["email"])
    max_overrides = SAFETY_MAX_OVERRIDES.get(channel, {})

    min_delay = defaults["min_delay_seconds"]
    max_delay = defaults["max_delay_seconds"]
    abs_min = max_overrides.get("min_delay_seconds", min_delay)

    if user_min_delay is not None:
        actual_min = max(user_min_delay, abs_min)
    else:
        actual_min = min_delay

    risk_level = "safe"
    if actual_min < min_delay:
        risk_level = "risky" if actual_min < min_delay // 2 else "moderate"

    return {
        "min_delay": actual_min,
        "max_delay": max(max_delay, actual_min + 30),
        "recommended_min": min_delay,
        "recommended_max": max_delay,
        "risk_level": risk_level,
    }


# ──────────────────────────────────────
# Usage tracking (legacy compat)
# ──────────────────────────────────────

def get_or_create_usage(db: Session, user_id: int):
    from app.models.models import UsageRecord
    from sqlalchemy.exc import IntegrityError

    today = date.today()
    record = db.query(UsageRecord).filter(UsageRecord.user_id == user_id, UsageRecord.date == today).first()
    if not record:
        try:
            record = UsageRecord(user_id=user_id, date=today)
            db.add(record)
            db.flush()
        except IntegrityError:
            db.rollback()
            record = db.query(UsageRecord).filter(UsageRecord.user_id == user_id, UsageRecord.date == today).first()
    return record


def increment_usage(db: Session, user_id: int, resource: str, amount: int = 1):
    record = get_or_create_usage(db, user_id)
    current = getattr(record, resource, 0)
    setattr(record, resource, current + amount)
    db.flush()


def get_plan_limits(plan: str) -> dict:
    """Legacy compat — 크레딧 모델에서는 한도가 크레딧으로 대체됨"""
    return {"projects": MAX_PROJECTS, "daily_emails": -1, "daily_dms": -1, "daily_prospects": -1}


def check_usage_limit(db: Session, user_id: int, plan: str, resource: str) -> dict:
    """Legacy compat — 크레딧 잔액만 확인"""
    action_map = {"daily_emails": "email", "daily_dms": "dm", "daily_prospects": "prospect"}
    action = action_map.get(resource, "prospect")
    result = check_credits(db, user_id, action)
    if result["allowed"]:
        return {"allowed": True, "within_plan": True}
    return {"allowed": False, "reason": "no_credits"}


def check_project_limit(db: Session, user_id: int, plan: str) -> bool:
    from app.models.models import Project
    count = db.query(Project).filter(Project.user_id == user_id).count()
    return count < MAX_PROJECTS
