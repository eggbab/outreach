import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.core.config import settings as app_settings
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.core.rate_limit import limiter
from app.models.models import OnboardingProgress, ServiceKey, User, UserSettings
from app.api.pipeline import create_default_stages



logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    name: str
    service_key: Optional[str] = None
    accept_terms: bool = False  # 이용약관/개인정보처리방침 동의 (한국 정보통신망법)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    token: str
    user: "UserResponse"


class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    plan: str
    is_admin: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def signup(request: Request, req: SignupRequest, db: Session = Depends(get_db)):
    if len(req.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters",
        )
    if not req.accept_terms:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이용약관과 개인정보처리방침에 동의해주세요",
        )

    # Validate service key (optional)
    sk = None
    if req.service_key:
        sk = db.query(ServiceKey).filter(ServiceKey.key == req.service_key).first()
        if not sk:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="유효하지 않은 서비스 키입니다",
            )
        if not sk.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="비활성화된 서비스 키입니다",
            )
        if sk.activated_by_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이미 사용된 서비스 키입니다",
            )
        if sk.expires_at and sk.expires_at < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="만료된 서비스 키입니다",
            )

    existing = db.query(User).filter(User.email == req.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    from app.core.plans import FREE_SIGNUP_CREDITS

    now = datetime.now(timezone.utc)
    plan = "pro" if sk else "free"
    user = User(
        email=req.email,
        password_hash=hash_password(req.password),
        name=req.name,
        plan=plan,
        credits=FREE_SIGNUP_CREDITS,
        trial_started_at=now,
        trial_ends_at=now + timedelta(days=14),
        plan_changed_at=now,
        service_key_id=sk.id if sk else None,
        terms_accepted_at=now,
    )
    db.add(user)
    db.flush()

    # Link service key to user
    if sk:
        sk.activated_by_user_id = user.id
        sk.last_used_at = now

    # Create default settings for the user
    user_settings = UserSettings(user_id=user.id)
    db.add(user_settings)

    # Create default pipeline stages
    create_default_stages(db, user.id)

    # Create onboarding progress
    onboarding = OnboardingProgress(user_id=user.id)
    db.add(onboarding)

    db.commit()

    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(token=token, user=UserResponse(
        id=user.id, email=user.email, name=user.name,
        plan=user.plan, is_admin=user.is_admin, created_at=user.created_at,
    ))


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
def login(request: Request, req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not verify_password(req.password, user.password_hash):
        logger.warning("Failed login attempt for email=%s", req.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="계정이 정지되었습니다. 관리자에게 문의하세요.",
        )

    # Check service key validity on login
    if user.service_key_id and not user.is_admin:
        sk = db.query(ServiceKey).filter(ServiceKey.id == user.service_key_id).first()
        if not sk or not sk.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="서비스 키가 비활성화되었습니다. 관리자에게 문의하세요.",
            )
        if sk.expires_at and sk.expires_at < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="서비스 키가 만료되었습니다. 관리자에게 문의하세요.",
            )
        sk.last_used_at = datetime.now(timezone.utc)
        db.commit()

    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(token=token, user=UserResponse.model_validate(user))


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


class ActivateKeyRequest(BaseModel):
    service_key: str


class ActivateKeyResponse(BaseModel):
    message: str
    plan: str


# ──────────────────────────────────────
# 비밀번호 재설정
# ──────────────────────────────────────

class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


@router.post("/forgot-password")
@limiter.limit("3/minute")
def forgot_password(request: Request, req: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    비밀번호 재설정 링크를 이메일로 발송.
    보안: 이메일 존재 여부를 노출하지 않기 위해 항상 200 반환.
    """
    user = db.query(User).filter(User.email == req.email).first()
    if user:
        token = secrets.token_urlsafe(32)
        user.reset_token = token
        user.reset_token_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        db.commit()

        reset_url = f"{app_settings.BASE_URL}/reset-password?token={token}"

        # 이메일 발송 시도 (실패해도 사용자에겐 성공으로 응답)
        try:
            from app.services.sender.email import send_system_email
            send_system_email(
                to_email=user.email,
                subject="[Outreach] 비밀번호 재설정 안내",
                body=(
                    f"{user.name}님,\n\n"
                    f"비밀번호 재설정을 요청하셨습니다. 아래 링크를 1시간 안에 클릭하세요:\n\n"
                    f"{reset_url}\n\n"
                    f"본인이 요청한 게 아니라면 이 메일을 무시하세요. 비밀번호는 변경되지 않습니다.\n\n"
                    f"— Outreach 팀"
                ),
            )
        except Exception:
            logger.exception("Failed to send reset email to %s", user.email)
            # 개발 환경에선 콘솔 로그라도 남기기
            logger.info("[DEV] Reset URL for %s: %s", user.email, reset_url)

    return {"message": "비밀번호 재설정 안내를 이메일로 보내드렸습니다. 받은편지함을 확인하세요."}


@router.post("/reset-password")
@limiter.limit("5/minute")
def reset_password(request: Request, req: ResetPasswordRequest, db: Session = Depends(get_db)):
    if len(req.new_password) < 8:
        raise HTTPException(status_code=400, detail="비밀번호는 8자 이상이어야 합니다")

    user = db.query(User).filter(User.reset_token == req.token).first()
    if not user:
        raise HTTPException(status_code=400, detail="유효하지 않은 재설정 링크입니다")

    if not user.reset_token_expires_at or user.reset_token_expires_at < datetime.now(timezone.utc).replace(tzinfo=None) and (
        user.reset_token_expires_at and user.reset_token_expires_at.tzinfo is None
    ):
        raise HTTPException(status_code=400, detail="재설정 링크가 만료되었습니다. 다시 요청하세요.")

    # tz-aware/naive 비교 안전 처리
    expires = user.reset_token_expires_at
    if expires and expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if not expires or expires < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="재설정 링크가 만료되었습니다. 다시 요청하세요.")

    user.password_hash = hash_password(req.new_password)
    user.reset_token = None
    user.reset_token_expires_at = None
    db.commit()

    return {"message": "비밀번호가 변경되었습니다. 새 비밀번호로 로그인하세요."}


@router.post("/activate-key", response_model=ActivateKeyResponse)
def activate_service_key(
    req: ActivateKeyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sk = db.query(ServiceKey).filter(ServiceKey.key == req.service_key).first()
    if not sk:
        raise HTTPException(status_code=400, detail="유효하지 않은 서비스 키입니다")
    if not sk.is_active:
        raise HTTPException(status_code=400, detail="비활성화된 서비스 키입니다")
    if sk.activated_by_user_id:
        raise HTTPException(status_code=400, detail="이미 사용된 서비스 키입니다")
    if sk.expires_at and sk.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="만료된 서비스 키입니다")

    now = datetime.now(timezone.utc)
    sk.activated_by_user_id = current_user.id
    sk.last_used_at = now
    current_user.service_key_id = sk.id
    current_user.plan = "pro"
    current_user.plan_changed_at = now
    db.commit()

    return ActivateKeyResponse(message="서비스 키가 등록되었습니다", plan="pro")
