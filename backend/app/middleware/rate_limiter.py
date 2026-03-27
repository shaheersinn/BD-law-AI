"""
app/middleware/rate_limiter.py — Per-user Redis-backed rate limiting.

Uses Redis sorted sets (sliding window algorithm) for accurate rate limiting.
The sliding window approach is more accurate than fixed windows and prevents
burst exploitation at window boundaries.

Rate limits:
  - Default: 100 requests per hour per authenticated user
  - Unauthenticated: 20 requests per hour per IP
  - Health/version endpoints: exempt
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import cast

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

log = structlog.get_logger(__name__)

# Endpoints exempt from rate limiting
EXEMPT_PATHS = {"/api/health", "/api/ready", "/api/version", "/api/docs", "/api/redoc"}


async def enforce_rate_limit(
    request: Request | None,
    category: str,
    user_id: str,
    limit: int = 20,
    window_seconds: int = 3600,
) -> None:
    """
    Standalone rate limit check for AI endpoints and other expensive operations.
    Raises 429 if rate limit exceeded. Fails open if Redis is unavailable.
    """
    if request is None:
        return

    key = f"rate_limit:{category}:{user_id}"

    try:
        from app.cache.client import cache as redis_cache

        allowed, remaining = await redis_cache.check_rate_limit(
            key=key,
            limit=limit,
            window_seconds=window_seconds,
        )
    except Exception as e:
        log.warning("Rate limit check failed (Redis unavailable), allowing request", error=str(e))
        return

    if not allowed:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please slow down.",
        )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Sliding window rate limiter using Redis sorted sets.

    Algorithm:
      1. Key = rate_limit:{user_id_or_ip}
      2. Add current timestamp to sorted set with score=timestamp
      3. Remove entries older than the window
      4. Count remaining entries
      5. If count > limit: return 429
      6. Otherwise: proceed

    This ensures requests are evenly distributed over time,
    not just limited per window boundary.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:  # type: ignore[type-arg]
        # Skip exempt paths
        if request.url.path in EXEMPT_PATHS:
            return cast(Response, await call_next(request))  # type: ignore[no-any-return]

        # Get rate limit settings
        from app.config import get_settings

        settings = get_settings()

        # Determine rate limit key
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            key = f"rate_limit:user:{user_id}"
            limit = settings.rate_limit_requests
        else:
            # Use IP for unauthenticated requests
            client_ip = self._get_client_ip(request)
            key = f"rate_limit:ip:{client_ip}"
            limit = 20  # Stricter limit for unauthenticated

        window_seconds = settings.rate_limit_window_seconds

        # Apply rate limit via Redis
        try:
            from app.cache.client import cache as redis_cache

            allowed, remaining = await redis_cache.check_rate_limit(
                key=key,
                limit=limit,
                window_seconds=window_seconds,
            )
        except Exception as e:
            # Redis unavailable — fail open (allow request) to avoid service disruption
            log.warning(
                "Rate limit check failed (Redis unavailable), allowing request", error=str(e)
            )
            return cast(Response, await call_next(request))

        if not allowed:
            request_id = getattr(request.state, "request_id", "-")
            log.warning(
                "Rate limit exceeded",
                key=key,
                request_id=request_id,
                path=str(request.url.path),
            )
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded. Please slow down.",
                    "code": "RATE_LIMIT_EXCEEDED",
                    "request_id": request_id,
                    "path": str(request.url.path),
                    "status_code": 429,
                },
                headers={
                    "Retry-After": str(window_seconds),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time()) + window_seconds),
                },
            )

        response = cast(Response, await call_next(request))
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response

    @staticmethod
    def _get_client_ip(request: Request) -> str:
        """
        Extract client IP from request headers.

        Respects X-Forwarded-For header for requests behind load balancers
        (DigitalOcean App Platform injects this header).
        """
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP in the chain (client IP, not proxy IP)
            return forwarded_for.split(",")[0].strip()
        return request.client.host if request.client else "unknown"
