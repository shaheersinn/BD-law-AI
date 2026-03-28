"""
app/routes/geo.py — Geospatial intelligence with caching, auth, and streaming.

Routes:
  GET  /api/geo/intensity                       → jurisdiction demand scores (cached 12h)
  POST /api/geo/intensity/{id}/brief            → AI brief (cached 12h, streaming variant)
  GET  /api/geo/jets                            → jet tracks
  POST /api/geo/jets/{id}/brief                 → AI tactical brief (cached 6h)
  GET  /api/geo/jets/{id}/brief/stream          → streaming SSE
  GET  /api/geo/foot-traffic                    → foot traffic events
  POST /api/geo/foot-traffic/{id}/strategy      → AI counter-strategy
  GET  /api/geo/satellite                       → satellite signals
  POST /api/geo/satellite/{id}/brief            → AI exposure brief
  GET  /api/geo/permits                         → permit filings
  POST /api/geo/permits/{id}/brief              → AI outreach brief
"""

import logging
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_auth
from app.auth.service import TokenClaims
from app.cache.client import TTL_GEO, TTL_LONG, TTL_MEDIUM, cache
from app.database import get_db
from app.models import FootTrafficEvent, JetTrack, PermitFiling, SatelliteSignal

log = logging.getLogger(__name__)
router = APIRouter(prefix="/geo", tags=["geospatial"])

# Static jurisdiction data — in production this would be DB-driven with nightly updates
GEO_JURISDICTIONS = [
    {
        "id": "can",
        "label": "Canada",
        "x": 195,
        "y": 112,
        "intensity": 91,
        "practice": "M&A + Regulatory",
        "drivers": "OSC enforcement wave, energy transition mandates, Indigenous consultation law",
    },
    {
        "id": "usa",
        "label": "USA",
        "x": 188,
        "y": 172,
        "intensity": 88,
        "practice": "Securities + Litigation",
        "drivers": "DOJ tech enforcement, climate litigation, cross-border M&A clearance",
    },
    {
        "id": "eu",
        "label": "EU",
        "x": 448,
        "y": 148,
        "intensity": 79,
        "practice": "Regulatory + Data",
        "drivers": "EU AI Act enforcement, CSRD mandates, antitrust wave",
    },
    {
        "id": "uk",
        "label": "UK",
        "x": 420,
        "y": 134,
        "intensity": 72,
        "practice": "Finance + Sanctions",
        "drivers": "Post-Brexit disputes, OFSI sanctions compliance, crypto regulation",
    },
    {
        "id": "uae",
        "label": "UAE",
        "x": 552,
        "y": 214,
        "intensity": 68,
        "practice": "Arbitration + M&A",
        "drivers": "DIFC arbitration surge, sovereign wealth structuring",
    },
    {
        "id": "aus",
        "label": "Australia",
        "x": 698,
        "y": 312,
        "intensity": 61,
        "practice": "Mining + Environmental",
        "drivers": "Critical minerals law, native title litigation, ESG disclosure",
    },
    {
        "id": "sgp",
        "label": "Singapore",
        "x": 670,
        "y": 250,
        "intensity": 74,
        "practice": "Dispute + Finance",
        "drivers": "Fintech disputes, family office structuring, supply chain arbitration",
    },
    {
        "id": "ind",
        "label": "India",
        "x": 610,
        "y": 222,
        "intensity": 66,
        "practice": "Corporate + Arbitration",
        "drivers": "FDI disputes, infrastructure arbitration, data localisation",
    },
    {
        "id": "jpn",
        "label": "Japan",
        "x": 715,
        "y": 172,
        "intensity": 63,
        "practice": "M&A + IP",
        "drivers": "Inbound M&A, semiconductor IP disputes, carbon credit structuring",
    },
]

GEO_INDEX = {g["id"]: g for g in GEO_JURISDICTIONS}


# ── Jurisdiction Heat Map ──────────────────────────────────────────────────────


@router.get("/intensity")
async def geo_intensity(claims: TokenClaims = Depends(require_auth)):
    """Legal demand intensity by jurisdiction. Cached 12 hours."""
    return await cache.get_or_set(
        cache.geo_intensity_key(),
        lambda: GEO_JURISDICTIONS,
        ttl=TTL_GEO,
    )


@router.post("/intensity/{jurisdiction_id}/brief")
async def geo_brief(
    jurisdiction_id: str,
    claims: TokenClaims = Depends(require_auth),
):
    """AI market intelligence brief — removed from production."""
    return JSONResponse(
        status_code=410,
        content={"error": "AI brief generation has been removed from production."},
    )


# ── Jet Tracker ────────────────────────────────────────────────────────────────


