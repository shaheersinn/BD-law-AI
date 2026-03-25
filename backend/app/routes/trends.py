"""
app/routes/trends.py — Phase 7 practice area trend analytics.

Endpoints:
    GET /api/v1/trends/practice_areas   Signal volume per practice area (7/30/90 days)
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_auth
from app.auth.models import User
from app.cache.client import cache
from app.database import get_db

log = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/trends", tags=["trends"])

_TRENDS_CACHE_KEY = "trends:practice_areas:v1"
_TRENDS_TTL = 3_600  # 1 hour


@router.get(
    "/practice_areas",
    summary="Signal volume per practice area over last 7/30/90 days",
)
async def practice_area_trends(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_auth),
) -> list[dict[str, Any]]:
    """
    Aggregate signal counts per practice_area_hints value over 7, 30, and 90 day windows.
    Used by the dashboard trend charts.
    Cached 1 hour.
    """
    cached = await cache.get(_TRENDS_CACHE_KEY)
    if cached is not None:
        return cached  # type: ignore[return-value]

    try:
        result = await db.execute(
            text("""
                SELECT
                    COALESCE(practice_area_hints, 'unknown')          AS practice_area,
                    COUNT(*) FILTER (WHERE scraped_at >= NOW() - INTERVAL '7 days')   AS count_7d,
                    COUNT(*) FILTER (WHERE scraped_at >= NOW() - INTERVAL '30 days')  AS count_30d,
                    COUNT(*) FILTER (WHERE scraped_at >= NOW() - INTERVAL '90 days')  AS count_90d
                FROM signal_records
                WHERE scraped_at >= NOW() - INTERVAL '90 days'
                GROUP BY practice_area_hints
                ORDER BY count_30d DESC
            """)
        )
        rows = result.mappings().all()
    except Exception:
        log.exception("trends: DB error fetching practice area trends")
        return []

    data = [
        {
            "practice_area": row["practice_area"],
            "count_7d": int(row["count_7d"] or 0),
            "count_30d": int(row["count_30d"] or 0),
            "count_90d": int(row["count_90d"] or 0),
        }
        for row in rows
    ]

    await cache.set(_TRENDS_CACHE_KEY, data, ttl=_TRENDS_TTL)
    return data
