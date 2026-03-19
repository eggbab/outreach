from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decrypt_value, encrypt_value, get_current_user
from app.models.models import User, UserSettings

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingsResponse(BaseModel):
    gmail_email: Optional[str] = None
    has_gmail_password: bool = False
    email_template: Optional[str] = None
    dm_template: Optional[str] = None
    daily_email_limit: int = 80
    daily_dm_limit: int = 15


class SettingsUpdate(BaseModel):
    gmail_email: Optional[str] = None
    gmail_app_password: Optional[str] = None  # Plain text, will be encrypted
    email_template: Optional[str] = None
    dm_template: Optional[str] = None
    daily_email_limit: Optional[int] = None
    daily_dm_limit: Optional[int] = None


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
        email_template=settings.email_template,
        dm_template=settings.dm_template,
        daily_email_limit=settings.daily_email_limit,
        daily_dm_limit=settings.daily_dm_limit,
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

    db.commit()
    db.refresh(settings)

    return SettingsResponse(
        gmail_email=settings.gmail_email,
        has_gmail_password=bool(settings.gmail_app_password_encrypted),
        email_template=settings.email_template,
        dm_template=settings.dm_template,
        daily_email_limit=settings.daily_email_limit,
        daily_dm_limit=settings.daily_dm_limit,
    )
