from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import structlog
import time

from config import settings
from database import create_tables
from routers import auth, users, projects, teams, matching, milestones, ai
from routers.milestones import webhook_router

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    log.info("antigravity_starting", env=settings.APP_ENV, version=settings.APP_VERSION)
    if settings.DEBUG:
        await create_tables()  # Auto-create tables in dev. Use Alembic in prod.
    yield
    log.info("antigravity_shutdown")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs" if settings.DEBUG else None,   # Hide docs in production
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)


# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://app.antigravity.io"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request timing middleware ──────────────────────────────────────────────────
@app.middleware("http")
async def add_process_time(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration = round((time.perf_counter() - start) * 1000, 2)
    response.headers["X-Process-Time-Ms"] = str(duration)
    return response


# ── Global exception handler ──────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    log.error("unhandled_exception", path=request.url.path, error=str(exc))
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


# ── Routers ───────────────────────────────────────────────────────────────────
PREFIX = "/api/v1"

app.include_router(auth.router,        prefix=PREFIX)
app.include_router(users.router,       prefix=PREFIX)
app.include_router(projects.router,    prefix=PREFIX)
app.include_router(teams.router,       prefix=PREFIX)
app.include_router(matching.router,    prefix=PREFIX)
app.include_router(milestones.router,  prefix=PREFIX)
app.include_router(ai.router,          prefix=PREFIX)
app.include_router(webhook_router,     prefix=PREFIX)


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["System"])
async def health():
    return {"status": "ok", "version": settings.APP_VERSION, "env": settings.APP_ENV}


@app.get("/", tags=["System"])
async def root():
    return {"name": settings.APP_NAME, "docs": "/docs" if settings.DEBUG else "disabled"}
