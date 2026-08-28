"""스키마 자동 보정 테스트.

실제로 있었던 사고: 모델에 users.is_admin을 추가했는데 schema_sync의 손수 적은
목록에 넣는 걸 잊어서, 기존 DB에서 회원가입이 전부 500으로 실패했다.
이제는 목록이 아니라 모델 정의에서 자동으로 찾아내므로, 그 회귀를 여기서 막는다.
"""
import pytest
from sqlalchemy import create_engine, inspect, text

from app.core.schema_sync import sync_schema


@pytest.fixture
def legacy_engine(tmp_path):
    """옛 버전 스키마를 흉내낸 DB — users 테이블에 신규 컬럼들이 빠져 있다."""
    engine = create_engine(f"sqlite:///{tmp_path}/legacy.db")
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                email VARCHAR(255) NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                name VARCHAR(100) NOT NULL,
                plan VARCHAR(20) NOT NULL DEFAULT 'free',
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL
            )
        """))
        conn.commit()
    return engine


class TestSchemaSync:
    def test_adds_columns_missing_from_existing_table(self, legacy_engine):
        """모델에 있고 DB에 없는 컬럼은 전부 자동으로 추가돼야 한다."""
        before = {c["name"] for c in inspect(legacy_engine).get_columns("users")}
        assert "is_admin" not in before  # 사전 조건

        sync_schema(legacy_engine)

        after = {c["name"] for c in inspect(legacy_engine).get_columns("users")}
        for col in ("is_admin", "credits", "is_active", "reset_token",
                    "reset_token_expires_at", "terms_accepted_at"):
            assert col in after, f"{col} 컬럼이 추가되지 않았습니다"

    def test_preserves_existing_rows(self, legacy_engine):
        """이미 있는 데이터를 지우지 않고 컬럼만 덧붙인다."""
        with legacy_engine.connect() as conn:
            conn.execute(text(
                "INSERT INTO users (email, password_hash, name, plan, created_at, updated_at) "
                "VALUES ('old@corp.com', 'x', '기존회원', 'free', '2026-01-01', '2026-01-01')"
            ))
            conn.commit()

        sync_schema(legacy_engine)

        with legacy_engine.connect() as conn:
            row = conn.execute(text(
                "SELECT email, is_admin FROM users WHERE email='old@corp.com'"
            )).first()
        assert row is not None, "기존 행이 사라졌습니다"
        assert row[0] == "old@corp.com"

    def test_is_idempotent(self, legacy_engine):
        """여러 번 실행해도 오류 없이 같은 결과여야 한다 (매 부팅마다 돈다)."""
        sync_schema(legacy_engine)
        first = {c["name"] for c in inspect(legacy_engine).get_columns("users")}
        sync_schema(legacy_engine)
        second = {c["name"] for c in inspect(legacy_engine).get_columns("users")}
        assert first == second

    def test_creates_all_model_tables(self, legacy_engine):
        """누락된 테이블도 함께 만들어야 한다."""
        sync_schema(legacy_engine)
        tables = set(inspect(legacy_engine).get_table_names())
        for t in ("projects", "prospects", "email_logs", "credit_transactions"):
            assert t in tables, f"{t} 테이블이 만들어지지 않았습니다"
