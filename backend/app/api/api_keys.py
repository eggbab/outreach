import hashlib
import secrets
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import ApiKey, User

router = APIRouter(prefix="/api/api-keys", tags=["api-keys"])


class ApiKeyCreate(BaseModel):
    name: str
    expires_at: Optional[datetime] = None


class ApiKeyResponse(BaseModel):
    id: int
    name: str
    key_prefix: str
    last_used_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ApiKeyCreatedResponse(ApiKeyResponse):
    key: str  # Full key, only shown once


@router.get("/", response_model=list[ApiKeyResponse])
def list_api_keys(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(ApiKey)
        .filter(ApiKey.user_id == current_user.id)
        .order_by(ApiKey.created_at.desc())
        .all()
    )


@router.post("/", response_model=ApiKeyCreatedResponse, status_code=status.HTTP_201_CREATED)
def create_api_key(
    req: ApiKeyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Generate a random API key
    raw_key = f"osk_{secrets.token_hex(24)}"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    key_prefix = raw_key[:10]

    api_key = ApiKey(
        user_id=current_user.id,
        name=req.name,
        key_hash=key_hash,
        key_prefix=key_prefix,
        expires_at=req.expires_at,
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    return ApiKeyCreatedResponse(
        id=api_key.id,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        last_used_at=api_key.last_used_at,
        expires_at=api_key.expires_at,
        is_active=api_key.is_active,
        created_at=api_key.created_at,
        key=raw_key,
    )


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_api_key(
    key_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    api_key = (
        db.query(ApiKey)
        .filter(ApiKey.id == key_id, ApiKey.user_id == current_user.id)
        .first()
    )
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    api_key.is_active = False
    db.commit()
