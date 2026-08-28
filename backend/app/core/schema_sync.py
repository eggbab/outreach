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

# 누락 컬럼은 손으로 나열하지 않고 모델 정의에서 자동으로 찾아낸다.
# (예전엔 목록을 직접 적었는데, 모델에 컬럼을 추가하고 목록에 적는 걸 잊으면
#  기존 DB에서 그 컬럼만 조용히 빠진 채 500 에러가 났다 — users.is_admin 사례.)

# Postgres 네이티브 enum 값도 모델에서 자동으로 찾아낸다 (컬럼과 같은 이유).
# 모델 Enum에 값을 추가하고 여기 적는 걸 잊으면, 그 값을 쓰는 순간
# "invalid input value for enum" 500이 난다 — prospect_status.replied 사례.

# 자주 필터하는 컬럼 인덱스 — (인덱스명, 테이블, 컬럼들). 대량 데이터에서 seq scan 방지.
_INDEXES = [
    ("ix_prospects_project_status", "prospects", "project_id, status"),
    ("ix_prospects_project_id", "prospects", "project_id"),
    ("ix_email_logs_user_status", "email_logs", "user_id, status"),
    ("ix_email_logs_prospect_id", "email_logs", "prospect_id"),
    ("ix_dm_logs_user_status", "dm_logs", "user_id, status"),
    ("ix_dm_logs_prospect_id", "dm_logs", "prospect_id"),
]


def _literal(value) -> str | None:
    """파이썬 기본값을 SQL 리터럴로. 표현할 수 없으면 None."""
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return "'" + value.replace("'", "''") + "'"
    return None


def _default_sql(col) -> str | None:
    """이 컬럼에 붙일 DEFAULT 절 값. 없으면 None.

    server_default가 있으면 그대로, 없으면 파이썬 default가 상수일 때만 쓴다.
    (utcnow 같은 함수형 default는 SQL로 옮길 수 없으므로 제외 — 그런 컬럼은
     nullable로 추가하고 애플리케이션이 값을 채운다.)
    """
    if col.server_default is not None:
        arg = getattr(col.server_default, "arg", None)
        return str(getattr(arg, "text", arg)) if arg is not None else None
    if col.default is not None and not col.default.is_callable:
        return _literal(col.default.arg)
    return None


def _add_missing_columns(conn, inspector, engine) -> None:
    """모델에는 있는데 DB에 없는 컬럼을 찾아 추가한다.

    기존 행이 있는 테이블에서도 안전하도록 NOT NULL을 바로 걸지 않는다.
    DEFAULT를 줄 수 있으면 채운 뒤에 NOT NULL로 조인다.
    """
    is_postgres = engine.dialect.name == "postgresql"
    table_names = set(inspector.get_table_names())

    for table_name, table in Base.metadata.tables.items():
        if table_name not in table_names:
            continue  # create_all이 방금 만든 테이블은 이미 최신
        existing = {c["name"] for c in inspector.get_columns(table_name)}
        for col in table.columns:
            if col.name in existing:
                continue
            try:
                type_sql = col.type.compile(dialect=engine.dialect)
                default_sql = _default_sql(col)
                ddl = f'ALTER TABLE "{table_name}" ADD COLUMN "{col.name}" {type_sql}'
                if default_sql is not None:
                    ddl += f" DEFAULT {default_sql}"
                conn.execute(text(ddl))
                conn.commit()

                # 모델이 NOT NULL이고 기본값도 있으면, 빈 값을 채운 뒤 제약을 건다.
                if not col.nullable and default_sql is not None and is_postgres:
                    conn.execute(text(
                        f'UPDATE "{table_name}" SET "{col.name}" = {default_sql} '
                        f'WHERE "{col.name}" IS NULL'
                    ))
                    conn.execute(text(
                        f'ALTER TABLE "{table_name}" '
                        f'ALTER COLUMN "{col.name}" SET NOT NULL'
                    ))
                    conn.commit()

                logger.info(f"schema_sync: {table_name}.{col.name} 컬럼 추가")
            except Exception as e:
                conn.rollback()
                logger.error(f"schema_sync: {table_name}.{col.name} 추가 실패: {e}")


def _add_missing_enum_values(engine) -> None:
    """모델 Enum에는 있는데 DB의 Postgres enum 타입엔 없는 값을 추가한다."""
    # DB에 실제로 있는 값 조회
    db_values: dict[str, set[str]] = {}
    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT t.typname, e.enumlabel FROM pg_type t "
            "JOIN pg_enum e ON e.enumtypid = t.oid"
        )).fetchall()
    for type_name, label in rows:
        db_values.setdefault(type_name, set()).add(label)

    # 모델이 요구하는 값 수집
    wanted: dict[str, list[str]] = {}
    for table in Base.metadata.tables.values():
        for col in table.columns:
            name = getattr(col.type, "name", None)
            values = getattr(col.type, "enums", None)
            if name and values:
                wanted.setdefault(name, [])
                for v in values:
                    if v not in wanted[name]:
                        wanted[name].append(v)

    for enum_name, values in wanted.items():
        if enum_name not in db_values:
            continue  # 아직 없는 타입은 create_all이 만든다
        for value in values:
            if value in db_values[enum_name]:
                continue
            try:
                # ADD VALUE는 트랜잭션 안에서 실행 불가 → autocommit
                with engine.connect().execution_options(
                    isolation_level="AUTOCOMMIT"
                ) as ac:
                    ac.execute(text(
                        f"ALTER TYPE {enum_name} ADD VALUE IF NOT EXISTS '{value}'"
                    ))
                logger.info(f"schema_sync: enum {enum_name}에 '{value}' 추가")
            except Exception as e:
                logger.error(f"schema_sync: enum {enum_name}.'{value}' 추가 실패: {e}")


def sync_schema(engine: Engine) -> None:
    """누락 테이블 생성 + 누락 컬럼/enum 값 추가. 멱등."""
    # 모델 모듈을 불러와야 Base.metadata가 채워진다. 호출자가 불러왔겠거니 하면,
    # metadata가 비어 있어도 오류 없이 '할 일 없음'으로 끝나 스키마가 조용히 어긋난다.
    import app.models.models  # noqa: F401

    if not Base.metadata.tables:
        raise RuntimeError("schema_sync: 모델 metadata가 비어 있습니다 — import 확인 필요")

    Base.metadata.create_all(bind=engine)

    inspector = inspect(engine)
    is_postgres = engine.dialect.name == "postgresql"

    with engine.connect() as conn:
        _add_missing_columns(conn, inspector, engine)

        # 인덱스 생성 (멱등 — IF NOT EXISTS)
        table_names = set(inspector.get_table_names())
        for idx_name, table, cols in _INDEXES:
            if table not in table_names:
                continue
            try:
                conn.execute(text(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table} ({cols})"))
                conn.commit()
            except Exception as e:
                logger.warning(f"schema_sync: 인덱스 {idx_name} 생성 실패 (무시): {e}")

    if is_postgres:
        _add_missing_enum_values(engine)
