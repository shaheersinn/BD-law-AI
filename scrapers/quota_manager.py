"""
app/scrapers/quota_manager.py — Free-Tier API Quota Manager.

Tracks usage of rate-limited and credit-based external APIs.
Prevents exceeding free tiers and triggering paid overages.

Sources with hard monthly limits:
  Twitter/X Basic:    10,000 tweets/month read
  Proxycurl:          10 credits/month (free)
  Alpha Vantage:      25 requests/day (free)
  HIBP:               unlimited reads (paid key: $3.50/mo)
  Reddit OAuth2:      60 req/min, 100/day per endpoint
  Google Trends:      Informal limit ~1,500 req/day (pytrends)

Quota data stored in Redis with TTL aligned to reset periods.
Fails open — if Redis unavailable, quota check returns True (allow).
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any

import structlog

log = structlog.get_logger(__name__)

# ── Quota definitions ─────────────────────────────────────────────────────────
QUOTA_CONFIGS: dict[str, dict[str, Any]] = {
    "twitter_x": {
        "display_name": "Twitter/X API v2 (Basic)",
        "limit": 10_000,
        "window": "monthly",
        "reset_day": 1,         # Resets on 1st of month
        "warn_threshold": 0.80,  # Warn at 80% used
        "hard_stop": 0.95,       # Stop scraping at 95%
    },
    "proxycurl": {
        "display_name": "Proxycurl LinkedIn API",
        "limit": 10,
        "window": "monthly",
        "reset_day": 1,
        "warn_threshold": 0.70,
        "hard_stop": 1.0,       # Use all 10 — they're precious
    },
    "alpha_vantage": {
        "display_name": "Alpha Vantage (Free)",
        "limit": 25,
        "window": "daily",
        "reset_day": None,
        "warn_threshold": 0.80,
        "hard_stop": 0.96,
    },
    "reddit": {
        "display_name": "Reddit OAuth2",
        "limit": 100,
        "window": "per_endpoint_daily",
        "reset_day": None,
        "warn_threshold": 0.85,
        "hard_stop": 0.95,
    },
    "google_trends": {
        "display_name": "Google Trends (pytrends)",
        "limit": 1_400,         # Conservative to avoid IP ban
        "window": "daily",
        "reset_day": None,
        "warn_threshold": 0.75,
        "hard_stop": 0.90,
    },
    "canlii": {
        "display_name": "CanLII API",
        "limit": 10_000,        # Generous for research use — track to be safe
        "window": "monthly",
        "reset_day": 1,
        "warn_threshold": 0.80,
        "hard_stop": 0.95,
    },
}


def _redis_key(api_name: str, window: str) -> str:
    now = datetime.now(tz=timezone.utc)
    if window == "daily" or window == "per_endpoint_daily":
        period = now.strftime("%Y-%m-%d")
    else:
        period = now.strftime("%Y-%m")
    return f"oracle:quota:{api_name}:{period}"


def _ttl_seconds(window: str) -> int:
    if window in ("daily", "per_endpoint_daily"):
        return 86_400 + 3_600   # 25 hours (safe margin)
    return 32 * 86_400          # 32 days for monthly


class QuotaManager:
    """
    Thread-safe (via Redis) API quota tracker.

    Usage:
        qm = QuotaManager(redis_client)
        if await qm.can_use("twitter_x", cost=1):
            # make request
            await qm.record_usage("twitter_x", cost=1)
    """

    def __init__(self, redis: Any) -> None:
        self._redis = redis

    async def can_use(self, api_name: str, cost: int = 1) -> bool:
        """Returns True if budget allows, False if hard stop reached."""
        if not self._redis:
            return True  # Fail open

        config = QUOTA_CONFIGS.get(api_name)
        if not config:
            return True  # Unknown API — allow

        try:
            key = _redis_key(api_name, config["window"])
            raw = await self._redis.get(key)
            current = int(raw) if raw else 0
            limit = config["limit"]
            hard_stop_at = int(limit * config["hard_stop"])

            if current + cost > hard_stop_at:
                log.warning("quota_hard_stop",
                            api=api_name,
                            current=current,
                            limit=limit,
                            hard_stop_at=hard_stop_at)
                return False

            warn_at = int(limit * config["warn_threshold"])
            if current >= warn_at:
                remaining = hard_stop_at - current
                log.warning("quota_warning",
                            api=api_name,
                            used_pct=round(current / limit * 100, 1),
                            remaining_calls=remaining)

            return True

        except Exception as exc:
            log.warning("quota_check_failed", api=api_name, error=str(exc))
            return True  # Fail open

    async def record_usage(self, api_name: str, cost: int = 1) -> None:
        """Increment usage counter for an API."""
        config = QUOTA_CONFIGS.get(api_name)
        if not config or not self._redis:
            return

        try:
            key = _redis_key(api_name, config["window"])
            ttl = _ttl_seconds(config["window"])
            pipe = self._redis.pipeline()
            await pipe.incrby(key, cost)
            await pipe.expire(key, ttl)
            await pipe.execute()
        except Exception as exc:
            log.warning("quota_record_failed", api=api_name, error=str(exc))

    async def get_status(self) -> list[dict[str, Any]]:
        """Return quota status for all tracked APIs."""
        statuses = []
        for api_name, config in QUOTA_CONFIGS.items():
            try:
                key = _redis_key(api_name, config["window"])
                raw = await self._redis.get(key) if self._redis else None
                current = int(raw) if raw else 0
                limit = config["limit"]
                pct = round(current / max(limit, 1) * 100, 1)
                statuses.append({
                    "api": api_name,
                    "display_name": config["display_name"],
                    "used": current,
                    "limit": limit,
                    "used_pct": pct,
                    "window": config["window"],
                    "status": (
                        "critical" if pct >= config["hard_stop"] * 100
                        else "warning" if pct >= config["warn_threshold"] * 100
                        else "ok"
                    ),
                    "remaining": max(0, int(limit * config["hard_stop"]) - current),
                })
            except Exception as exc:
                statuses.append({
                    "api": api_name,
                    "display_name": config["display_name"],
                    "status": "unknown",
                    "error": str(exc),
                })
        return statuses

    async def reset(self, api_name: str) -> bool:
        """Manually reset quota counter (admin only). Returns True if reset."""
        config = QUOTA_CONFIGS.get(api_name)
        if not config or not self._redis:
            return False
        try:
            key = _redis_key(api_name, config["window"])
            await self._redis.delete(key)
            log.info("quota_manually_reset", api=api_name)
            return True
        except Exception:
            return False
