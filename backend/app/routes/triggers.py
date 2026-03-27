"""
app/routes/triggers.py — Live trigger feed with caching, auth, and streaming briefs.

Routes:
  GET  /api/triggers/live              → paginated trigger feed, cached 5 min
  GET  /api/triggers/{id}              → single trigger detail
  POST /api/triggers/{id}/label        → partner feedback (confirmed/dismissed/matter_opened)
  POST /api/triggers/{id}/brief        → AI brief, cached 6h
  GET  /api/triggers/{id}/brief/stream → streaming SSE brief
  GET  /api/triggers/stats             → count by source + urgency band
"""

import logging
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_auth, require_write
from app.auth.service import TokenClaims
from app.cache.client import TTL_AI, TTL_SHORT, cache
from app.database import get_db
from app.middleware.rate_limiter import enforce_rate_limit
from app.models import Trigger
from app.services.audit_log import AuditEventType, extract_request_meta, log_event

log = logging.getLogger(__name__)
router = APIRouter(prefix="/triggers", tags=["triggers"])


# ── Schemas ────────────────────────────────────────────────────────────────────


class TriggerOut(BaseModel):
    id: int
    source: str
    trigger_type: str
    company_name: str
    client_id: int | None
    title: str
    description: str | None
    url: str | None
    urgency: int
    practice_area: str | None
    practice_confidence: int
    filed_at: datetime
    detected_at: datetime
    confirmed: bool | None
    dismissed: bool | None
    actioned: bool
    model_config = {"from_attributes": True}


class LabelRequest(BaseModel):
    outcome: str  # "confirmed" | "dismissed" | "matter_opened"
    notes: str | None = None


class TriggerStats(BaseModel):
    total_24h: int
    total_72h: int
    by_source: dict[str, int]
    by_urgency_band: dict[str, int]
    unlabelled_high_urgency: int


# ── Routes ─────────────────────────────────────────────────────────────────────


@router.get("/live", response_model=list[TriggerOut])
async def live_triggers(
    source: str | None = Query(
        default=None, description="Filter by source: SEDAR|EDGAR|CANLII|JOBS|OSC"
    ),
    min_urgency: int = Query(default=50, ge=0, le=100),
    hours_back: int = Query(default=72, ge=1, le=168),
    unactioned_only: bool = Query(default=False),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    claims: TokenClaims = Depends(require_auth),
):
    """
    Live trigger feed. Cached per unique query combo for 5 minutes.
    High urgency (≥80) triggers are never cached — always fresh.
    """
    # Only cache standard queries, not custom filters
    use_cache = (
        source is None
        and min_urgency == 50
        and hours_back == 72
        and not unactioned_only
        and skip == 0
    )
    cache_key = cache.trigger_feed_key(source or "ALL", min_urgency, hours_back)

    if use_cache:
        cached = await cache.get(cache_key)
        if cached:
            return cached

    cutoff = datetime.now(UTC) - timedelta(hours=hours_back)
    q = (
        select(Trigger)
        .where(Trigger.urgency >= min_urgency, Trigger.filed_at >= cutoff)
        .order_by(Trigger.filed_at.desc())
        .offset(skip)
        .limit(limit)
    )
    if source:
        q = q.where(Trigger.source == source)
    if unactioned_only:
        q = q.where(not Trigger.actioned)

    result = await db.execute(q)
    triggers = result.scalars().all()

    data = [
        {
            **t.to_dict(),
            "source": t.source if isinstance(t.source, str) else t.source.value,
        }
        for t in triggers
    ]

    if use_cache and min_urgency < 80:
        await cache.set(cache_key, data, ttl=TTL_SHORT)

    return data


