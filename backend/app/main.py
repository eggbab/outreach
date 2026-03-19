from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import Base, engine
from app.api.auth import router as auth_router
from app.api.projects import router as projects_router
from app.api.keywords import router as keywords_router
from app.api.prospects import router as prospects_router
from app.api.collect import router as collect_router
from app.api.email_send import router as email_send_router
from app.api.chrome import router as chrome_router
from app.api.settings import router as settings_router

# Import all models so they are registered with Base.metadata
import app.models.models  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all tables on startup
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Outreach SaaS API",
    description="B2B outreach automation - prospect collection and multi-channel sending",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth_router)
app.include_router(projects_router)
app.include_router(keywords_router)
app.include_router(prospects_router)
app.include_router(collect_router)
app.include_router(email_send_router)
app.include_router(chrome_router)
app.include_router(settings_router)


@app.get("/api/health")
def health_check():
    return {"status": "ok"}
