import logging
import secrets

from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

# Generate stable defaults for development (written to .env on first run)
_DEV_SECRET_KEY = "dev-secret-key-change-in-production-please"


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/outreach"

    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""

    # JWT — MUST be set via env var in production
    SECRET_KEY: str = _DEV_SECRET_KEY
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_HOURS: int = 72

    # Environment
    ENV: str = "development"  # development | production

    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    # Encryption key for sensitive data (gmail app passwords, etc.)
    # Must be a valid Fernet key. Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    ENCRYPTION_KEY: str = ""

    # Base URL for tracking pixels/links
    BASE_URL: str = "http://localhost:8000"

    # Toss Payments (test mode defaults)
    TOSS_CLIENT_KEY: str = "test_ck_D5GePWvyJnrK0W0k6q8gLzN97Eoq"
    TOSS_SECRET_KEY: str = "test_sk_zXLkKEypNArWmo50nX3lmeaxYG5R"

    # Redis (for Celery, optional)
    REDIS_URL: str = "redis://localhost:6379/0"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


settings = Settings()

# Warn or fail on insecure defaults
if settings.ENV == "production":
    if settings.SECRET_KEY == _DEV_SECRET_KEY:
        raise RuntimeError("SECRET_KEY must be set in production! Set it in .env or environment variable.")
    if not settings.ENCRYPTION_KEY:
        raise RuntimeError("ENCRYPTION_KEY must be set in production! Generate with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"")
elif settings.SECRET_KEY == _DEV_SECRET_KEY:
    logger.warning("Using default SECRET_KEY — this is fine for development but must be changed for production.")
