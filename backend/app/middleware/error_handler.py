"""
app/middleware/error_handler.py — Structured error handling middleware.

All errors return a consistent JSON envelope:
{
    "error": "human-readable message",
    "code":  "MACHINE_CODE",
    "request_id": "uuid",
    "path": "/api/clients/999",
    "timestamp": "2025-11-14T09:00:00Z"
}

Unhandled exceptions are caught, logged with full traceback to structlog,
and returned as a 500 with a sanitised message (no stack traces to client).
"""

import logging
import time
import uuid
from typing import Callable

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

log = logging.getLogger(__name__)


def _error_body(
    message: str,
    code: str,
    request_id: str,
    path: str,
    status_code: int,
) -> dict:
    return {
        "error": message,
        "code": code,
        "request_id": request_id,
        "path": path,
        "status_code": status_code,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """
    Catches all unhandled exceptions and returns structured JSON errors.
    Also injects X-Request-ID header on every response.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        start = time.perf_counter()

        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{(time.perf_counter() - start)*1000:.1f}ms"
            return response

        except Exception as exc:
            elapsed = (time.perf_counter() - start) * 1000
            log.exception(
                "Unhandled exception",
                extra={
                    "request_id": request_id,
                    "path": request.url.path,
                    "method": request.method,
                    "elapsed_ms": round(elapsed, 1),
                    "exc_type": type(exc).__name__,
                },
            )
            body = _error_body(
                message="An unexpected error occurred. The error has been logged.",
                code="INTERNAL_SERVER_ERROR",
                request_id=request_id,
                path=request.url.path,
                status_code=500,
            )
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content=body,
                headers={"X-Request-ID": request_id},
            )


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Logs every request/response with timing.
    Skips health check and static asset routes to reduce noise.
    """

    SKIP_PATHS = {"/api/health", "/favicon.ico", "/assets"}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip noise
        if any(request.url.path.startswith(p) for p in self.SKIP_PATHS):
            return await call_next(request)

        start = time.perf_counter()
        response = await call_next(request)
        elapsed = (time.perf_counter() - start) * 1000

        request_id = getattr(request.state, "request_id", "-")
        log.info(
            "%s %s %d %.1fms",
            request.method,
            request.url.path,
            response.status_code,
            elapsed,
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "ms": round(elapsed, 1),
                "ip": request.client.host if request.client else "-",
            },
        )
        return response
