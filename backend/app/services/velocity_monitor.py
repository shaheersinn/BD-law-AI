"""
app/services/velocity_monitor.py — Signal Velocity Monitor (Agent 021).

Phase 5: Tracks signal rate per company per practice area over rolling windows.
Escalates high-velocity companies to the live feed stream for priority scoring.

Algorithm:
  1. Each incoming signal: push timestamp to Redis sorted set
       Key: oracle:velocity:{company_id}:{practice_area}
       Score: Unix timestamp (float)
  2. 48-hour window count = ZCOUNT(key, now-48h, now)
  3. Baseline expected rate from 30-day count normalised to 48h
       expected_48h = (count_30d / WINDOW_30D_s) * WINDOW_48H_s
  4. velocity_ratio = 48h_count / expected_48h
  5. If velocity_ratio > 2.0 → HIGH PRIORITY (log + future: live scoring trigger)

Score cache:
  Velocity scores stored as Redis hashes for fast dashboard reads.
  Key: oracle:velocity_scores:{company_id}
  Fields: score (float), top_practice_area (str), computed_at (ISO datetime)
  TTL: 24 hours
"""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime
from typing import Any

import redis.asyncio as aioredis
from redis.asyncio import Redis

from app.config import get_settings

log = logging.getLogger(__name__)
settings = get_settings()

# ── Constants ──────────────────────────────────────────────────────────────────
VELOCITY_KEY_PREFIX = "oracle:velocity"
VELOCITY_SCORE_KEY_PREFIX = "oracle:velocity_scores"
WINDOW_48H: float = 48.0 * 3600.0
WINDOW_30D: float = 30.0 * 24.0 * 3600.0
VELOCITY_THRESHOLD = 2.0  # Escalate when 48h rate exceeds 2× baseline
VELOCITY_SCORE_TTL = 86400  # Score cache TTL: 24 hours
SIGNAL_RETENTION_TTL = int(WINDOW_30D) + 3600  # 30 days + 1h buffer


