"""
app/routes/scrapers.py — Phase 1B Scraper Health Dashboard.

Endpoints:
  GET  /api/v1/scrapers/health            → paginated ScraperHealth list (auth required)
  GET  /api/v1/scrapers/health/{name}     → single scraper health record (auth required)
  GET  /api/v1/scrapers/summary           → aggregate counts, cached 60s (auth required)
  GET  /api/v1/scrapers/registry          → all registered source_ids (auth required)
  GET  /api/v1/scrapers/categories        → per-category health summary (auth required)
  POST /api/v1/scrapers/{source_id}/run   → trigger on-demand (partner role)
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_auth, require_partner
from app.auth.models import User
from app.cache.client import cache
from app.database import get_db
from app.models.scraper_health import ScraperHealth
from app.scrapers.registry import ScraperRegistry

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/scrapers", tags=["scrapers"])


# ── Response Schemas ──────────────────────────────────────────────────────────


class ScraperHealthOut(BaseModel):
    id: int
    scraper_name: str
    scraper_category: str
    status: str
    last_run_at: datetime | None
    last_success_at: datetime | None
    last_error_at: datetime | None
    last_error_message: str | None
    consecutive_failures: int
    total_runs: int
    total_failures: int
    records_last_run: int
    records_total: int
    avg_run_duration_ms: float | None
    p95_run_duration_ms: float | None
    success_rate_7d: float | None
    source_reliability_score: float
    requires_api_key: bool

    model_config = {"from_attributes": True}


class ScraperSummaryOut(BaseModel):
    total: int
    healthy: int
    degraded: int
    failing: int
    disabled: int
    registry_count: int
    last_updated: datetime


class CategorySummaryOut(BaseModel):
    category: str
    total: int
    healthy: int
    degraded: int
    failing: int
    disabled: int


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/health", response_model=list[ScraperHealthOut])
async def list_scraper_health(
    status: str | None = Query(
        None, description="Filter by status (healthy/degraded/failing/disabled)"
    ),
    category: str | None = Query(None, description="Filter by scraper category"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_auth),
) -> list[ScraperHealthOut]:
    """List all scraper health records, filterable by status and category."""
    stmt = select(ScraperHealth)
    if status:
        stmt = stmt.where(ScraperHealth.status == status)
    if category:
        stmt = stmt.where(ScraperHealth.scraper_category == category)
    stmt = (
        stmt.order_by(ScraperHealth.scraper_category, ScraperHealth.scraper_name)
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return [ScraperHealthOut.model_validate(row) for row in rows]


@router.get("/health/{scraper_name}", response_model=ScraperHealthOut)
async def get_scraper_health(
    scraper_name: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_auth),
) -> ScraperHealthOut:
    """Get health record for a single scraper by name."""
    stmt = select(ScraperHealth).where(ScraperHealth.scraper_name == scraper_name)
    result = await db.execute(stmt)
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(
            status_code=404, detail=f"Scraper {scraper_name!r} not found in health table"
        )
    return ScraperHealthOut.model_validate(row)


@router.get("/summary", response_model=ScraperSummaryOut)
async def scraper_summary(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_auth),
) -> ScraperSummaryOut:
    """
    Aggregate scraper health summary.
    Cached in Redis for 60 seconds.
    """
    cache_key = "oracle:scrapers:summary"
    cached: dict[str, Any] | None = await cache.get(cache_key)
    if cached:
        return ScraperSummaryOut(**cached)

    # Count by status
    stmt = select(ScraperHealth.status, func.count(ScraperHealth.id)).group_by(ScraperHealth.status)
    result = await db.execute(stmt)
    counts: dict[str, int] = {row[0]: row[1] for row in result.all()}

    summary = ScraperSummaryOut(
        total=sum(counts.values()),
        healthy=counts.get("healthy", 0),
        degraded=counts.get("degraded", 0),
        failing=counts.get("failing", 0),
        disabled=counts.get("disabled", 0),
        registry_count=ScraperRegistry.count(),
        last_updated=datetime.now(tz=UTC),
    )
    await cache.set(cache_key, summary.model_dump(mode="json"), ttl=60)
    return summary


@router.get("/registry")
async def list_registry(
    _: User = Depends(require_auth),
) -> dict[str, Any]:
    """List all registered scraper source_ids."""
    return {
        "count": ScraperRegistry.count(),
        "source_ids": ScraperRegistry.all_ids(),
    }


@router.get("/categories", response_model=list[CategorySummaryOut])
async def categories_summary(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_auth),
) -> list[CategorySummaryOut]:
    """Per-category health summary."""
    stmt = (
        select(
            ScraperHealth.scraper_category,
            ScraperHealth.status,
            func.count(ScraperHealth.id),
        )
        .group_by(ScraperHealth.scraper_category, ScraperHealth.status)
        .order_by(ScraperHealth.scraper_category)
    )
    result = await db.execute(stmt)
    rows = result.all()

    # Pivot: category → {status: count}
    cat_map: dict[str, dict[str, int]] = {}
    for category, status, count in rows:
        if category not in cat_map:
            cat_map[category] = {}
        cat_map[category][status] = count

    return [
        CategorySummaryOut(
            category=cat,
            total=sum(v for v in counts.values()),
            healthy=counts.get("healthy", 0),
            degraded=counts.get("degraded", 0),
            failing=counts.get("failing", 0),
            disabled=counts.get("disabled", 0),
        )
        for cat, counts in sorted(cat_map.items())
    ]


@router.post("/{source_id}/run", status_code=202)
async def trigger_scraper(
    source_id: str,
    _: User = Depends(require_partner),
) -> dict[str, Any]:
    """
    Trigger a single scraper on-demand.
    Requires partner role or above.
    Returns 202 Accepted with Celery task ID.
    """
    try:
        ScraperRegistry.get(source_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=404, detail=f"Scraper {source_id!r} not found in registry"
        ) from exc

    try:
        from app.tasks.scraper_tasks import run_single_scraper  # noqa: PLC0415

        task = run_single_scraper.delay(source_id)
        log.info("scraper_triggered", source_id=source_id, task_id=task.id)
        return {"task_id": task.id, "source_id": source_id, "status": "queued"}
    except Exception as exc:
        log.error("scraper_trigger_failed", source_id=source_id, error=str(exc))
        raise HTTPException(status_code=503, detail="Failed to queue scraper task") from exc
