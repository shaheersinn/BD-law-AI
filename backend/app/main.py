"""
app/main.py — ORACLE FastAPI application entry point.

Wires together:
  - Application lifespan (startup/shutdown)
  - All middleware (CORS, error handling, request logging, rate limiting)
  - All routers
  - Health and readiness endpoints
  - Static file serving (React SPA in production)

Architecture note:
  The app uses lifespan context manager (not deprecated on_event).
  Middleware is added outermost-first (last added = first executed on request).
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from jose import JWTError

from app.config import get_settings
from app.database import (
    check_db_connection,
    check_mongo_connection,
    close_mongo_connection,
    dispose_engine,
)

settings = get_settings()

# ── Structured Logging Setup ───────────────────────────────────────────────────

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.dev.ConsoleRenderer()
        if settings.is_development
        else structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))

log = structlog.get_logger(__name__)

# ── Sentry (production error monitoring) ──────────────────────────────────────

if settings.sentry_dsn:
    import sentry_sdk
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.environment,
        integrations=[
            FastApiIntegration(),
            SqlalchemyIntegration(),
            CeleryIntegration(monitor_beat_tasks=True),
        ],
        traces_sample_rate=0.1 if settings.is_production else 0.0,
        profiles_sample_rate=0.1 if settings.is_production else 0.0,
    )
    log.info("Sentry initialised", environment=settings.environment)


# ── Application Lifespan ───────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[type-arg]
    """
    Manage application startup and shutdown.

    Startup:
      1. Check PostgreSQL connection
      2. Check MongoDB connection
      3. Warm up entity resolver
      4. Create required directories
      5. Log startup complete

    Shutdown:
      1. Dispose PostgreSQL engine (drain pool)
      2. Close MongoDB client
    """
    # ── Startup ────────────────────────────────────────────────────────────────
    log.info(
        "ORACLE starting",
        version=settings.app_version,
        environment=settings.environment,
        debug=settings.debug,
    )

    # PostgreSQL health check
    pg_ok = await check_db_connection()
    if pg_ok:
        log.info("PostgreSQL connected")
    else:
        log.warning("PostgreSQL UNREACHABLE — API degraded, some endpoints unavailable")

    # MongoDB health check
    mongo_ok = await check_mongo_connection()
    if mongo_ok:
        log.info("MongoDB connected")
    else:
        log.warning("MongoDB UNREACHABLE — social signal features degraded")

    # Ensure required local directories exist
    for directory in [
        settings.models_dir,
        settings.data_dir,
        f"{settings.data_dir}/raw",
        f"{settings.data_dir}/features",
        f"{settings.data_dir}/labels",
        f"{settings.data_dir}/training",
    ]:
        Path(directory).mkdir(parents=True, exist_ok=True)

    # Phase 7: warm up ML orchestrator (non-blocking — API degrades gracefully if models absent)
    try:
        from app.ml.orchestrator import get_orchestrator

        orchestrator = get_orchestrator()
        if not orchestrator._loaded:
            orchestrator.load()
            log.info("ML orchestrator loaded at startup")
    except Exception:
        log.warning(
            "ML orchestrator failed to load at startup — scoring endpoints will return empty"
        )

    log.info("ORACLE startup complete", pg=pg_ok, mongo=mongo_ok)

    yield  # Application runs here

    # ── Shutdown ───────────────────────────────────────────────────────────────
    log.info("ORACLE shutting down")
    await dispose_engine()
    await close_mongo_connection()
    log.info("ORACLE shutdown complete")


# ── FastAPI Application ────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "ORACLE — BigLaw BD Intelligence Platform. "
        "Predicts mandate probability across 34 practice areas × 3 time horizons."
    ),
    docs_url="/api/docs" if not settings.is_production else None,
    redoc_url="/api/redoc" if not settings.is_production else None,
    openapi_url="/api/openapi.json" if not settings.is_production else None,
    lifespan=lifespan,
)


# ── Middleware ─────────────────────────────────────────────────────────────────
# NOTE: Middleware is executed in reverse registration order.
# Last added = outermost = first executed on incoming request.

# Import middleware here to avoid circular imports at module level
from app.middleware.error_handler import (  # noqa: E402
    ErrorHandlerMiddleware,
    RequestLoggingMiddleware,
)
from app.middleware.rate_limiter import RateLimitMiddleware  # noqa: E402
from app.middleware.security_headers import SecurityHeadersMiddleware  # noqa: E402

app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(SecurityHeadersMiddleware, is_production=settings.is_production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-Correlation-ID"],
    expose_headers=["X-Request-ID", "X-Response-Time", "X-RateLimit-Remaining"],
)


# ── Exception Handlers ─────────────────────────────────────────────────────────


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Return structured JSON error for all HTTP exceptions."""
    request_id = getattr(request.state, "request_id", "-")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "code": f"HTTP_{exc.status_code}",
            "request_id": request_id,
            "path": str(request.url.path),
            "status_code": exc.status_code,
        },
        headers={
            "X-Request-ID": request_id,
            **(exc.headers or {}),
        },
    )


