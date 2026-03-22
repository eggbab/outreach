from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from typing import Generator

from app.core.config import settings

_db_url = settings.DATABASE_URL
_connect_args = {}
_engine_kwargs = {}

if _db_url.startswith("sqlite"):
    _connect_args = {"check_same_thread": False}
elif "supabase" in _db_url:
    # Add sslmode if not already present
    if "sslmode" not in _db_url:
        sep = "&" if "?" in _db_url else "?"
        _db_url = _db_url + sep + "sslmode=require"
    # Serverless: use NullPool (no persistent connections)
    from sqlalchemy.pool import NullPool
    _engine_kwargs = {"poolclass": NullPool}

engine = create_engine(
    _db_url,
    pool_pre_ping=True,
    connect_args=_connect_args,
    **_engine_kwargs,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
