import logging

from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

# Generate stable defaults for development (written to .env on first run)
_DEV_SECRET_KEY = "dev-secret-key-change-in-production-please"
_DEV_ENCRYPTION_KEY = "fvYHhX1aPMMv9eWsM9vCMOSgADtfnXOgz17qb_ZlKI0="


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

    # CORS — comma-separated origins, or JSON list. Override with CORS_ORIGINS env var.
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    # Encryption key for sensitive data (gmail app passwords, etc.)
    ENCRYPTION_KEY: str = _DEV_ENCRYPTION_KEY

    # Base URL for tracking pixels/links
    BASE_URL: str = "http://localhost:8000"

    # 계좌이체 결제 — 입금받을 계좌 정보 (관리자가 .env에서 설정)
    BANK_NAME: str = ""           # 예: "국민은행"
    BANK_ACCOUNT: str = ""        # 예: "123-456-789012"
    BANK_HOLDER: str = ""         # 예: "김우진"

    # Redis (for Celery, optional)
    REDIS_URL: str = "redis://localhost:6379/0"

    # Rate limiting (테스트 환경에서 false로 비활성화)
    RATE_LIMIT_ENABLED: bool = True

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


settings = Settings()

# 프로덕션에서 dev 기본 키로 기동하면 JWT 위조·저장된 앱 비밀번호 복호화가 가능해짐 — 기동 자체를 차단
if settings.ENV == "production":
    _insecure = []
    if settings.SECRET_KEY == _DEV_SECRET_KEY:
        _insecure.append("SECRET_KEY")
    if settings.ENCRYPTION_KEY == _DEV_ENCRYPTION_KEY:
        _insecure.append("ENCRYPTION_KEY")
    if _insecure:
        raise RuntimeError(
            f"프로덕션에서 기본 {'/'.join(_insecure)} 사용 금지. "
            "scripts/generate_keys.sh 로 키를 생성해 환경변수로 설정하세요."
        )
elif settings.SECRET_KEY == _DEV_SECRET_KEY:
    logger.warning("Using default SECRET_KEY — fine for development.")
