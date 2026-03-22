import os

# Override DATABASE_URL before any app imports
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import pytest
from contextlib import asynccontextmanager
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

# Now import app components (they'll use the overridden DATABASE_URL)
from app.core.database import Base, get_db
from app.main import app as fastapi_app

# Import all models so they are registered with Base.metadata
import app.models.models  # noqa: F401

# Create test engine (SQLite in-memory)
test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@event.listens_for(test_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


# Override lifespan to use test engine
original_lifespan = fastapi_app.router.lifespan_context


@asynccontextmanager
async def test_lifespan(app):
    Base.metadata.create_all(bind=test_engine)
    yield


fastapi_app.router.lifespan_context = test_lifespan

# Rate limiting is only applied via @limiter.limit decorators on specific
# endpoints (collect, email_send). Auth endpoints use app-level middleware.
# Tests run without hitting real rate limits due to fresh state per test.


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database for each test."""
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(db_session):
    """FastAPI TestClient with overridden DB dependency."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    fastapi_app.dependency_overrides[get_db] = override_get_db
    with TestClient(fastapi_app) as c:
        yield c
    fastapi_app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def auth_headers(client):
    """Sign up a test user and return authorization headers."""
    response = client.post(
        "/api/auth/signup",
        json={
            "email": "test@example.com",
            "password": "testpassword123",
            "name": "Test User",
        },
    )
    assert response.status_code == 201
    token = response.json()["token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def project_id(client, auth_headers):
    """Create a test project and return its ID."""
    response = client.post(
        "/api/projects/",
        json={"name": "Test Project"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    return response.json()["id"]
