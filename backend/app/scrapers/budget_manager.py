"""
app/scrapers/budget_manager.py — API budget manager for all free-tier sources.

Tracks API credit consumption across all sources with daily/monthly limits.
Prevents ORACLE from burning through free-tier quotas before high-priority
companies are scraped.

Free Tier Limits (as of 2026):
  Alpha Vantage:    25 requests/day
  Proxycurl:        10 credits/month
  Groq:             14,400 requests/day (Phase 4 training only)
  OpenSky:          4,000 API credits/day (anonymous), more with account
  Twitter/X:        ~500K tweets/month (Basic tier)
  CANLII:           No documented limit, but rate-limited at ~1 req/sec
  HIBP:             50 requests/month (free tier)

Budget strategy:
  1. Priority-weighted allocation — high-priority companies (watchlist_priority=1)
     get allocated more API credits than low-priority
  2. Graceful degradation — when budget is exhausted, fall back to cached data
     or triangulation from adjacent sources
  3. Daily reset at midnight UTC
  4. Monthly reset on 1st of each month
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Optional

log = logging.getLogger(__name__)


# ── Budget Configurations ─────────────────────────────────────────────────────

BUDGET_CONFIGS: dict[str, dict] = {
    "alpha_vantage": {
        "daily_limit": 25,
        "monthly_limit": None,
        "priority": "market_data",
    },
    "proxycurl": {
        "daily_limit": None,
        "monthly_limit": 10,
        "priority": "jobs",
    },
    "opensky": {
        "daily_limit": 4000,
        "monthly_limit": None,
        "priority": "geo",
    },
    "twitter": {
        "daily_limit": None,
        "monthly_limit": 500000,
        "priority": "social",
    },
    "hibp": {
        "daily_limit": None,
        "monthly_limit": 50,
        "priority": "security",
    },
    "groq": {
        "daily_limit": 14400,
        "monthly_limit": None,
        "priority": "training_only",  # Never used in production scoring
    },
    "canlii": {
        "daily_limit": 5000,  # Conservative self-imposed limit
        "monthly_limit": None,
        "priority": "legal",
    },
    "google_trends": {
        "daily_limit": 100,  # pytrends informal rate limit
        "monthly_limit": None,
        "priority": "geo",
    },
}


class ApiBudgetManager:
    """
    Tracks API credit usage across all free-tier sources.

    Uses Redis for persistence (survives restarts).
    Falls back to in-memory if Redis unavailable.
    """

    def __init__(self) -> None:
        self._memory: dict[str, dict] = {}
        self._redis_available = False
        self.log = logging.getLogger("oracle.scrapers.budget_manager")

    async def _get_redis(self) -> Optional[object]:
        """Get Redis client. Returns None if unavailable."""
        try:
            from app.cache.client import get_redis
            return await get_redis()
        except Exception:
            return None

    def _daily_key(self, source: str) -> str:
        today = date.today().isoformat()
        return f"oracle:budget:daily:{source}:{today}"

    def _monthly_key(self, source: str) -> str:
        now = datetime.now(tz=timezone.utc)
        return f"oracle:budget:monthly:{source}:{now.year}:{now.month:02d}"

    async def check_budget(self, source: str, amount: int = 1) -> bool:
        """
        Check if a source has budget remaining.

        Returns True if request is allowed, False if budget exhausted.
        Does NOT consume budget — call consume() after the request succeeds.
        """
        config = BUDGET_CONFIGS.get(source)
        if config is None:
            return True  # Unknown sources are not limited

        redis = await self._get_redis()

        # Check daily limit
        if config["daily_limit"] is not None:
            daily_used = await self._get_count(redis, self._daily_key(source))
            if daily_used + amount > config["daily_limit"]:
                self.log.warning(
                    "Budget: %s daily limit reached (%d/%d)",
                    source, daily_used, config["daily_limit"],
                )
                return False

        # Check monthly limit
        if config["monthly_limit"] is not None:
            monthly_used = await self._get_count(redis, self._monthly_key(source))
            if monthly_used + amount > config["monthly_limit"]:
                self.log.warning(
                    "Budget: %s monthly limit reached (%d/%d)",
                    source, monthly_used, config["monthly_limit"],
                )
                return False

        return True

    async def consume(self, source: str, amount: int = 1) -> None:
        """Record that `amount` API credits have been consumed for `source`."""
        redis = await self._get_redis()

        daily_key = self._daily_key(source)
        monthly_key = self._monthly_key(source)

        if redis is not None:
            try:
                await redis.incrby(daily_key, amount)  # type: ignore
                await redis.expire(daily_key, 86400 * 2)  # 2 day TTL
                await redis.incrby(monthly_key, amount)  # type: ignore
                await redis.expire(monthly_key, 86400 * 35)  # 35 day TTL
                return
            except Exception:
                pass

        # Fallback: in-memory
        if daily_key not in self._memory:
            self._memory[daily_key] = 0
        self._memory[daily_key] += amount
        if monthly_key not in self._memory:
            self._memory[monthly_key] = 0
        self._memory[monthly_key] += amount

    async def get_usage(self, source: str) -> dict:
        """Return current usage stats for a source."""
        config = BUDGET_CONFIGS.get(source, {})
        redis = await self._get_redis()

        daily_used = await self._get_count(redis, self._daily_key(source))
        monthly_used = await self._get_count(redis, self._monthly_key(source))

        return {
            "source": source,
            "daily_used": daily_used,
            "daily_limit": config.get("daily_limit"),
            "monthly_used": monthly_used,
            "monthly_limit": config.get("monthly_limit"),
            "daily_remaining": (
                config["daily_limit"] - daily_used
                if config.get("daily_limit") else None
            ),
            "monthly_remaining": (
                config["monthly_limit"] - monthly_used
                if config.get("monthly_limit") else None
            ),
        }

    async def _get_count(self, redis: Optional[object], key: str) -> int:
        """Get counter value from Redis or memory."""
        if redis is not None:
            try:
                val = await redis.get(key)  # type: ignore
                return int(val) if val else 0
            except Exception:
                pass
        return self._memory.get(key, 0)


# ── Singleton ─────────────────────────────────────────────────────────────────

_budget_manager: Optional[ApiBudgetManager] = None


def get_budget_manager() -> ApiBudgetManager:
    """Get the singleton budget manager instance."""
    global _budget_manager
    if _budget_manager is None:
        _budget_manager = ApiBudgetManager()
    return _budget_manager
