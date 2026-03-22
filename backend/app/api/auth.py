import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.models.models import OnboardingProgress, User, UserSettings
from app.api.pipeline import create_default_stages

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    name: str


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
    created_at: datetime

    model_config = {"from_attributes": True}


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def signup(req: SignupRequest, db: Session = Depends(get_db)):
    if len(req.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters",
        )

    existing = db.query(User).filter(User.email == req.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    now = datetime.now(timezone.utc)
    user = User(
        email=req.email,
        password_hash=hash_password(req.password),
        name=req.name,
        plan="pro",
        trial_started_at=now,
        trial_ends_at=now + timedelta(days=14),
        plan_changed_at=now,
    )
    db.add(user)
    db.flush()

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
        plan=user.plan, created_at=user.created_at,
    ))


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not verify_password(req.password, user.password_hash):
        logger.warning("Failed login attempt for email=%s", req.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(token=token, user=UserResponse.model_validate(user))


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user