class VelocityMonitor:
    """
    Tracks signal velocity per company per practice area using Redis sorted sets.

    Each sorted set member is a unique timestamp-based string (millisecond precision).
    The sorted set score is the Unix timestamp so ZCOUNT gives O(log N) window queries.
    """

    def __init__(self) -> None:
        self._client: Redis | None = None  # type: ignore[type-arg]

    def _get_client(self) -> Redis:  # type: ignore[type-arg]
        if self._client is None:
            self._client = aioredis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=10,
                socket_timeout=5,
                socket_connect_timeout=5,
            )
        return self._client

    def _signal_key(self, company_id: int, practice_area: str) -> str:
        """Sorted set key for raw signal timestamps."""
        return f"{VELOCITY_KEY_PREFIX}:{company_id}:{practice_area}"

    def _score_key(self, company_id: int) -> str:
        """Hash key for cached velocity score."""
        return f"{VELOCITY_SCORE_KEY_PREFIX}:{company_id}"

    async def record_signal(self, company_id: int, practice_area: str) -> None:
        """
        Record a new signal event for (company_id, practice_area).

        Adds a timestamped entry to the Redis sorted set and trims
        entries older than 30 days to keep memory bounded.

        Args:
            company_id: Integer company primary key.
            practice_area: One of the 34 PRACTICE_AREA_BITS keys.
        """
        try:
            client = self._get_client()
            now = time.time()
            key = self._signal_key(company_id, practice_area)
            # Member must be unique per event; use ms timestamp as string
            member = str(int(now * 1000))

            pipe = client.pipeline()
            pipe.zadd(key, {member: now})
            # Trim entries older than 30 days to keep memory bounded
            pipe.zremrangebyscore(key, 0, now - WINDOW_30D)
            # Extend TTL to keep data for 30 days
            pipe.expire(key, SIGNAL_RETENTION_TTL)
            await pipe.execute()

        except Exception as exc:
            log.warning(
                "velocity_record_failed",
                company_id=company_id,
                practice_area=practice_area,
                error=str(exc),
            )

    async def get_velocity_ratio(self, company_id: int, practice_area: str) -> float:
        """
        Compute velocity ratio for (company_id, practice_area).

        velocity_ratio = 48h_count / expected_48h_count
        where expected_48h_count = (30d_count / WINDOW_30D_s) * WINDOW_48H_s

        Returns 0.0 when:
          - No 30-day baseline (no historical signals)
          - Expected rate < 0.5 events per 48h (too sparse for meaningful ratio)
          - On Redis error
        """
        try:
            client = self._get_client()
            now = time.time()
            key = self._signal_key(company_id, practice_area)

            pipe = client.pipeline()
            pipe.zcount(key, now - WINDOW_48H, "+inf")
            pipe.zcount(key, now - WINDOW_30D, "+inf")
            results = await pipe.execute()

            count_48h: int = int(results[0])
            count_30d: int = int(results[1])

            if count_30d == 0:
                return 0.0

            # Normalise 30-day count to the 48-hour window
            expected_48h = (count_30d / WINDOW_30D) * WINDOW_48H
            if expected_48h < 0.5:
                # Less than 1 signal expected in 48h — baseline too sparse
                return 0.0

            return count_48h / expected_48h

        except Exception as exc:
            log.warning(
                "velocity_ratio_failed",
                company_id=company_id,
                practice_area=practice_area,
                error=str(exc),
            )
            return 0.0

    async def get_velocity_score(self, company_id: int) -> float:
        """
        Return the cached velocity score for a company.

        Returns 0.0 if not yet computed or on error.
        Scores are refreshed by compute_and_cache_scores() every 5 minutes.
        """
        try:
            client = self._get_client()
            value = await client.hget(self._score_key(company_id), "score")
            if value is None:
                return 0.0
            return float(value)
        except Exception as exc:
            log.warning("velocity_score_get_failed", company_id=company_id, error=str(exc))
            return 0.0

    async def compute_and_cache_scores(self, company_ids: list[int]) -> dict[str, Any]:
        """
        Compute and cache velocity scores for a list of companies.

        For each company: computes velocity ratio across all 34 practice areas,
        takes the maximum, and stores it as the company's velocity_score.
        High-velocity companies (ratio > VELOCITY_THRESHOLD) are logged for escalation.

        Args:
            company_ids: List of active company IDs to score.

        Returns:
            Summary dict: companies_scanned, high_velocity_count, escalated (list).
        """
        from app.models.signal import PRACTICE_AREA_BITS

        practice_areas = list(PRACTICE_AREA_BITS.keys())
        results: dict[str, Any] = {
            "companies_scanned": 0,
            "high_velocity_count": 0,
            "escalated": [],
        }

        if not company_ids:
            return results

        try:
            client = self._get_client()
            pipe = client.pipeline()

            for company_id in company_ids:
                max_ratio = 0.0
                max_area = ""

                for area in practice_areas:
                    ratio = await self.get_velocity_ratio(company_id, area)
                    if ratio > max_ratio:
                        max_ratio = ratio
                        max_area = area

                score_key = self._score_key(company_id)
                pipe.hset(
                    score_key,
                    mapping={
                        "score": str(round(max_ratio, 4)),
                        "top_practice_area": max_area,
                        "computed_at": datetime.now(UTC).isoformat(),
                    },
                )
                pipe.expire(score_key, VELOCITY_SCORE_TTL)
                results["companies_scanned"] += 1

                if max_ratio > VELOCITY_THRESHOLD:
                    results["high_velocity_count"] += 1
                    escalation = {
                        "company_id": company_id,
                        "velocity_ratio": round(max_ratio, 4),
                        "top_practice_area": max_area,
                    }
                    results["escalated"].append(escalation)
                    log.info(
                        "velocity_escalation",
                        company_id=company_id,
                        velocity_ratio=round(max_ratio, 4),
                        practice_area=max_area,
                    )

            await pipe.execute()

        except Exception as exc:
            log.error("velocity_score_compute_failed", error=str(exc))
            results["error"] = str(exc)

        return results

    async def run(self) -> dict[str, Any]:
        """
        Entry point for the Celery velocity monitor task (Agent 021).

        Fetches all active company IDs from the database, computes velocity
        scores, and returns a summary for Celery's result backend.
        """
        from sqlalchemy import select

        from app.database import AsyncSessionLocal
        from app.models.company import Company

        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(Company.id).where(Company.is_active.is_(True)))
                company_ids: list[int] = [row[0] for row in result.fetchall()]

            if not company_ids:
                log.info("velocity_monitor_no_active_companies")
                return {"companies_scanned": 0, "high_velocity_count": 0}

            summary = await self.compute_and_cache_scores(company_ids)
            log.info(
                "velocity_monitor_complete",
                companies=summary["companies_scanned"],
                high_velocity=summary["high_velocity_count"],
            )
            return summary

        except Exception as exc:
            log.error("velocity_monitor_failed", error=str(exc))
            return {"error": str(exc), "companies_scanned": 0, "high_velocity_count": 0}

    async def close(self) -> None:
        """Close the Redis connection."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None


# ── Module-level singleton ─────────────────────────────────────────────────────
# Import this in other modules:
#   from app.services.velocity_monitor import velocity_monitor
velocity_monitor = VelocityMonitor()
