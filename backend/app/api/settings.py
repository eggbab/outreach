from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import encrypt_value, get_current_user
from app.core.plans import get_safe_daily_limit, get_send_delay, SAFETY_DEFAULTS, SAFETY_MAX_OVERRIDES
from app.models.models import User, UserSettings

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingsResponse(BaseModel):
    gmail_email: Optional[str] = None
    has_gmail_password: bool = False
    email_subject: Optional[str] = None
    email_template: Optional[str] = None
    dm_template: Optional[str] = None
    daily_email_limit: int = 80
    daily_dm_limit: int = 15
    ad_prefix_enabled: bool = True
    sender_info: Optional[str] = None


class SettingsUpdate(BaseModel):
    model_config = {"extra": "forbid"}

    gmail_email: Optional[str] = None
    gmail_app_password: Optional[str] = None  # Plain text, will be encrypted
    email_subject: Optional[str] = None
    email_template: Optional[str] = None
    dm_template: Optional[str] = None
    daily_email_limit: Optional[int] = None
    daily_dm_limit: Optional[int] = None
    ad_prefix_enabled: Optional[bool] = None
    sender_info: Optional[str] = None


@router.get("/", response_model=SettingsResponse)
def get_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    settings = db.query(UserSettings).filter(UserSettings.user_id == current_user.id).first()
    if not settings:
        return SettingsResponse()

    return SettingsResponse(
        gmail_email=settings.gmail_email,
        has_gmail_password=bool(settings.gmail_app_password_encrypted),
        email_subject=settings.email_subject,
        email_template=settings.email_template,
        dm_template=settings.dm_template,
        daily_email_limit=settings.daily_email_limit,
        daily_dm_limit=settings.daily_dm_limit,
        ad_prefix_enabled=settings.ad_prefix_enabled,
        sender_info=settings.sender_info,
    )


@router.put("/", response_model=SettingsResponse)
def update_settings(
    req: SettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    settings = db.query(UserSettings).filter(UserSettings.user_id == current_user.id).first()
    if not settings:
        settings = UserSettings(user_id=current_user.id)
        db.add(settings)

    if req.gmail_email is not None:
        settings.gmail_email = req.gmail_email

    if req.gmail_app_password is not None:
        settings.gmail_app_password_encrypted = encrypt_value(req.gmail_app_password)

    if req.email_subject is not None:
        settings.email_subject = req.email_subject

    if req.email_template is not None:
        settings.email_template = req.email_template

    if req.dm_template is not None:
        settings.dm_template = req.dm_template

    if req.daily_email_limit is not None:
        if req.daily_email_limit < 1 or req.daily_email_limit > 500:
            raise HTTPException(status_code=400, detail="daily_email_limit must be between 1 and 500")
        settings.daily_email_limit = req.daily_email_limit

    if req.daily_dm_limit is not None:
        if req.daily_dm_limit < 1 or req.daily_dm_limit > 100:
            raise HTTPException(status_code=400, detail="daily_dm_limit must be between 1 and 100")
        settings.daily_dm_limit = req.daily_dm_limit

    if req.ad_prefix_enabled is not None:
        settings.ad_prefix_enabled = req.ad_prefix_enabled

    if req.sender_info is not None:
        settings.sender_info = req.sender_info[:1000]

    db.commit()
    db.refresh(settings)

    return SettingsResponse(
        gmail_email=settings.gmail_email,
        has_gmail_password=bool(settings.gmail_app_password_encrypted),
        email_subject=settings.email_subject,
        email_template=settings.email_template,
        dm_template=settings.dm_template,
        daily_email_limit=settings.daily_email_limit,
        daily_dm_limit=settings.daily_dm_limit,
        ad_prefix_enabled=settings.ad_prefix_enabled,
        sender_info=settings.sender_info,
    )


@router.get("/safety-guide")
def get_safety_guide(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """발송 안전 가이드 — 계정 나이 기반 권장 한도 + 위험도"""
    settings = db.query(UserSettings).filter(UserSettings.user_id == current_user.id).first()

    from datetime import datetime as dt, timezone as tz
    created = current_user.created_at
    if created and created.tzinfo is None:
        created = created.replace(tzinfo=tz.utc)
    account_age = (dt.now(tz.utc) - created).days if created else 0

    email_limit = get_safe_daily_limit("email", account_age, settings.daily_email_limit if settings else None)
    dm_limit = get_safe_daily_limit("dm", account_age, settings.daily_dm_limit if settings else None)
    email_delay = get_send_delay("email")
    dm_delay = get_send_delay("dm")

    return {
        "account_age_days": account_age,
        "email": {
            **email_limit,
            "delay": email_delay,
            "guide": {
                "bounce_rate_warning": SAFETY_DEFAULTS["email"]["max_bounce_rate"],
                "spam_rate_warning": SAFETY_DEFAULTS["email"]["max_spam_rate"],
                "tips": [
                    "새 계정은 4주간 워밍업 필요 — 하루 5건부터 시작해서 매일 3건씩 늘리세요",
                    "발송 간격을 30초~2분으로 랜덤 설정하면 기계적 패턴 회피 가능",
                    "제목과 본문에 변수({company_name} 등)를 사용해 매번 다른 내용을 보내세요",
                    "반송률 3% 이상이면 즉시 발송을 중단하고 이메일 리스트를 정리하세요",
                    "Google 기준 스팸 신고율 0.1% 이상이면 계정 평판이 하락합니다",
                    "Google Workspace (유료)는 일 2,000건, 무료 Gmail은 일 500건이 공식 한도입니다",
                    "여러 Gmail 계정을 번갈아 사용하면 계정당 부담을 줄일 수 있습니다",
                ],
            },
        },
        "dm": {
            **dm_limit,
            "delay": dm_delay,
            "guide": {
                "tips": [
                    "새 인스타 계정은 최소 2주간 DM을 보내지 말고 일반 활동만 하세요 (워밍업 6주 권장)",
                    "DM 간격을 3~8분으로 랜덤 설정하세요 — 시간당 5건 이하 권장",
                    "동일한 메시지 반복은 Action Block의 주요 원인입니다",
                    "팔로워가 아닌 사람에게 보내면 제한이 훨씬 빡빡합니다",
                    "DM에 링크를 포함하면 차단 위험이 크게 높아집니다",
                    "Action Block은 보통 24시간~7일 후 풀립니다 — 풀린 후 바로 재발송하지 마세요",
                    "반복적으로 Block되면 영구 정지될 수 있습니다",
                    "하루 최대 50~70건이 성숙 계정의 상한선입니다",
                ],
            },
        },
        "override_limits": {
            "email": SAFETY_MAX_OVERRIDES["email"],
            "dm": SAFETY_MAX_OVERRIDES["dm"],
        },
        "disclaimer": "발송 한도와 속도는 사용자가 직접 조정할 수 있습니다. 권장치를 초과하면 계정 제한/정지 위험이 있으며, 이에 대한 책임은 전적으로 사용자에게 있습니다.",
    }
