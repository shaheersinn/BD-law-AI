"""
app/cache/client.py — Redis cache client with typed helpers.

Provides:
  - get / set / delete / exists
  - JSON-aware serialisation
  - key namespacing
  - TTL defaults per data type

Cache key convention:
  {namespace}:{version}:{identifier}

  e.g.:
    client:v1:42                → client detail
    churn:v1:42                 → churn brief for client 42
    triggers:v1:live:ALL:50     → trigger feed page
    geo:v1:intensity            → geo jurisdiction scores
    ai:v1:{prompt_hash}         → AI response cache
"""

import hashlib
import json
import logging
from typing import Any, Optional

import redis.asyncio as aioredis

from app.config import get_settings

log = logging.getLogger(__name__)
settings = get_settings()

# ── TTL constants (seconds) ────────────────────────────────────────────────────
TTL_SHORT    = 60 * 5          #  5 minutes — live feeds
TTL_MEDIUM   = 60 * 30         # 30 minutes — enriched data
TTL_LONG     = 60 * 60 * 4    #  4 hours  — stable intelligence
TTL_AI       = 60 * 60 * 6    #  6 hours  — AI briefs (expensive to regenerate)
TTL_GEO      = 60 * 60 * 12   # 12 hours  — geo scores
TTL_DAY      = 60 * 60 * 24   # 24 hours  — model scores


class CacheClient:
    """
    Async Redis wrapper. Falls back gracefully if Redis is unavailable —
    cache misses are treated as cache empty (no crash).
    """

    def __init__(self) -> None:
        self._redis: Optional[aioredis.Redis] = None

    def _connect(self) -> aioredis.Redis:
        if self._redis is None:
            self._redis = aioredis.from_url(
                str(settings.redis_url),
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
        return self._redis

    # ── Primitives ─────────────────────────────────────────────────────────────

    async def get(self, key: str) -> Optional[Any]:
        try:
            raw = await self._connect().get(key)
            if raw is None:
                return None
            return json.loads(raw)
        except Exception as e:
            log.debug("Cache GET failed for %s: %s", key, e)
            return None

    async def set(self, key: str, value: Any, ttl: int = TTL_MEDIUM) -> bool:
        try:
            await self._connect().setex(key, ttl, json.dumps(value, default=str))
            return True
        except Exception as e:
            log.debug("Cache SET failed for %s: %s", key, e)
            return False

    async def delete(self, key: str) -> bool:
        try:
            await self._connect().delete(key)
            return True
        except Exception as e:
            log.debug("Cache DELETE failed for %s: %s", key, e)
            return False

    async def exists(self, key: str) -> bool:
        try:
            return bool(await self._connect().exists(key))
        except Exception:
            return False

    async def invalidate_pattern(self, pattern: str) -> int:
        """Delete all keys matching a glob pattern. Use sparingly."""
        try:
            keys = await self._connect().keys(pattern)
            if keys:
                return await self._connect().delete(*keys)
            return 0
        except Exception as e:
            log.debug("Cache invalidate_pattern failed: %s", e)
            return 0

    async def incr(self, key: str, amount: int = 1) -> Optional[int]:
        """Atomic increment — used for rate limiting."""
        try:
            return await self._connect().incr(key, amount)
        except Exception:
            return None

    async def expire(self, key: str, ttl: int) -> bool:
        try:
            return bool(await self._connect().expire(key, ttl))
        except Exception:
            return False

    async def health_check(self) -> bool:
        try:
            return await self._connect().ping()
        except Exception:
            return False

    # ── Domain helpers ──────────────────────────────────────────────────────────

    def client_key(self, client_id: int) -> str:
        return f"client:v1:{client_id}"

    def churn_brief_key(self, client_id: int) -> str:
        return f"churn:v1:{client_id}"

    def trigger_feed_key(self, source: str, min_urgency: int, hours: int) -> str:
        return f"triggers:v1:live:{source}:{min_urgency}:{hours}"

    def geo_intensity_key(self) -> str:
        return "geo:v1:intensity"

    def ai_response_key(self, prompt_key: str, **kwargs) -> str:
        """Deterministic cache key for an AI response."""
        payload = json.dumps({"prompt": prompt_key, **kwargs}, sort_keys=True)
        digest = hashlib.sha256(payload.encode()).hexdigest()[:16]
        return f"ai:v1:{prompt_key}:{digest}"

    def rate_limit_key(self, user_id: int, endpoint: str) -> str:
        return f"ratelimit:v1:{user_id}:{endpoint}"

    def model_perf_key(self) -> str:
        return "model:v1:performance"

    async def get_or_set(
        self,
        key: str,
        factory,
        ttl: int = TTL_MEDIUM,
    ) -> Any:
        """
        Cache-aside pattern.
        Returns cached value if present, otherwise calls factory(), caches result.
        factory can be sync or async.
        """
        cached = await self.get(key)
        if cached is not None:
            return cached

        import inspect
        if inspect.iscoroutinefunction(factory):
            value = await factory()
        else:
            value = factory()

        await self.set(key, value, ttl)
        return value


# Singleton — import and use everywhere
cache = CacheClient()
