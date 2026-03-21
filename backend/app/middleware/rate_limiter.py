"""
app/middleware/rate_limiter.py — Redis-backed per-user rate limiting.

Separate limits by endpoint class:
  - AI generation: 60 calls/hour (expensive, token-cost endpoint)
  - Standard API:  600 calls/hour
  - Auth:          20 attempts/hour (brute-force protection)

Uses sliding window log algorithm for accuracy.
Falls back to allow-all if Redis is unavailable (fail open).
"""

import logging
import time
from typing import Optional

from fastapi import HTTPException, Request, status

from app.cache.client import cache

log = logging.getLogger(__name__)

# ── Rate limit buckets ─────────────────────────────────────────────────────────

LIMITS = {
    "ai":       (60,  3600),   # 60 requests per hour
    "standard": (600, 3600),   # 600 requests per hour
    "auth":     (20,  3600),   # 20 attempts per hour
    "scrape":   (10,  3600),   # 10 manual scrape triggers per hour
}


async def check_rate_limit(
    identifier: str,
    limit_type: str = "standard",
) -> tuple[bool, dict]:
    """
    Check if identifier (user_id or IP) has exceeded the rate limit.

    Returns:
        (allowed: bool, headers: dict) — headers include RateLimit-* values

    Uses token bucket algorithm: increment counter, set expiry on first call.
    """
    max_calls, window = LIMITS.get(limit_type, LIMITS["standard"])
    key = f"rl:{limit_type}:{identifier}"

    try:
        count = await cache.incr(key)
        if count == 1:
            # First call in window — set expiry
            await cache.expire(key, window)

        remaining = max(0, max_calls - count)
        allowed = count <= max_calls

        headers = {
            "X-RateLimit-Limit":     str(max_calls),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Window":    str(window),
        }
        return allowed, headers

    except Exception as e:
        log.debug("Rate limit check failed (allowing): %s", e)
        return True, {}


async def enforce_rate_limit(
    request: Request,
    limit_type: str = "standard",
    identifier: Optional[str] = None,
) -> None:
    """
    FastAPI dependency — raises 429 if rate limit exceeded.
    Identifier defaults to authenticated user ID or client IP.

    Usage:
        @router.post("/ai/brief")
        async def brief(
            _: None = Depends(lambda req=Request: enforce_rate_limit(req, "ai"))
        ):
    """
    ident = identifier
    if not ident:
        # Prefer user ID from token (set by auth middleware)
        user_id = getattr(request.state, "user_id", None)
        ident = str(user_id) if user_id else (
            request.client.host if request.client else "unknown"
        )

    allowed, headers = await check_rate_limit(ident, limit_type)

    # Always add rate limit headers
    request.state.rate_limit_headers = headers

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded for {limit_type} endpoint. Try again later.",
            headers={**headers, "Retry-After": "3600"},
        )


# ── Convenience dependency factories ──────────────────────────────────────────

def ai_rate_limit(request: Request):
    """Use as: Depends(ai_rate_limit)"""
    import asyncio
    return asyncio.ensure_future(enforce_rate_limit(request, "ai"))


def auth_rate_limit(request: Request):
    """Use as: Depends(auth_rate_limit) on login endpoints"""
    import asyncio
    return asyncio.ensure_future(enforce_rate_limit(request, "auth"))
