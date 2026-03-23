"""
app/middleware/error_handler.py — Error handling and request logging middleware.

ErrorHandlerMiddleware: Catches all unhandled exceptions and returns structured
JSON responses instead of exposing raw Python tracebacks.

RequestLoggingMiddleware: Logs every request with method, path, status code,
and duration. Attaches a unique request_id to every request for tracing.
"""

from __future__ import annotations

import time
import uuid
from typing import Callable

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

log = structlog.get_logger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """
    Catch all unhandled exceptions and return structured JSON errors.

    Without this middleware, FastAPI returns HTML 500 errors for unhandled
    exceptions in production, which leaks implementation details and breaks
    API clients expecting JSON.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:  # type: ignore[type-arg]
        try:
            return await call_next(request)
        except Exception as exc:
            request_id = getattr(request.state, "request_id", str(uuid.uuid4()))

            log.exception(
                "Unhandled exception",
                request_id=request_id,
                path=str(request.url.path),
                method=request.method,
                exc_type=type(exc).__name__,
            )

            # Never expose internal error details in production
            from app.config import get_settings
            settings = get_settings()

            error_detail = (
                str(exc)
                if settings.is_development
                else "An internal server error occurred"
            )

            return JSONResponse(
                status_code=500,
                content={
                    "error": error_detail,
                    "code": "INTERNAL_SERVER_ERROR",
                    "request_id": request_id,
                    "path": str(request.url.path),
                    "status_code": 500,
                },
                headers={"X-Request-ID": request_id},
            )


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Log every HTTP request with structured context.

    Attaches a unique request_id to request.state for use throughout
    the request lifecycle (error handlers, route handlers, services).

    Logs: method, path, status code, duration, request_id
    Skips: /api/health, /api/ready (too noisy in production)
    """

    SKIP_PATHS = {"/api/health", "/api/ready", "/api/version"}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:  # type: ignore[type-arg]
        # Generate unique request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
        request.state.request_id = request_id

        start_time = time.perf_counter()
        response: Response = Response(status_code=500)  # default if exception occurs

        try:
            response = await call_next(request)
            return response
        finally:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

            # Skip logging for health/readiness endpoints
            if request.url.path not in self.SKIP_PATHS:
                log.info(
                    "Request",
                    request_id=request_id,
                    method=request.method,
                    path=str(request.url.path),
                    status_code=response.status_code,
                    duration_ms=duration_ms,
                )

            # Add response headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{duration_ms}ms"