@router.get("/jets")
async def list_jet_tracks(
    days_back: int = Query(default=30, ge=1, le=90),
    flagged_only: bool = Query(default=False),
    min_confidence: int = Query(default=0, ge=0, le=100),
    db: AsyncSession = Depends(get_db),
    claims: TokenClaims = Depends(require_auth),
):
    """Corporate jet tracks sorted by confidence."""
    cache_key = f"geo:v1:jets:{days_back}:{flagged_only}:{min_confidence}"
    cached = await cache.get(cache_key)
    if cached:
        return cached

    cutoff = datetime.now(UTC) - timedelta(days=days_back)
    q = (
        select(JetTrack)
        .where(JetTrack.departed_at >= cutoff, JetTrack.confidence >= min_confidence)
        .order_by(JetTrack.confidence.desc())
    )
    if flagged_only:
        q = q.where(JetTrack.is_flagged)

    result = await db.execute(q)
    data = [t.to_dict() for t in result.scalars().all()]
    await cache.set(cache_key, data, ttl=TTL_MEDIUM)
    return data


@router.post("/jets/{track_id}/brief")
async def jet_brief(
    track_id: int,
    claims: TokenClaims = Depends(require_auth),
):
    """AI tactical brief — removed from production."""
    return JSONResponse(
        status_code=410,
        content={"error": "AI brief generation has been removed from production."},
    )


# ── Foot Traffic ────────────────────────────────────────────────────────────────


@router.get("/foot-traffic")
async def list_foot_traffic(
    days_back: int = Query(default=14, ge=1, le=60),
    severity: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    claims: TokenClaims = Depends(require_auth),
):
    cache_key = f"geo:v1:foot:{days_back}:{severity or 'all'}"
    cached = await cache.get(cache_key)
    if cached:
        return cached

    cutoff = datetime.now(UTC) - timedelta(days=days_back)
    q = (
        select(FootTrafficEvent)
        .where(FootTrafficEvent.occurred_at >= cutoff)
        .order_by(FootTrafficEvent.device_count.desc())
    )
    if severity:
        q = q.where(FootTrafficEvent.severity == severity)

    result = await db.execute(q)
    data = [e.to_dict() for e in result.scalars().all()]
    await cache.set(cache_key, data, ttl=TTL_MEDIUM)
    return data


@router.post("/foot-traffic/{event_id}/strategy")
async def foot_traffic_strategy(
    event_id: int,
    claims: TokenClaims = Depends(require_auth),
):
    """AI counter-strategy — removed from production."""
    return JSONResponse(
        status_code=410,
        content={"error": "AI brief generation has been removed from production."},
    )


# ── Satellite Signals ──────────────────────────────────────────────────────────


@router.get("/satellite")
async def list_satellite(
    urgency: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    claims: TokenClaims = Depends(require_auth),
):
    cache_key = f"geo:v1:satellite:{urgency or 'all'}"
    cached = await cache.get(cache_key)
    if cached:
        return cached

    q = select(SatelliteSignal).order_by(SatelliteSignal.confidence.desc())
    if urgency:
        q = q.where(SatelliteSignal.urgency == urgency)

    result = await db.execute(q)
    data = [s.to_dict() for s in result.scalars().all()]
    await cache.set(cache_key, data, ttl=TTL_LONG)
    return data


@router.post("/satellite/{signal_id}/brief")
async def satellite_brief(
    signal_id: int,
    claims: TokenClaims = Depends(require_auth),
):
    """AI exposure brief — removed from production."""
    return JSONResponse(
        status_code=410,
        content={"error": "AI brief generation has been removed from production."},
    )


# ── Permit Radar ───────────────────────────────────────────────────────────────


@router.get("/permits")
async def list_permits(
    days_back: int = Query(default=30, ge=1, le=90),
    urgency: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    claims: TokenClaims = Depends(require_auth),
):
    cache_key = f"geo:v1:permits:{days_back}:{urgency or 'all'}"
    cached = await cache.get(cache_key)
    if cached:
        return cached

    cutoff = datetime.now(UTC) - timedelta(days=days_back)
    q = (
        select(PermitFiling)
        .where(PermitFiling.filed_at >= cutoff)
        .order_by(PermitFiling.filed_at.desc())
    )
    if urgency:
        q = q.where(PermitFiling.urgency == urgency)

    result = await db.execute(q)
    data = [p.to_dict() for p in result.scalars().all()]
    await cache.set(cache_key, data, ttl=TTL_LONG)
    return data


@router.post("/permits/{permit_id}/brief")
async def permit_brief(
    permit_id: int,
    claims: TokenClaims = Depends(require_auth),
):
    """AI outreach brief — removed from production."""
    return JSONResponse(
        status_code=410,
        content={"error": "AI brief generation has been removed from production."},
    )