@router.get("/stats", response_model=TriggerStats)
async def trigger_stats(
    db: AsyncSession = Depends(get_db),
    claims: TokenClaims = Depends(require_auth),
):
    """Aggregated signal statistics. Cached 5 minutes."""
    cache_key = "triggers:v1:stats"
    cached = await cache.get(cache_key)
    if cached:
        return TriggerStats(**cached)

    now = datetime.now(UTC)

    # Counts by time window
    total_24h = (
        await db.execute(
            select(func.count(Trigger.id)).where(Trigger.detected_at >= now - timedelta(hours=24))
        )
    ).scalar() or 0

    total_72h = (
        await db.execute(
            select(func.count(Trigger.id)).where(Trigger.detected_at >= now - timedelta(hours=72))
        )
    ).scalar() or 0

    # By source
    source_rows = await db.execute(
        select(Trigger.source, func.count(Trigger.id))
        .where(Trigger.detected_at >= now - timedelta(hours=72))
        .group_by(Trigger.source)
    )
    by_source = {(s if isinstance(s, str) else s.value): c for s, c in source_rows.all()}

    # By urgency band
    all_recent = (
        (
            await db.execute(
                select(Trigger.urgency).where(Trigger.detected_at >= now - timedelta(hours=72))
            )
        )
        .scalars()
        .all()
    )

    bands = {"CRITICAL (95-100)": 0, "HIGH (80-94)": 0, "MODERATE (65-79)": 0, "WATCH (50-64)": 0}
    for u in all_recent:
        if u >= 95:
            bands["CRITICAL (95-100)"] += 1
        elif u >= 80:
            bands["HIGH (80-94)"] += 1
        elif u >= 65:
            bands["MODERATE (65-79)"] += 1
        elif u >= 50:
            bands["WATCH (50-64)"] += 1

    # Unactioned high-urgency
    unlabelled = (
        await db.execute(
            select(func.count(Trigger.id)).where(
                Trigger.urgency >= 80,
                not Trigger.actioned,
                Trigger.detected_at >= now - timedelta(hours=72),
            )
        )
    ).scalar() or 0

    result = {
        "total_24h": total_24h,
        "total_72h": total_72h,
        "by_source": by_source,
        "by_urgency_band": bands,
        "unlabelled_high_urgency": unlabelled,
    }
    await cache.set(cache_key, result, ttl=TTL_SHORT)
    return TriggerStats(**result)


@router.get("/{trigger_id}", response_model=TriggerOut)
async def get_trigger(
    trigger_id: int,
    db: AsyncSession = Depends(get_db),
    claims: TokenClaims = Depends(require_auth),
):
    result = await db.execute(select(Trigger).where(Trigger.id == trigger_id))
    t = result.scalars().first()
    if not t:
        raise HTTPException(status_code=404, detail="Trigger not found")
    return {**t.to_dict(), "source": t.source if isinstance(t.source, str) else t.source.value}


@router.post("/{trigger_id}/label", status_code=200)
async def label_trigger(
    trigger_id: int,
    req: LabelRequest,
    db: AsyncSession = Depends(get_db),
    claims: TokenClaims = Depends(require_write),
    request: Request = None,
):
    """
    Partner feedback loop — the single most valuable data operation.
    Each label becomes a training example for the next model retrain.
    """
    valid_outcomes = {"confirmed", "dismissed", "matter_opened"}
    if req.outcome not in valid_outcomes:
        raise HTTPException(status_code=400, detail=f"outcome must be one of: {valid_outcomes}")

    result = await db.execute(select(Trigger).where(Trigger.id == trigger_id))
    t = result.scalars().first()
    if not t:
        raise HTTPException(status_code=404, detail="Trigger not found")

    if req.outcome == "confirmed":
        t.confirmed = True
    elif req.outcome == "dismissed":
        t.dismissed = True
    elif req.outcome == "matter_opened":
        t.matter_opened = True
        t.confirmed = True  # matter opened implies confirmed

    t.actioned = True
    t.actioned_by = claims.email

    await db.commit()

    # Invalidate trigger feed cache so next load reflects the label
    await cache.invalidate_pattern("triggers:v1:live:*")
    await cache.delete("triggers:v1:stats")

    await log_event(
        AuditEventType.trigger_label,
        user_id=claims.user_id,
        resource_type="trigger",
        resource_id=trigger_id,
        detail={
            "outcome": req.outcome,
            "company": t.company_name,
            "source": t.source if isinstance(t.source, str) else t.source.value,
            "urgency": t.urgency,
            "notes": req.notes,
        },
        **(extract_request_meta(request) if request else {}),
    )

    return {
        "status": "labelled",
        "trigger_id": trigger_id,
        "outcome": req.outcome,
        "message": "Label recorded. This data will improve the model on next retrain.",
    }


@router.post("/{trigger_id}/brief")
async def trigger_brief(
    trigger_id: int,
    db: AsyncSession = Depends(get_db),
    claims: TokenClaims = Depends(require_auth),
    request: Request = None,
):
    return JSONResponse(
        status_code=410,
        content={
            "error": "AI brief generation has been removed from production.",
            "trigger_id": trigger_id,
            "message": "Use the scoring API at /api/v1/scores/{company_id} for ML-based predictions.",
        },
    )


@router.get("/{trigger_id}/brief/stream")
async def trigger_brief_stream(
    trigger_id: int,
    claims: TokenClaims = Depends(require_auth),
):
    """Streaming AI brief — removed from production."""
    return JSONResponse(
        status_code=410,
        content={"error": "AI streaming has been removed from production."},
    )
