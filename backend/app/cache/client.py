"""
app/cache/client.py — Redis cache client for ORACLE.

Provides:
  - Simple get/set/delete with type-safe helpers
  - TTL-aware caching with signal-type-specific expiry
  - Sliding window rate limiting via sorted sets
  - Health check
  - get_or_set pattern for cache-aside caching

Uses hiredis for faster response parsing (installed as dependency).
Connection pool is managed by the redis-py async client.
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable
from typing import Any, TypeVar

import redis.asyncio as aioredis
from redis.asyncio import Redis

from app.config import get_settings

log = logging.getLogger(__name__)
settings = get_settings()

# Standard TTL tiers (seconds)
TTL_SHORT = 300  # 5 minutes
TTL_MEDIUM = 3600  # 1 hour
TTL_LONG = 21_600  # 6 hours
TTL_AI = 21_600  # 6 hours — AI-generated briefs
TTL_GEO = 43_200  # 12 hours — geospatial data

T = TypeVar("T")

# ── Cache TTL Constants (seconds) ─────────────────────────────────────────────
# Signal-type-specific TTLs. See Phase 1C for full rationale.

TTL = {
    # High-velocity signals — check frequently
    "options_anomaly": 300,  # 5 minutes
    "jet_track": 900,  # 15 minutes
    "breaking_news": 600,  # 10 minutes
    "live_score": 60,  # 1 minute (live feed scores)
    # Medium-velocity signals — check daily
    "job_postings": 86400,  # 24 hours
    "social_sentiment": 43200,  # 12 hours
    "google_trends": 21600,  # 6 hours
    "regulatory_news": 7200,  # 2 hours
    # Low-velocity signals — check weekly
    "sedar_filings": 86400,  # 24 hours
    "canlii_cases": 86400,  # 24 hours
    "osb_insolvency_stats": 604800,  # 7 days
    "scc_decisions": 604800,  # 7 days
    "stats_canada": 604800,  # 7 days
    # Static reference data — cache for a month
    "corporations_canada": 2592000,  # 30 days
    "transport_canada": 2592000,  # 30 days
    "law_firm_posts": 86400,  # 24 hours
    # Computed scores
    "practice_area_score": 3600,  # 1 hour
    "company_features": 7200,  # 2 hours
    # Default fallback
    "default": 3600,  # 1 hour
}


class RedisCache:
    """
    Async Redis cache client.

    Singleton pattern — use the module-level `cache` instance.
    Connection pool is shared across all application requests.
    """

    def __init__(self) -> None:
        self._client: Redis | None = None  # type: ignore[type-arg]

    def _get_client(self) -> Redis:  # type: ignore[type-arg]
        """
        Return Redis client, creating it on first call.

        Uses connection pool for efficient connection reuse.
        hiredis parser is used automatically when installed.
        """
        if self._client is None:
            self._client = aioredis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=50,
                socket_timeout=5,
                socket_connect_timeout=5,
                retry_on_timeout=True,
            )
        return self._client

    async def health_check(self) -> bool:
        """Check Redis connectivity. Returns True if connected."""
        try:
            client = self._get_client()
            result = await client.ping()  # type: ignore[misc]
            return bool(result)
        except Exception as e:
            log.error("Redis health check failed: %s", e)
            return False

    async def get(self, key: str) -> Any | None:
        """
        Get a value from cache.

        Returns:
            Deserialized value if found, None if not found or on error.
        """
        try:
            client = self._get_client()
            value = await client.get(key)
            if value is None:
                return None
            return json.loads(value)
        except Exception as e:
            log.warning("Cache GET failed for key %s: %s", key, e)
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
        signal_type: str | None = None,
    ) -> bool:
        """
        Set a value in cache.

        Args:
            key: Cache key
            value: Value to cache (must be JSON-serializable)
            ttl: TTL in seconds (overrides signal_type TTL)
            signal_type: Use predefined TTL for this signal type

        Returns:
            True if set successfully, False on error.
        """
        try:
            client = self._get_client()
            expire = ttl or TTL.get(signal_type or "default", TTL["default"])
            serialized = json.dumps(value, default=str)
            await client.setex(key, expire, serialized)
            return True
        except Exception as e:
            log.warning("Cache SET failed for key %s: %s", key, e)
            return False

    async def delete(self, key: str) -> bool:
        """Delete a key from cache. Returns True if deleted."""
        try:
            client = self._get_client()
            result: int = await client.delete(key)  # type: ignore[assignment]
            return result > 0
        except Exception as e:
            log.warning("Cache DELETE failed for key %s: %s", key, e)
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a pattern.

        Use sparingly — KEYS command is O(N) and blocks Redis.
        Only safe for low-volume maintenance operations.

        Returns:
            Number of keys deleted.
        """
        try:
            client = self._get_client()
            keys = await client.keys(pattern)
            if keys:
                result: int = await client.delete(*keys)  # type: ignore[assignment]
                return result
            return 0
        except Exception as e:
            log.warning("Cache DELETE PATTERN failed for %s: %s", pattern, e)
            return 0

    async def exists(self, key: str) -> bool:
        """Check if a key exists in cache."""
        try:
            client = self._get_client()
            return bool(await client.exists(key))
        except Exception as e:
            log.warning("Cache EXISTS failed for key %s: %s", key, e)
            return False

    async def get_or_set(
        self,
        key: str,
        factory: Callable[[], Any],
        ttl: int | None = None,
        signal_type: str | None = None,
    ) -> Any:
        """
        Cache-aside pattern: get from cache, or compute and cache.

        Args:
            key: Cache key
            factory: Async callable that computes the value on cache miss
            ttl: TTL override in seconds
            signal_type: Use predefined TTL for this signal type

        Returns:
            Cached or freshly computed value.

        Usage:
            score = await cache.get_or_set(
                f"score:{company_id}",
                lambda: scoring_service.compute(company_id),
                signal_type="practice_area_score",
            )
        """
        cached = await self.get(key)
        if cached is not None:
            return cached

        value = await factory()
        await self.set(key, value, ttl=ttl, signal_type=signal_type)
        return value

    async def check_rate_limit(
        self,
        key: str,
        limit: int,
        window_seconds: int,
    ) -> tuple[bool, int]:
        """
        Sliding window rate limit check using Redis sorted set.

        Algorithm:
          1. Add current timestamp to sorted set
          2. Remove entries outside the sliding window
          3. Count remaining entries
          4. Allow if count <= limit

        Args:
            key: Rate limit key (e.g., "rate_limit:user:123")
            limit: Max requests allowed in the window
            window_seconds: Window size in seconds

        Returns:
            (allowed: bool, remaining: int)
        """
        try:
            client = self._get_client()
            now = time.time()
            window_start = now - window_seconds
            full_key = f"oracle:{key}"

            # Pipeline for atomic execution
            pipe = client.pipeline()
            pipe.zremrangebyscore(full_key, 0, window_start)  # Remove old entries
            pipe.zadd(full_key, {str(now): now})  # Add current request
            pipe.zcard(full_key)  # Count requests in window
            pipe.expire(full_key, window_seconds + 1)  # Set TTL

            results = await pipe.execute()
            request_count = results[2]

            allowed = request_count <= limit
            remaining = max(0, limit - request_count)
            return allowed, remaining

        except Exception as e:
            log.warning("Rate limit check failed: %s", e)
            return True, limit  # Fail open on Redis error

    async def invalidate_company(self, company_id: str) -> int:
        """
        Invalidate all cached data for a company.

        Called when new signals arrive for a company that force
        immediate cache refresh (e.g., SEDAR confidentiality filing).

        Returns:
            Number of keys deleted.
        """
        return await self.delete_pattern(f"oracle:*:{company_id}:*")

    # ── Key helpers ─────────────────────────────────────────────────────────────

    def ai_response_key(self, template_id: str, **params: Any) -> str:
        """Deterministic cache key for AI-generated text responses."""
        sorted_params = ":".join(f"{k}={v}" for k, v in sorted(params.items()))
        return f"oracle:ai:{template_id}:{sorted_params}"

    def client_key(self, client_id: int) -> str:
        """Cache key for a client record."""
        return f"client:v1:{client_id}"

    def trigger_feed_key(self, category: str, limit: int, offset: int) -> str:
        """Cache key for a paginated trigger feed."""
        return f"triggers:v1:live:{category}:{limit}:{offset}"

    def churn_brief_key(self, client_id: int) -> str:
        """Cache key for a client churn brief."""
        return f"client:v1:churn_brief:{client_id}"

    def geo_intensity_key(self) -> str:
        """Cache key for geo intensity data."""
        return "geo:v1:intensity"

    async def invalidate_pattern(self, pattern: str) -> int:
        """Alias for delete_pattern for convenience."""
        return await self.delete_pattern(pattern)

    async def close(self) -> None:
        """Close the Redis connection pool. Called on application shutdown."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None


# ── Singleton Instance ─────────────────────────────────────────────────────────
# Import this in other modules:
#   from app.cache.client import cache

cache = RedisCache()

# Alias for backward-compat with tests that import CacheClient
CacheClient = RedisCache


async def get_redis() -> Redis:
    """Return the underlying redis.asyncio.Redis client from the singleton cache."""
    return cache._get_client()
