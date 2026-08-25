import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

from app.core.config import settings
from app.core.database import Base, engine
from app.core.rate_limit import limiter

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

# Phase 1: Subscription & Payments (계좌이체)
from app.api.subscription import router as subscription_router
from app.api.payments import router as payments_router, admin_router as payments_admin_router

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

# Phase 6: Discover, Benchmarks, Blacklist
from app.api.discover import router as discover_router
from app.api.benchmarks import router as benchmarks_router
from app.api.blacklist import router as blacklist_router
from app.api.admin import router as admin_router
from app.api.extension import router as extension_router
from app.api.tasks import router as tasks_router

from app.services.scheduler import start_scheduler, stop_scheduler

# Import all models so they are registered with Base.metadata
import app.models.models  # noqa: F401

# limiter는 app.core.rate_limit에서 import (모든 라우터가 공유)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 스키마 관리는 create_all 기반 (프로젝트 컨벤션) — 누락 테이블/컬럼을 멱등하게 보정
    try:
        from app.core.schema_sync import sync_schema
        sync_schema(engine)
    except Exception:
        logging.getLogger(__name__).exception("schema sync failed — starting anyway")
    # 재시작으로 죽은 채 running으로 남은 작업 정리 (수집 영구 차단 방지)
    try:
        from app.core.database import SessionLocal
        from app.core.job_reaper import reap_stale_jobs
        _db = SessionLocal()
        try:
            reap_stale_jobs(_db, startup=True)
        finally:
            _db.close()
    except Exception:
        logging.getLogger(__name__).exception("job reaper failed — starting anyway")
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


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception):
    """예상하지 못한 서버 오류를 사용자가 이해할 한국어로 변환."""
    # FastAPI HTTPException은 자체 핸들러가 처리하므로 이건 진짜 예외만 잡힘
    logger = logging.getLogger("app.error")
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "일시적인 오류가 발생했습니다. 잠시 후 다시 시도해주세요. 문제가 계속되면 고객센터에 문의해주세요.",
        },
    )


# CORS — 와일드카드 대신 실제 사용하는 메서드/헤더만 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    # 크롬 확장(백그라운드 워커)의 origin은 chrome-extension://<id> — 목록 관리 대신 스킴 단위 허용
    allow_origin_regex=r"^chrome-extension://[a-p]{32}$",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key", "Accept"],
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
app.include_router(payments_admin_router)

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

# Phase 6
app.include_router(discover_router)
app.include_router(benchmarks_router)
app.include_router(blacklist_router)
app.include_router(admin_router)
app.include_router(extension_router)
app.include_router(tasks_router)


_CSP_VALUE = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; "  # 랜딩 3D 배경 텍스처가 data: URI 사용
    "connect-src 'self'"
)


@app.middleware("http")
async def add_csp_header(request: Request, call_next):
    response = await call_next(request)
    content_type = response.headers.get("content-type", "")
    if "text/html" in content_type:
        response.headers["Content-Security-Policy"] = _CSP_VALUE
    return response


@app.get("/api/health")
def health_check():
    return {"status": "ok"}


# Serve frontend static files in production
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# 로컬(backend/app/main.py)과 Docker(/app/app/main.py)에서 dist 위치가 달라 후보를 모두 시도
_dist_candidates = [
    Path(__file__).parent.parent.parent / "frontend" / "dist",  # 로컬 monorepo
    Path(__file__).parent.parent / "frontend" / "dist",          # Docker (/app/frontend/dist)
    Path("/app/frontend/dist"),                                   # Docker 절대경로 fallback
]
_frontend_dist = next((p for p in _dist_candidates if p.exists()), _dist_candidates[0])
_frontend_assets = _frontend_dist / "assets"
if _frontend_dist.exists() and _frontend_assets.exists():
    _index_html = _frontend_dist / "index.html"

    # Serve static assets (JS, CSS, images)
    app.mount("/assets", StaticFiles(directory=str(_frontend_assets)), name="static-assets")

    # Serve other static files (manifest, icons, etc.)
    @app.get("/manifest.json")
    def serve_manifest():
        return FileResponse(str(_frontend_dist / "manifest.json"))

    @app.get("/favicon.svg")
    def serve_favicon():
        return FileResponse(str(_frontend_dist / "favicon.svg"))

    @app.get("/sw.js")
    def serve_service_worker():
        # SPA fallback이 index.html을 돌려주면 MIME 오류로 등록 실패 — 직접 서빙
        return FileResponse(str(_frontend_dist / "sw.js"), media_type="application/javascript")

    _icons_dir = _frontend_dist / "icons"
    if _icons_dir.exists():
        app.mount("/icons", StaticFiles(directory=str(_icons_dir)), name="static-icons")

    # SPA fallback middleware — only for non-API, non-asset GET requests
    from starlette.middleware.base import BaseHTTPMiddleware

    class SPAFallbackMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            response = await call_next(request)
            # If a non-API GET request got 404, serve index.html for SPA routing
            path = request.url.path
            if (
                request.method == "GET"
                and response.status_code == 404
                and not path.startswith("/api/")
                and not path.startswith("/assets/")
            ):
                fallback = FileResponse(str(_index_html))
                fallback.headers["Content-Security-Policy"] = _CSP_VALUE
                return fallback
            return response

    app.add_middleware(SPAFallbackMiddleware)
