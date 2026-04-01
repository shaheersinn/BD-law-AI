"""
app/services/analytics_service.py — Phase 12: Weekly usage analytics.

Computes a weekly snapshot from api_request_log and stores it in usage_reports.
Delivers the summary via Slack webhook if SLACK_WEBHOOK_URL is set,
otherwise logs to structlog for manual review.

Called by Celery task agents.compute_usage_report (Agent 033) every Monday 08:00 UTC.
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from typing import Any

import httpx
import structlog
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings

log = structlog.get_logger(__name__)
settings = get_settings()

# p50/p95 percentile approximation bucket size (ms)
_PERCENTILE_SQL = """
SELECT
    endpoint,
    COUNT(*) AS request_count,
    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY response_time_ms) AS p50_ms,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY response_time_ms) AS p95_ms,
    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY response_time_ms) AS p99_ms
FROM api_request_log
WHERE created_at >= :since
GROUP BY endpoint
ORDER BY request_count DESC
LIMIT 20
"""

_TOP_COMPANIES_SQL = """
SELECT
    arl.company_id,
    c.name AS company_name,
    COUNT(*) AS request_count
FROM api_request_log arl
LEFT JOIN companies c ON c.id = arl.company_id
WHERE arl.created_at >= :since
  AND arl.company_id IS NOT NULL
