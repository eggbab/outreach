from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from typing import Generator

from app.core.config import settings

_connect_args = {}
_engine_kwargs = {}

if settings.DATABASE_URL.startswith("sqlite"):
    _connect_args = {"check_same_thread": False}
elif "pooler.supabase.com" in settings.DATABASE_URL:
    # Supabase transaction pooler doesn't support prepared statements
    _connect_args = {"options": "-c statement_timeout=30000"}
    _engine_kwargs = {
        "pool_size": 5,
        "max_overflow": 10,
        "pool_recycle": 300,
    }

engine = create_engine(
    settings.DATABASE_URL,
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
