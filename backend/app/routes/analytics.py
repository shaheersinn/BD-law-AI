"""
app/routes/analytics.py — Model performance + BD analytics endpoints.

Powers the internal admin performance dashboard:
  GET /api/analytics/model-performance   → PR-AUC, precision, advance days, ROI
  GET /api/analytics/signal-quality      → noise rate by source, best/worst sources
  GET /api/analytics/bd-performance      → win rates, pipeline velocity, coaching data
  GET /api/analytics/revenue-attribution → which alerts led to actual matters
  GET /api/analytics/health              → system health: DB, Redis, Celery, scrapers
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_admin, require_partner
from app.auth.service import TokenClaims
from app.cache.client import TTL_MEDIUM, cache
from app.database import get_db
from app.models import Alert, Client, Trigger
from app.models.bd_activity import BDActivity, ContentPiece, MatterSource

log = logging.getLogger(__name__)
router = APIRouter(prefix="/analytics", tags=["analytics"])


# ── Schemas ────────────────────────────────────────────────────────────────────

class ModelPerformanceOut(BaseModel):
    total_alerts_fired: int
    alerts_labelled: int
    labelling_rate: float
    confirmed_real_mandate: int
    dismissed_as_noise: int
    matters_opened_from_alerts: int
    precision_at_high: Optional[float]
    recall: Optional[float]
    avg_advance_days: Optional[float]
    best_source: Optional[str]
    worst_source: Optional[str]
    revenue_from_alerted_matters: float
    estimated_roi: float


class SignalQualityOut(BaseModel):
    source: str
    total_signals: int
    confirmed: int
    dismissed: int
    precision: float
    avg_urgency: float


class SystemHealthOut(BaseModel):
    database: str
    redis: str
    celery: str
    last_sedar_scrape: Optional[datetime]
    last_edgar_scrape: Optional[datetime]
    last_scoring_run: Optional[datetime]
    total_triggers_24h: int
    total_alerts_24h: int


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.get("/model-performance", response_model=ModelPerformanceOut)
async def model_performance(
    days_back: int = Query(default=90, le=365),
    claims: TokenClaims = Depends(require_partner),
    db: AsyncSession = Depends(get_db),
):
    """
    Model accuracy metrics for the convergence engine.
    Cached for 30 minutes — expensive query.
    """
    cache_key = f"analytics:model_perf:{days_back}"
    cached = await cache.get(cache_key)
    if cached:
        return ModelPerformanceOut(**cached)

    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)

    alerts = (
        await db.execute(select(Alert).where(Alert.fired_at >= cutoff))
    ).scalars().all()

    total = len(alerts)
    labelled = sum(1 for a in alerts if a.confirmed is not None)
    confirmed = sum(1 for a in alerts if a.confirmed == True)
    dismissed = sum(1 for a in alerts if a.dismissed == True)
    matter_opened = sum(1 for a in alerts if a.matter_opened == True)

    labelling_rate = labelled / total if total > 0 else 0.0

    # Precision at HIGH threshold (≥80)
    high_alerts = [a for a in alerts if a.score >= 80 and a.confirmed is not None]
    precision_high = None
    if high_alerts:
        tp = sum(1 for a in high_alerts if a.confirmed == True)
        precision_high = round(tp / len(high_alerts), 3)

    # Recall
    recall = None
    if confirmed > 0:
        # How many confirmed mandates did we alert on vs total labelled
        recall = round(confirmed / labelled, 3) if labelled > 0 else None

    # Average advance days (fired_at to mandate_confirmed_at)
    advance_days = [
        (a.mandate_confirmed_at - a.fired_at).days
        for a in alerts
        if a.mandate_confirmed_at and a.fired_at
    ]
    avg_advance = round(sum(advance_days) / len(advance_days), 1) if advance_days else None

    # Signal quality by source
    source_stats: dict[str, dict] = {}
    triggers = (
        await db.execute(
            select(Trigger)
            .where(and_(Trigger.filed_at >= cutoff, Trigger.confirmed.isnot(None)))
        )
    ).scalars().all()

    for t in triggers:
        src = t.source if isinstance(t.source, str) else t.source.value
        if src not in source_stats:
            source_stats[src] = {"total": 0, "confirmed": 0}
        source_stats[src]["total"] += 1
        if t.confirmed:
            source_stats[src]["confirmed"] += 1

    best = max(source_stats, key=lambda s: source_stats[s]["confirmed"] / max(source_stats[s]["total"], 1), default=None)
    worst = min(source_stats, key=lambda s: source_stats[s]["confirmed"] / max(source_stats[s]["total"], 1), default=None)

    # Revenue from alerted matters
    alerted_client_ids = {a.client_id for a in alerts if a.matter_opened and a.client_id}
    revenue = 0.0
    if alerted_client_ids:
        clients = (
            await db.execute(select(Client).where(Client.id.in_(alerted_client_ids)))
        ).scalars().all()
        revenue = sum(float(c.annual_revenue or 0) for c in clients)

    # Simple ROI: revenue / (Anthropic API cost estimate)
    api_cost_estimate = total * 0.01    # ~$0.01 per API call
    roi = round(revenue / max(api_cost_estimate, 1), 1)

    result = {
        "total_alerts_fired": total,
        "alerts_labelled": labelled,
        "labelling_rate": round(labelling_rate, 3),
        "confirmed_real_mandate": confirmed,
        "dismissed_as_noise": dismissed,
        "matters_opened_from_alerts": matter_opened,
        "precision_at_high": precision_high,
        "recall": recall,
        "avg_advance_days": avg_advance,
        "best_source": best,
        "worst_source": worst,
        "revenue_from_alerted_matters": revenue,
        "estimated_roi": roi,
    }

    await cache.set(cache_key, result, ttl=TTL_MEDIUM)
    return ModelPerformanceOut(**result)


@router.get("/signal-quality", response_model=list[SignalQualityOut])
async def signal_quality(
    days_back: int = Query(default=30, le=180),
    claims: TokenClaims = Depends(require_partner),
    db: AsyncSession = Depends(get_db),
):
    """Per-source signal quality metrics — noise rate, precision, average urgency."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)

    result = await db.execute(
        select(
            Trigger.source,
            func.count(Trigger.id).label("total"),
            func.sum(func.cast(Trigger.confirmed == True, type_=type(func.count()))).label("confirmed"),
            func.sum(func.cast(Trigger.dismissed == True, type_=type(func.count()))).label("dismissed"),
            func.avg(Trigger.urgency).label("avg_urgency"),
        )
        .where(Trigger.filed_at >= cutoff)
        .group_by(Trigger.source)
        .order_by(func.count(Trigger.id).desc())
    )

    rows = result.all()
    out = []
    for row in rows:
        total = row.total or 0
        confirmed = row.confirmed or 0
        dismissed = row.dismissed or 0
        labelled = confirmed + dismissed
        precision = round(confirmed / labelled, 3) if labelled > 0 else 0.0

        src = row.source if isinstance(row.source, str) else row.source.value
        out.append(SignalQualityOut(
            source=src,
            total_signals=total,
            confirmed=confirmed,
            dismissed=dismissed,
            precision=precision,
            avg_urgency=round(float(row.avg_urgency or 0), 1),
        ))

    return out