@app.exception_handler(JWTError)
async def jwt_exception_handler(request: Request, exc: JWTError) -> JSONResponse:
    """Return 401 for all JWT errors (invalid, expired, malformed)."""
    request_id = getattr(request.state, "request_id", "-")
    log.warning("JWT error", path=request.url.path, error=str(exc))
    return JSONResponse(
        status_code=401,
        content={
            "error": "Token invalid or expired",
            "code": "INVALID_TOKEN",
            "request_id": request_id,
            "path": str(request.url.path),
            "status_code": 401,
        },
        headers={
            "WWW-Authenticate": "Bearer",
            "X-Request-ID": request_id,
        },
    )


# ── Routers ────────────────────────────────────────────────────────────────────
# Imported here to avoid circular imports. Each router registers its own prefix.

from app.auth import router as auth_router  # noqa: E402

PREFIX = "/api"

app.include_router(auth_router.router, prefix=PREFIX)

# Phase 1B — Scraper Health Dashboard
from app.routes.scrapers import router as scrapers_router  # noqa: E402

app.include_router(scrapers_router, prefix=PREFIX)

# Phase 3 — Ground Truth Pipeline
from app.routes.ground_truth import router as ground_truth_router  # noqa: E402

app.include_router(ground_truth_router, prefix=PREFIX)

# Phase 4 — LLM Training Pipeline
from app.routes.training import router as training_router  # noqa: E402

app.include_router(training_router, prefix=PREFIX)

# Phase 7 — Scoring API
from app.routes.companies import router as companies_router  # noqa: E402
from app.routes.scores import router as scores_router  # noqa: E402
from app.routes.signals import router as signals_router  # noqa: E402
from app.routes.trends import router as trends_router  # noqa: E402

app.include_router(scores_router, prefix=PREFIX)
app.include_router(companies_router, prefix=PREFIX)
app.include_router(signals_router, prefix=PREFIX)
app.include_router(trends_router, prefix=PREFIX)

# Phase 9 — Feedback Loop
from app.routes.feedback import router as feedback_router  # noqa: E402

app.include_router(feedback_router, prefix=PREFIX)

# Phase 10 — Prometheus Metrics
from app.routes.metrics import router as metrics_router  # noqa: E402

app.include_router(metrics_router, prefix=PREFIX)

# Phase 8B — Additional BD intelligence routes
from app.routes.analytics import router as analytics_router  # noqa: E402
from app.routes.clients import router as clients_router  # noqa: E402
from app.routes.geo import router as geo_router  # noqa: E402
from app.routes.triggers import router as triggers_router  # noqa: E402
from app.routes.watchlist import router as watchlist_router  # noqa: E402

app.include_router(watchlist_router, prefix=PREFIX)
app.include_router(analytics_router, prefix=PREFIX)
app.include_router(geo_router, prefix=PREFIX)
app.include_router(clients_router, prefix=PREFIX)
app.include_router(triggers_router, prefix=PREFIX)


# ── System Endpoints ───────────────────────────────────────────────────────────


@app.get("/api/health", tags=["system"], summary="Health check")
async def health() -> dict:  # type: ignore[type-arg]
    """
    Health check endpoint.

    Returns the health status of all system components.
    Used by DigitalOcean App Platform for container health monitoring.
    """
    pg_ok = await check_db_connection()
    mongo_ok = await check_mongo_connection()

    # Import cache health check here to avoid circular imports
    from app.cache.client import cache as redis_cache

    redis_ok = await redis_cache.health_check()

    try:
        from app.ml.orchestrator import get_orchestrator

        ml_ready = get_orchestrator()._loaded
    except Exception:
        ml_ready = False

    overall = "ok" if (pg_ok and mongo_ok and redis_ok) else "degraded"

    return {
        "status": overall,
        "version": settings.app_version,
        "environment": settings.environment,
        "ml_ready": ml_ready,
        "components": {
            "postgresql": "connected" if pg_ok else "unreachable",
            "mongodb": "connected" if mongo_ok else "unreachable",
            "redis": "connected" if redis_ok else "unreachable",
            "ml": "ready" if ml_ready else "not_loaded",
        },
    }


@app.get("/api/ready", tags=["system"], summary="Readiness check")
async def ready() -> JSONResponse:
    """
    Readiness check endpoint.

    Returns 200 only when the application is ready to serve traffic.
    Used by load balancers and deployment orchestration.
    PostgreSQL must be connected — other services degrade gracefully.
    """
    pg_ok = await check_db_connection()
    if not pg_ok:
        return JSONResponse(
            status_code=503,
            content={"ready": False, "reason": "PostgreSQL unreachable"},
        )
    return JSONResponse(status_code=200, content={"ready": True})


@app.get("/api/version", tags=["system"], summary="Version info")
async def version() -> dict:  # type: ignore[type-arg]
    """Return application version and build information."""
    return {
        "version": settings.app_version,
        "environment": settings.environment,
        "name": settings.app_name,
    }


# ── React SPA (production) ─────────────────────────────────────────────────────

FRONTEND_DIST = Path(__file__).parent.parent.parent / "frontend" / "dist"

if FRONTEND_DIST.exists():
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str) -> FileResponse | JSONResponse:
        """
        Serve React SPA for all non-API routes.

        In production, FastAPI serves the built React app.
        In development, the Vite dev server handles frontend (port 5173).
        """
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API endpoint not found")

        index = FRONTEND_DIST / "index.html"
        if index.exists():
            return FileResponse(
                str(index),
                headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
            )
        return JSONResponse(
            status_code=503,
            content={"error": "Frontend not built. Run: cd frontend && npm run build"},
        )
