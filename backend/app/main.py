import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

from app.core.config import settings
from app.core.database import Base, engine

# Existing routers
from app.api.auth import router as auth_router
from app.api.projects import router as projects_router
from app.api.keywords import router as keywords_router
from app.api.prospects import router as prospects_router
from app.api.collect import router as collect_router
from app.api.email_send import router as email_send_router
from app.api.chrome import router as chrome_router
from app.api.settings import router as settings_router
from app.api.dashboard import router as dashboard_router
from app.api.dm import router as dm_router
from app.api.tracking import router as tracking_router

# Phase 1: Subscription & Payments
from app.api.subscription import router as subscription_router
from app.api.payments import router as payments_router

# Phase 2: Analytics, Notes, Tags
from app.api.analytics import router as analytics_router
from app.api.notes import router as notes_router
from app.api.tags import router as tags_router

# Phase 3: Templates, Sequences, Deliverability
from app.api.templates import router as templates_router
from app.api.sequences import router as sequences_router
from app.api.deliverability import router as deliverability_router

# Phase 4: Pipeline, Calls, Timeline, Proposals, Meetings
from app.api.pipeline import router as pipeline_router
from app.api.calls import router as calls_router
from app.api.timeline import router as timeline_router
from app.api.proposals import proposal_router, template_router as proposal_template_router
from app.api.meetings import slot_router, meeting_router, booking_router

# Phase 5: Onboarding, Teams, Export, API Keys
from app.api.onboarding import router as onboarding_router
from app.api.teams import router as teams_router
from app.api.export import router as export_router
from app.api.api_keys import router as api_keys_router

from app.services.scheduler import start_scheduler, stop_scheduler

# Import all models so they are registered with Base.metadata
import app.models.models  # noqa: F401

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Tables are managed by Alembic/MCP — skip create_all in production
    if settings.DATABASE_URL.startswith("sqlite"):
        Base.metadata.create_all(bind=engine)
    try:
        start_scheduler()
    except Exception:
        pass  # Scheduler may fail in serverless
    yield
    try:
        stop_scheduler()
    except Exception:
        pass


app = FastAPI(
    title="Outreach SaaS API",
    description="B2B outreach automation - prospect collection and multi-channel sending",
    version="2.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "요청이 너무 많습니다. 잠시 후 다시 시도해주세요."},
    )


# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──

# Existing
app.include_router(auth_router)
app.include_router(projects_router)
app.include_router(keywords_router)
app.include_router(prospects_router)
app.include_router(collect_router)
app.include_router(email_send_router)
app.include_router(chrome_router)
app.include_router(settings_router)
app.include_router(dashboard_router)
app.include_router(dm_router)
app.include_router(tracking_router)

# Phase 1
app.include_router(subscription_router)
app.include_router(payments_router)

# Phase 2
app.include_router(analytics_router)
app.include_router(notes_router)
app.include_router(tags_router)

# Phase 3
app.include_router(templates_router)
app.include_router(sequences_router)
app.include_router(deliverability_router)

# Phase 4
app.include_router(pipeline_router)
app.include_router(calls_router)
app.include_router(timeline_router)
app.include_router(proposal_router)
app.include_router(proposal_template_router)
app.include_router(slot_router)
app.include_router(meeting_router)
app.include_router(booking_router)

# Phase 5
app.include_router(onboarding_router)
app.include_router(teams_router)
app.include_router(export_router)
app.include_router(api_keys_router)


@app.middleware("http")
async def add_csp_header(request: Request, call_next):
    response = await call_next(request)
    content_type = response.headers.get("content-type", "")
    if "text/html" in content_type:
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self' 'unsafe-inline' https://js.tosspayments.com; style-src 'self' 'unsafe-inline'"
        )
    return response


@app.get("/api/health")
def health_check():
    return {"status": "ok"}
