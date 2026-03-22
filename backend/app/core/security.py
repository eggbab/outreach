from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from cryptography.fernet import Fernet
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db

security_scheme = HTTPBearer()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(hours=settings.JWT_EXPIRY_HOURS)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: Session = Depends(get_db),
):
    from app.models.models import ApiKey, User
    import hashlib

    token = credentials.credentials

    # Check if it's an API key (starts with "osk_")
    if token.startswith("osk_"):
        key_hash = hashlib.sha256(token.encode()).hexdigest()
        # DB-level comparison via SQLAlchemy filter — not vulnerable to timing attacks
        # since the comparison happens in PostgreSQL, not in Python.
        api_key = db.query(ApiKey).filter(ApiKey.key_hash == key_hash, ApiKey.is_active == True).first()
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or revoked API key",
            )
        if api_key.expires_at and api_key.expires_at < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key expired",
            )
        # Update last used
        api_key.last_used_at = datetime.now(timezone.utc)
        db.flush()

        user = db.query(User).filter(User.id == api_key.user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )
        return user

    # Regular JWT token
    payload = decode_access_token(token)
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user


def encrypt_value(value: str) -> str:
    """Encrypt a string value using Fernet symmetric encryption."""
    if not settings.ENCRYPTION_KEY:
        # Fallback: store as-is if no encryption key configured (dev only)
        return value
    f = Fernet(settings.ENCRYPTION_KEY.encode())
    return f.encrypt(value.encode()).decode()


def decrypt_value(encrypted_value: str) -> str:
    """Decrypt a Fernet-encrypted string."""
    if not settings.ENCRYPTION_KEY:
        return encrypted_value
    f = Fernet(settings.ENCRYPTION_KEY.encode())
    return f.decrypt(encrypted_value.encode()).decode()
