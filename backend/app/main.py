"""
app/main.py — FastAPI application entry point v2.
Wires auth, caching, error handling, all routers, startup tasks.
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from jose import JWTError

from app.config import get_settings
from app.database import check_db_connection
from app.middleware.error_handler import ErrorHandlerMiddleware, RequestLoggingMiddleware
from app.routes import analytics, geo, triggers, watchlist
from app.routes import ai as ai_routes
from app.routes import clients
from app.auth import router as auth_router

settings = get_settings()

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.ConsoleRenderer() if settings.debug else structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
)
logging.basicConfig(level=logging.DEBUG if settings.debug else logging.INFO)
log = structlog.get_logger(__name__)

if settings.sentry_dsn:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    sentry_sdk.init(
        dsn=settings.sentry_dsn, environment=settings.environment,
        integrations=[FastApiIntegration()], traces_sample_rate=0.05,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("BD for Law API starting", version=settings.app_version, env=settings.environment)

    db_ok = await check_db_connection()
    log.info("Database", status="connected" if db_ok else "UNREACHABLE")

    from app.cache.client import cache as redis_client
    redis_ok = await redis_client.health_check()
    log.info("Redis", status="connected" if redis_ok else "unreachable")

    if db_ok:
        try:
            from app.database import AsyncSessionLocal
            from app.services.entity_resolution import resolver
            async with AsyncSessionLocal() as db:
                count = await resolver.rebuild(db)
            log.info("Entity resolver", entities=count)
        except Exception as e:
            log.warning("Entity resolver warm-up failed (non-fatal)", error=str(e))

    Path(settings.models_dir).mkdir(parents=True, exist_ok=True)
    log.info("Startup complete")
    yield
    log.info("Shutting down")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="ORACLE — BigLaw BD intelligence platform REST API",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# Middleware (outermost first)
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID", "X-Response-Time", "X-RateLimit-Remaining"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    request_id = getattr(request.state, "request_id", "-")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "code": f"HTTP_{exc.status_code}",
                 "request_id": request_id, "path": request.url.path,
                 "status_code": exc.status_code},
        headers={"X-Request-ID": request_id, **(exc.headers or {})},
    )


@app.exception_handler(JWTError)
async def jwt_error_handler(request: Request, exc: JWTError):
    request_id = getattr(request.state, "request_id", "-")
    return JSONResponse(
        status_code=401,
        content={"error": "Token invalid or expired", "code": "INVALID_TOKEN",
                 "request_id": request_id, "path": request.url.path, "status_code": 401},
        headers={"WWW-Authenticate": "Bearer", "X-Request-ID": request_id},
    )


PREFIX = "/api"
app.include_router(auth_router.router,  prefix=PREFIX)
app.include_router(clients.router,      prefix=PREFIX)
app.include_router(triggers.router,     prefix=PREFIX)
app.include_router(geo.router,          prefix=PREFIX)
app.include_router(ai_routes.router,    prefix=PREFIX)
app.include_router(watchlist.router,    prefix=PREFIX)
app.include_router(analytics.router,    prefix=PREFIX)


@app.get("/api/health", tags=["system"])
async def health():
    db_ok = await check_db_connection()
    from app.cache.client import cache
    redis_ok = await cache.health_check()
    return {
        "status": "ok" if (db_ok and redis_ok) else "degraded",
        "version": settings.app_version,
        "environment": settings.environment,
        "components": {
            "database": "connected" if db_ok else "unreachable",
            "redis":    "connected" if redis_ok else "unreachable",
        },
    }


@app.get("/api/ready", tags=["system"])
async def ready():
    db_ok = await check_db_connection()
    if not db_ok:
        return JSONResponse(status_code=503, content={"ready": False, "reason": "Database unreachable"})
    return {"ready": True}


# Serve React SPA in production
FRONTEND_DIST = Path(__file__).parent.parent.parent / "frontend" / "dist"
if FRONTEND_DIST.exists():
    assets = FRONTEND_DIST / "assets"
    if assets.exists():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API endpoint not found")
        index = FRONTEND_DIST / "index.html"
        if index.exists():
            return FileResponse(index, headers={"Cache-Control": "no-cache"})
        return JSONResponse(status_code=503, content={"error": "Frontend not built. Run: cd frontend && npm run build"})