@router.get("/bd-performance")
async def bd_performance(
    partner_id: Optional[int] = Query(default=None),
    days_back: int = Query(default=90),
    claims: TokenClaims = Depends(require_partner),
    db: AsyncSession = Depends(get_db),
):
    """
    BD activity analytics for coaching dashboard.
    Partners see only their own data unless admin.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)

    # If non-admin, restrict to own partner_id
    effective_partner_id = partner_id
    if not claims.is_admin and claims.partner_id:
        effective_partner_id = claims.partner_id

    q = select(BDActivity).where(BDActivity.occurred_at >= cutoff)
    if effective_partner_id:
        q = q.where(BDActivity.partner_id == effective_partner_id)

    activities = (await db.execute(q)).scalars().all()

    # Activity by type
    by_type: dict[str, int] = {}
    for a in activities:
        by_type[a.activity_type] = by_type.get(a.activity_type, 0) + 1

    # Follow-up velocity
    meetings = [a for a in activities if a.activity_type == "meeting"]
    fast_meetings = [m for m in meetings if m.had_followup_within_48h == True]
    fast_win_rate = None
    if fast_meetings:
        won = sum(1 for m in fast_meetings if m.led_to_matter == True)
        fast_win_rate = round(won / len(fast_meetings) * 100, 1)

    slow_meetings = [m for m in meetings if m.had_followup_within_48h == False]
    slow_win_rate = None
    if slow_meetings:
        won = sum(1 for m in slow_meetings if m.led_to_matter == True)
        slow_win_rate = round(won / len(slow_meetings) * 100, 1)

    # Content published
    content_q = select(ContentPiece)
    if effective_partner_id:
        content_q = content_q.where(ContentPiece.partner_id == effective_partner_id)
    content = (await db.execute(content_q)).scalars().all()
    total_inquiries = sum(c.inquiries_attributed for c in content)

    # Referral source breakdown
    matter_sources = (await db.execute(select(MatterSource))).scalars().all()
    source_breakdown: dict[str, int] = {}
    for ms in matter_sources:
        source_breakdown[ms.source_type] = source_breakdown.get(ms.source_type, 0) + 1

    return {
        "period_days": days_back,
        "total_activities": len(activities),
        "activities_by_type": by_type,
        "meetings": len(meetings),
        "fast_followup_win_rate": fast_win_rate,
        "slow_followup_win_rate": slow_win_rate,
        "followup_speed_advantage": (
            round(fast_win_rate - slow_win_rate, 1)
            if fast_win_rate is not None and slow_win_rate is not None else None
        ),
        "content_pieces": len(content),
        "content_attributed_inquiries": total_inquiries,
        "referral_source_breakdown": source_breakdown,
    }


@router.get("/health", response_model=SystemHealthOut)
async def system_health(
    claims: TokenClaims = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """System health check for admin — DB, Redis, Celery, scraper freshness."""
    from app.database import check_db_connection
    from app.cache.client import cache as redis_client

    # DB
    db_ok = await check_db_connection()

    # Redis
    redis_ok = await redis_client.health_check()

    # Celery — check if workers are alive
    celery_status = "unknown"
    try:
        from app.tasks.celery_app import celery_app
        insp = celery_app.control.inspect(timeout=2)
        active = insp.active()
        celery_status = "healthy" if active else "no_workers"
    except Exception as e:
        celery_status = f"error: {e}"

    # Scraper freshness
    now = datetime.now(timezone.utc)
    cutoff_24h = now - timedelta(hours=24)

    last_sedar = (
        await db.execute(
            select(func.max(Trigger.detected_at))
            .where(Trigger.source == "SEDAR")
        )
    ).scalar()

    last_edgar = (
        await db.execute(
            select(func.max(Trigger.detected_at))
            .where(Trigger.source == "EDGAR")
        )
    ).scalar()

    last_alert = (
        await db.execute(select(func.max(Alert.fired_at)))
    ).scalar()

    triggers_24h = (
        await db.execute(
            select(func.count(Trigger.id))
            .where(Trigger.detected_at >= cutoff_24h)
        )
    ).scalar() or 0

    alerts_24h = (
        await db.execute(
            select(func.count(Alert.id))
            .where(Alert.fired_at >= cutoff_24h)
        )
    ).scalar() or 0

    return SystemHealthOut(
        database="healthy" if db_ok else "unreachable",
        redis="healthy" if redis_ok else "unreachable",
        celery=celery_status,
        last_sedar_scrape=last_sedar,
        last_edgar_scrape=last_edgar,
        last_scoring_run=last_alert,
        total_triggers_24h=triggers_24h,
        total_alerts_24h=alerts_24h,
    )
