"""
app/scrapers/law_blogs/trend_detector.py — Multi-firm trend consensus detector.

When 3+ Bay Street firms publish about the same topic in a 7-day window,
this generates a high-confidence blog_legal_trend signal.

This is NOT a scraper — it's a post-processing step run after all firm
blog scrapers complete. Called by Agent 004 (Blog Monitor).

Trend detection logic:
  1. Pull all blog_practice_alert signals from last 7 days (from PostgreSQL)
  2. Group by practice area
  3. For each area with 3+ Tier 1 firms: generate blog_legal_trend signal
  4. Weight by: Tier 1 count, Tier 2 count, time proximity

Output: list[ScraperResult] with signal_type="blog_legal_trend"
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

log = structlog.get_logger(__name__)

_TIER1_THRESHOLD = 3  # Tier 1 firms to trigger trend
_TIER2_THRESHOLD = 5  # Tier 2 firms alone to trigger trend
_LOOKBACK_DAYS = 7


async def detect_blog_trends(
    db: Any,  # AsyncSession
    mongo_db: Any,  # MongoDB handle
) -> list[dict[str, Any]]:
    """
    Analyse recent blog posts and detect consensus trends.

    Returns list of trend dicts (not ScraperResults — caller converts).
    Called by Celery task `run_blog_trend_detector`.
    """
    from sqlalchemy import and_, select

    from app.models.company import SignalRecord

    cutoff = datetime.now(tz=UTC) - timedelta(days=_LOOKBACK_DAYS)

    try:
        result = await db.execute(
            select(SignalRecord).where(
                and_(
                    SignalRecord.signal_type == "blog_practice_alert",
                    SignalRecord.scraped_at >= cutoff,
                )
            )
        )
        signals = result.scalars().all()
    except Exception as exc:
        log.error("trend_detector_db_error", error=str(exc))
        return []

    # Group by practice area × tier
    area_firms: dict[str, dict[int, set[str]]] = defaultdict(lambda: defaultdict(set))

    for signal in signals:
        import json

        try:
            hints = json.loads(signal.practice_area_hints or "[]")
            value = json.loads(signal.signal_value or "{}")
            tier = value.get("tier", 2)
            firm_id = value.get("firm_id", "")
            for area in hints:
                area_firms[area][tier].add(firm_id)
        except (json.JSONDecodeError, TypeError):
            continue

    # Generate trend signals
    trends = []
    for area, tier_firms in area_firms.items():
        t1_count = len(tier_firms.get(1, set()))
        t2_count = len(tier_firms.get(2, set()))
        if t1_count >= _TIER1_THRESHOLD or t2_count >= _TIER2_THRESHOLD:
            confidence = min(0.95, 0.6 + (t1_count * 0.1) + (t2_count * 0.05))
            trends.append(
                {
                    "practice_area": area,
                    "tier1_firm_count": t1_count,
                    "tier2_firm_count": t2_count,
                    "all_firms": list(tier_firms.get(1, set()) | tier_firms.get(2, set())),
                    "confidence": confidence,
                    "detected_at": datetime.now(tz=UTC).isoformat(),
                    "lookback_days": _LOOKBACK_DAYS,
                }
            )

    log.info(
        "trend_detector_complete",
        trends_found=len(trends),
        areas=[t["practice_area"] for t in trends],
    )

    return trends