GROUP BY arl.company_id, c.name
ORDER BY request_count DESC
LIMIT 10
"""


async def compute_weekly_usage_report(db: AsyncSession) -> dict[str, Any]:
    """
    Compute this week's usage report from api_request_log.

    Returns a dict matching the usage_reports table schema.
    Stores the result in the usage_reports table.
    """
    now = datetime.now(UTC)
    week_start = (now - timedelta(days=7)).date()
    since = datetime.combine(week_start, datetime.min.time()).replace(tzinfo=UTC)

    # ── Endpoint breakdown (p50/p95/p99 + count) ──────────────────────────────
    endpoint_rows = (await db.execute(text(_PERCENTILE_SQL), {"since": since})).all()
    endpoint_breakdown: list[dict[str, Any]] = []
    all_p50: list[float] = []
    all_p95: list[float] = []

    for row in endpoint_rows:
        endpoint_breakdown.append(
            {
                "endpoint": row.endpoint,
                "count": row.request_count,
                "p50_ms": round(float(row.p50_ms or 0), 1),
                "p95_ms": round(float(row.p95_ms or 0), 1),
                "p99_ms": round(float(row.p99_ms or 0), 1),
            }
        )
        all_p50.append(float(row.p50_ms or 0))
        all_p95.append(float(row.p95_ms or 0))

    overall_p50 = round(sum(all_p50) / len(all_p50), 1) if all_p50 else None
    overall_p95 = round(max(all_p95), 1) if all_p95 else None

    # ── Top companies ──────────────────────────────────────────────────────────
    company_rows = (await db.execute(text(_TOP_COMPANIES_SQL), {"since": since})).all()
    top_companies = [
        {
            "company_id": row.company_id,
            "name": row.company_name or f"company:{row.company_id}",
            "request_count": row.request_count,
        }
        for row in company_rows
    ]

    # ── Top practice areas from signals endpoint logs ─────────────────────────
    # Proxy: count requests to /v1/signals endpoints which include practice area
    pa_rows = (
        await db.execute(
            text(
                """
                SELECT endpoint, COUNT(*) AS cnt
                FROM api_request_log
                WHERE created_at >= :since
                  AND (endpoint LIKE '%signals%' OR endpoint LIKE '%trends%')
                GROUP BY endpoint
                ORDER BY cnt DESC
                LIMIT 10
                """
            ),
            {"since": since},
        )
    ).all()
    top_practice_areas = [
        {"endpoint": row.endpoint, "view_count": row.cnt} for row in pa_rows
    ]

    # ── Redis cache hit rate ───────────────────────────────────────────────────
    cache_hit_rate = await _get_redis_cache_hit_rate()

    report = {
        "week_start": week_start,
        "top_companies": top_companies,
        "top_practice_areas": top_practice_areas,
        "p50_ms": overall_p50,
        "p95_ms": overall_p95,
        "cache_hit_rate": cache_hit_rate,
        "endpoint_breakdown": endpoint_breakdown,
    }

    # ── Persist to usage_reports table ────────────────────────────────────────
    await db.execute(
        text(
            """
            INSERT INTO usage_reports
                (week_start, top_companies, top_practice_areas, p50_ms, p95_ms,
                 cache_hit_rate, endpoint_breakdown)
            VALUES
                (:week_start, :top_companies::jsonb, :top_practice_areas::jsonb,
                 :p50_ms, :p95_ms, :cache_hit_rate, :endpoint_breakdown::jsonb)
            """
        ),
        {
            "week_start": week_start,
            "top_companies": json.dumps(top_companies),
            "top_practice_areas": json.dumps(top_practice_areas),
            "p50_ms": overall_p50,
            "p95_ms": overall_p95,
            "cache_hit_rate": cache_hit_rate,
            "endpoint_breakdown": json.dumps(endpoint_breakdown),
        },
    )
    await db.commit()

    log.info(
        "usage_report.computed",
        week_start=str(week_start),
        total_endpoints=len(endpoint_breakdown),
        top_company=top_companies[0]["name"] if top_companies else None,
        p95_ms=overall_p95,
        cache_hit_rate=cache_hit_rate,
    )

    # ── Deliver report ────────────────────────────────────────────────────────
    await _deliver_report(report)

    return report


async def get_latest_usage_report(db: AsyncSession) -> dict[str, Any] | None:
    """Return the most recently stored usage_reports row."""
    row = (
        await db.execute(
            text(
                """
                SELECT week_start, top_companies, top_practice_areas, p50_ms, p95_ms,
                       cache_hit_rate, endpoint_breakdown, created_at
                FROM usage_reports
                ORDER BY week_start DESC
                LIMIT 1
                """
            )
        )
    ).first()

    if row is None:
        return None

    return {
        "week_start": str(row.week_start),
        "top_companies": row.top_companies or [],
        "top_practice_areas": row.top_practice_areas or [],
        "p50_ms": row.p50_ms,
        "p95_ms": row.p95_ms,
        "cache_hit_rate": row.cache_hit_rate,
        "endpoint_breakdown": row.endpoint_breakdown or [],
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


async def get_perf_report(db: AsyncSession, days: int = 7) -> list[dict[str, Any]]:
    """
    Return p50/p95/p99 response times per endpoint from the last N days.
    Sorted by p95 DESC to surface slowest endpoints first.
    """
    since = datetime.now(UTC) - timedelta(days=days)
    rows = (await db.execute(text(_PERCENTILE_SQL), {"since": since})).all()
    return [
        {
            "endpoint": row.endpoint,
            "count": row.request_count,
            "p50_ms": round(float(row.p50_ms or 0), 1),
            "p95_ms": round(float(row.p95_ms or 0), 1),
            "p99_ms": round(float(row.p99_ms or 0), 1),
        }
        for row in sorted(rows, key=lambda r: float(r.p95_ms or 0), reverse=True)
    ]


async def _get_redis_cache_hit_rate() -> float | None:
    """Compute cache hit rate from Redis INFO stats."""
    try:
        from app.cache.client import cache

        info = await cache._redis.info("stats")
        hits = int(info.get("keyspace_hits", 0))
        misses = int(info.get("keyspace_misses", 0))
        total = hits + misses
        if total == 0:
            return None
        return round(hits / total, 4)
    except Exception:
        log.warning("analytics: failed to read Redis cache hit rate")
        return None


async def _deliver_report(report: dict[str, Any]) -> None:
    """Post summary to Slack if webhook configured, else log to structlog."""
    if not settings.slack_webhook_url:
        log.info(
            "usage_report.summary",
            week_start=str(report.get("week_start")),
            p95_ms=report.get("p95_ms"),
            cache_hit_rate=report.get("cache_hit_rate"),
            top_companies=[c["name"] for c in (report.get("top_companies") or [])[:3]],
        )
        return

    top_co = ", ".join(c["name"] for c in (report.get("top_companies") or [])[:3])
    hit_rate = report.get("cache_hit_rate")
    hit_pct = f"{hit_rate * 100:.1f}%" if hit_rate is not None else "N/A"
    p95 = report.get("p95_ms")

    text_body = (
        f"*ORACLE Weekly Usage Report* — week of {report.get('week_start')}\n"
        f"• Top companies: {top_co or 'none'}\n"
        f"• Overall p95 response time: {p95:.0f}ms\n" if p95 else ""
        f"• Cache hit rate: {hit_pct}\n"
        f"• Endpoints tracked: {len(report.get('endpoint_breakdown') or [])}"
    )

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                settings.slack_webhook_url,
                json={"text": text_body},
            )
            resp.raise_for_status()
        log.info("usage_report.slack_delivered", week_start=str(report.get("week_start")))
    except httpx.HTTPError as exc:
        log.warning("usage_report.slack_failed", error=str(exc))
