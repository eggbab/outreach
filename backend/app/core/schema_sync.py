"""시작 시 스키마 동기화 — 프로젝트 컨벤션은 create_all (CLAUDE.md).

create_all은 누락된 '테이블'만 만들고 기존 테이블의 새 '컬럼'은 추가하지 않으므로,
버전 업그레이드로 추가된 컬럼/enum 값을 여기서 명시적으로 보정한다.
(Alembic 마이그레이션은 초기 2개뿐이라 현행 모델과 크게 어긋나 사용하지 않는다.)
"""
import logging

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from app.core.database import Base

logger = logging.getLogger(__name__)

# (테이블, 컬럼, SQLite/공용 DDL 타입) — 신규 버전에서 추가된 컬럼 목록
_ADDED_COLUMNS = [
    ("email_logs", "replied_at", "TIMESTAMP"),
    ("global_prospects", "times_replied", "INTEGER DEFAULT 0"),
    ("user_settings", "ad_prefix_enabled", "BOOLEAN DEFAULT TRUE"),
    ("user_settings", "sender_info", "TEXT"),
    ("prospects", "instagram_pk", "VARCHAR(50)"),
    ("dm_logs", "message_body", "TEXT"),
    ("dm_logs", "replied_at", "TIMESTAMP"),
]

# Postgres 네이티브 enum에 추가된 값
_ADDED_ENUM_VALUES = [
    ("enrollment_status", "stopped"),
]


def sync_schema(engine: Engine) -> None:
    """누락 테이블 생성 + 누락 컬럼/enum 값 추가. 멱등."""
    Base.metadata.create_all(bind=engine)

    inspector = inspect(engine)
    is_postgres = engine.dialect.name == "postgresql"

    with engine.connect() as conn:
        for table, column, ddl_type in _ADDED_COLUMNS:
            if table not in inspector.get_table_names():
                continue
            existing = {c["name"] for c in inspector.get_columns(table)}
            if column in existing:
                continue
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl_type}"))
            conn.commit()
            logger.info(f"schema_sync: {table}.{column} 컬럼 추가")

        if is_postgres:
            for enum_name, value in _ADDED_ENUM_VALUES:
                try:
                    # ADD VALUE는 일부 PG 버전에서 트랜잭션 안에서 실행 불가 → autocommit
                    with engine.connect().execution_options(
                        isolation_level="AUTOCOMMIT"
                    ) as ac:
                        ac.execute(text(
                            f"ALTER TYPE {enum_name} ADD VALUE IF NOT EXISTS '{value}'"
                        ))
                    logger.info(f"schema_sync: enum {enum_name}에 '{value}' 추가")
                except Exception as e:
                    logger.warning(f"schema_sync: enum {enum_name} 갱신 실패 (무시): {e}")
