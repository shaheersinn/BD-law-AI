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
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_auth, require_partner
from app.auth.service import TokenClaims
from app.cache.client import TTL_AI, TTL_GEO, TTL_LONG, TTL_MEDIUM, cache
from app.database import get_db
from app.middleware.rate_limiter import enforce_rate_limit
from app.models import FootTrafficEvent, JetTrack, PermitFiling, SatelliteSignal
from app.services.anthropic_service import ai
from app.services.audit_log import AuditEventType, extract_request_meta, log_event
from app.services.streaming import sse_headers, stream_ai_response

log = logging.getLogger(__name__)
router = APIRouter(prefix="/geo", tags=["geospatial"])

# Static jurisdiction data — in production this would be DB-driven with nightly updates
GEO_JURISDICTIONS = [
    {"id": "can", "label": "Canada",    "x": 195, "y": 112, "intensity": 91, "practice": "M&A + Regulatory",       "drivers": "OSC enforcement wave, energy transition mandates, Indigenous consultation law"},
    {"id": "usa", "label": "USA",       "x": 188, "y": 172, "intensity": 88, "practice": "Securities + Litigation", "drivers": "DOJ tech enforcement, climate litigation, cross-border M&A clearance"},
    {"id": "eu",  "label": "EU",        "x": 448, "y": 148, "intensity": 79, "practice": "Regulatory + Data",       "drivers": "EU AI Act enforcement, CSRD mandates, antitrust wave"},
    {"id": "uk",  "label": "UK",        "x": 420, "y": 134, "intensity": 72, "practice": "Finance + Sanctions",     "drivers": "Post-Brexit disputes, OFSI sanctions compliance, crypto regulation"},
    {"id": "uae", "label": "UAE",       "x": 552, "y": 214, "intensity": 68, "practice": "Arbitration + M&A",       "drivers": "DIFC arbitration surge, sovereign wealth structuring"},
    {"id": "aus", "label": "Australia", "x": 698, "y": 312, "intensity": 61, "practice": "Mining + Environmental",  "drivers": "Critical minerals law, native title litigation, ESG disclosure"},
    {"id": "sgp", "label": "Singapore", "x": 670, "y": 250, "intensity": 74, "practice": "Dispute + Finance",       "drivers": "Fintech disputes, family office structuring, supply chain arbitration"},
    {"id": "ind", "label": "India",     "x": 610, "y": 222, "intensity": 66, "practice": "Corporate + Arbitration", "drivers": "FDI disputes, infrastructure arbitration, data localisation"},
    {"id": "jpn", "label": "Japan",     "x": 715, "y": 172, "intensity": 63, "practice": "M&A + IP",                "drivers": "Inbound M&A, semiconductor IP disputes, carbon credit structuring"},
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
    request: Request = None,
):
    """AI market intelligence brief for a jurisdiction. Cached 12h."""
    await enforce_rate_limit(request, "ai", str(claims.user_id))

    geo = GEO_INDEX.get(jurisdiction_id)
    if not geo:
        raise HTTPException(status_code=404, detail=f"Jurisdiction '{jurisdiction_id}' not found")

    cache_key = f"geo:v1:brief:{jurisdiction_id}"
    cached = await cache.get(cache_key)
    if cached:
        return cached

    brief = await ai.generate(
        "geo_brief",
        jurisdiction=geo["label"],
        index=geo["intensity"],
        practice=geo["practice"],
        drivers=geo["drivers"],
    )

    data = {"brief": brief, "jurisdiction": geo["label"], "intensity": geo["intensity"]}
    await cache.set(cache_key, data, ttl=TTL_GEO)

    await log_event(
        AuditEventType.ai_generate,
        user_id=claims.user_id,
        detail={"prompt_key": "geo_brief", "jurisdiction": jurisdiction_id},
        **(extract_request_meta(request) if request else {}),
    )
    return data


@router.get("/intensity/{jurisdiction_id}/brief/stream")
async def geo_brief_stream(
    jurisdiction_id: str,
    claims: TokenClaims = Depends(require_auth),
    request: Request = None,
):
    await enforce_rate_limit(request, "ai", str(claims.user_id))
    geo = GEO_INDEX.get(jurisdiction_id)
    if not geo:
        raise HTTPException(status_code=404, detail="Jurisdiction not found")

    return StreamingResponse(
        stream_ai_response(
            "geo_brief",
            jurisdiction=geo["label"], index=geo["intensity"],
            practice=geo["practice"], drivers=geo["drivers"],
        ),
        headers=sse_headers(),
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

    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
    q = (
        select(JetTrack)
        .where(JetTrack.departed_at >= cutoff, JetTrack.confidence >= min_confidence)
        .order_by(JetTrack.confidence.desc())
    )
    if flagged_only:
        q = q.where(JetTrack.is_flagged == True)

    result = await db.execute(q)
    data = [t.to_dict() for t in result.scalars().all()]
    await cache.set(cache_key, data, ttl=TTL_MEDIUM)
    return data


@router.post("/jets/{track_id}/brief")
async def jet_brief(
    track_id: int,
    db: AsyncSession = Depends(get_db),
    claims: TokenClaims = Depends(require_auth),
    request: Request = None,
):
    """AI tactical brief for a jet track. Cached 6h."""
    await enforce_rate_limit(request, "ai", str(claims.user_id))

    cache_key = f"geo:v1:jet_brief:{track_id}"
    cached = await cache.get(cache_key)
    if cached:
        return cached

    result = await db.execute(select(JetTrack).where(JetTrack.id == track_id))
    track = result.scalars().first()
    if not track:
        raise HTTPException(status_code=404, detail="Jet track not found")

    brief = await ai.generate(
        "jet_brief",
        company=track.company,
        tail=track.tail_number,
        executive=track.executive or "Senior Executive",
        origin=track.origin_name or track.origin_icao,
        destination=track.dest_name or track.dest_icao,
        date=track.departed_at.strftime("%b %d · %H:%M UTC"),
        signal=track.signal_text or "Bay Street proximity trip detected",
        mandate=track.predicted_mandate or "M&A Advisory",
        confidence=track.confidence,
        warmth=track.relationship_warmth,
    )

    data = {"brief": brief, "track_id": track_id, "company": track.company}
    await cache.set(cache_key, data, ttl=TTL_AI)

    await log_event(
        AuditEventType.ai_generate, user_id=claims.user_id,
        resource_type="jet_track", resource_id=track_id,
        detail={"prompt_key": "jet_brief", "company": track.company},
        **(extract_request_meta(request) if request else {}),
    )
    return data


@router.get("/jets/{track_id}/brief/stream")
async def jet_brief_stream(
    track_id: int,
    db: AsyncSession = Depends(get_db),
    claims: TokenClaims = Depends(require_auth),
    request: Request = None,
):
    await enforce_rate_limit(request, "ai", str(claims.user_id))
    result = await db.execute(select(JetTrack).where(JetTrack.id == track_id))
    track = result.scalars().first()
    if not track:
        raise HTTPException(status_code=404, detail="Jet track not found")

    return StreamingResponse(
        stream_ai_response(
            "jet_brief",
            company=track.company, tail=track.tail_number,
            executive=track.executive or "Senior Executive",
            origin=track.origin_name or track.origin_icao,
            destination=track.dest_name or track.dest_icao,
            date=track.departed_at.strftime("%b %d · %H:%M UTC"),
            signal=track.signal_text or "Bay Street proximity trip",
            mandate=track.predicted_mandate or "M&A Advisory",
            confidence=track.confidence, warmth=track.relationship_warmth,
        ),
        headers=sse_headers(),
    )


# ── Foot Traffic ────────────────────────────────────────────────────────────────

@router.get("/foot-traffic")
async def list_foot_traffic(
    days_back: int = Query(default=14, ge=1, le=60),
    severity: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    claims: TokenClaims = Depends(require_auth),
):
    cache_key = f"geo:v1:foot:{days_back}:{severity or 'all'}"
    cached = await cache.get(cache_key)
    if cached:
        return cached

    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
    q = select(FootTrafficEvent).where(FootTrafficEvent.occurred_at >= cutoff).order_by(
        FootTrafficEvent.device_count.desc()
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
    db: AsyncSession = Depends(get_db),
    claims: TokenClaims = Depends(require_auth),
    request: Request = None,
):
    await enforce_rate_limit(request, "ai", str(claims.user_id))

    cache_key = f"geo:v1:foot_strategy:{event_id}"
    cached = await cache.get(cache_key)
    if cached:
        return cached

    result = await db.execute(select(FootTrafficEvent).where(FootTrafficEvent.id == event_id))
    event = result.scalars().first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    brief = await ai.generate(
        "foot_traffic_strategy",
        client=event.target_company,
        location=event.location_name,
        devices=event.device_count,
        duration=f"{event.avg_duration_minutes or 90} min avg",
        date=event.occurred_at.strftime("%b %d"),
        threat=event.threat_assessment or "Competitor engagement detected",
        severity=event.severity.upper(),
    )

    data = {"brief": brief, "event_id": event_id, "company": event.target_company}
    await cache.set(cache_key, data, ttl=TTL_AI)

    await log_event(
        AuditEventType.ai_generate, user_id=claims.user_id,
        resource_type="foot_traffic", resource_id=event_id,
        detail={"prompt_key": "foot_traffic_strategy", "company": event.target_company},
        **(extract_request_meta(request) if request else {}),
    )
    return data


@router.get("/foot-traffic/{event_id}/strategy/stream")
async def foot_traffic_stream(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    claims: TokenClaims = Depends(require_auth),
    request: Request = None,
):
    await enforce_rate_limit(request, "ai", str(claims.user_id))
    result = await db.execute(select(FootTrafficEvent).where(FootTrafficEvent.id == event_id))
    event = result.scalars().first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    return StreamingResponse(
        stream_ai_response(
            "foot_traffic_strategy",
            client=event.target_company, location=event.location_name,
            devices=event.device_count, duration=f"{event.avg_duration_minutes or 90} min avg",
            date=event.occurred_at.strftime("%b %d"),
            threat=event.threat_assessment or "Competitor engagement detected",
            severity=event.severity.upper(),
        ),
        headers=sse_headers(),
    )


# ── Satellite Signals ──────────────────────────────────────────────────────────

@router.get("/satellite")
async def list_satellite(
    urgency: Optional[str] = Query(default=None),
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
    db: AsyncSession = Depends(get_db),
    claims: TokenClaims = Depends(require_auth),
    request: Request = None,
):
    await enforce_rate_limit(request, "ai", str(claims.user_id))

    cache_key = f"geo:v1:sat_brief:{signal_id}"
    cached = await cache.get(cache_key)
    if cached:
        return cached

    result = await db.execute(select(SatelliteSignal).where(SatelliteSignal.id == signal_id))
    sig = result.scalars().first()
    if not sig:
        raise HTTPException(status_code=404, detail="Signal not found")

    brief = await ai.generate(
        "satellite_brief",
        company=sig.company, location=sig.location,
        observation=sig.observation, inference=sig.legal_inference,
        signal_type=sig.signal_type, confidence=sig.confidence, urgency=sig.urgency.upper(),
    )

    data = {"brief": brief, "signal_id": signal_id, "company": sig.company}
    await cache.set(cache_key, data, ttl=TTL_AI)

    await log_event(
        AuditEventType.ai_generate, user_id=claims.user_id,
        resource_type="satellite", resource_id=signal_id,
        detail={"prompt_key": "satellite_brief", "company": sig.company},
        **(extract_request_meta(request) if request else {}),
    )
    return data


@router.get("/satellite/{signal_id}/brief/stream")
async def satellite_brief_stream(
    signal_id: int,
    db: AsyncSession = Depends(get_db),
    claims: TokenClaims = Depends(require_auth),
    request: Request = None,
):
    await enforce_rate_limit(request, "ai", str(claims.user_id))
    result = await db.execute(select(SatelliteSignal).where(SatelliteSignal.id == signal_id))
    sig = result.scalars().first()
    if not sig:
        raise HTTPException(status_code=404, detail="Signal not found")

    return StreamingResponse(
        stream_ai_response(
            "satellite_brief",
            company=sig.company, location=sig.location,
            observation=sig.observation, inference=sig.legal_inference,
            signal_type=sig.signal_type, confidence=sig.confidence, urgency=sig.urgency.upper(),
        ),
        headers=sse_headers(),
    )


# ── Permit Radar ───────────────────────────────────────────────────────────────

@router.get("/permits")
async def list_permits(
    days_back: int = Query(default=30, ge=1, le=90),
    urgency: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    claims: TokenClaims = Depends(require_auth),
):
    cache_key = f"geo:v1:permits:{days_back}:{urgency or 'all'}"
    cached = await cache.get(cache_key)
    if cached:
        return cached

    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
    q = select(PermitFiling).where(PermitFiling.filed_at >= cutoff).order_by(PermitFiling.filed_at.desc())
    if urgency:
        q = q.where(PermitFiling.urgency == urgency)

    result = await db.execute(q)
    data = [p.to_dict() for p in result.scalars().all()]
    await cache.set(cache_key, data, ttl=TTL_LONG)
    return data


@router.post("/permits/{permit_id}/brief")
async def permit_brief(
    permit_id: int,
    db: AsyncSession = Depends(get_db),
    claims: TokenClaims = Depends(require_auth),
    request: Request = None,
):
    await enforce_rate_limit(request, "ai", str(claims.user_id))

    cache_key = f"geo:v1:permit_brief:{permit_id}"
    cached = await cache.get(cache_key)
    if cached:
        return cached

    result = await db.execute(select(PermitFiling).where(PermitFiling.id == permit_id))
    permit = result.scalars().first()
    if not permit:
        raise HTTPException(status_code=404, detail="Permit not found")

    rel_line = (
        f"Existing relationship: {permit.lead_partner}"
        if permit.lead_partner
        else "No existing relationship — prospect outreach required"
    )

    brief = await ai.generate(
        "permit_brief",
        company=permit.company, permit=permit.permit_type,
        location=permit.location,
        filed=permit.filed_at.strftime("%b %d, %Y"),
        project_type=permit.project_type or "Major project",
        work=", ".join(permit.legal_work_triggered or []),
        fee=permit.estimated_fee or "TBD",
        urgency=permit.urgency.upper(),
        relationship_line=rel_line,
    )

    data = {"brief": brief, "permit_id": permit_id, "company": permit.company}
    await cache.set(cache_key, data, ttl=TTL_AI)

    await log_event(
        AuditEventType.ai_generate, user_id=claims.user_id,
        resource_type="permit", resource_id=permit_id,
        detail={"prompt_key": "permit_brief", "company": permit.company},
        **(extract_request_meta(request) if request else {}),
    )
    return data


@router.get("/permits/{permit_id}/brief/stream")
async def permit_brief_stream(
    permit_id: int,
    db: AsyncSession = Depends(get_db),
    claims: TokenClaims = Depends(require_auth),
    request: Request = None,
):
    await enforce_rate_limit(request, "ai", str(claims.user_id))
    result = await db.execute(select(PermitFiling).where(PermitFiling.id == permit_id))
    permit = result.scalars().first()
    if not permit:
        raise HTTPException(status_code=404, detail="Permit not found")

    rel_line = (
        f"Existing relationship: {permit.lead_partner}"
        if permit.lead_partner
        else "No existing relationship — prospect outreach required"
    )

    return StreamingResponse(
        stream_ai_response(
            "permit_brief",
            company=permit.company, permit=permit.permit_type,
            location=permit.location,
            filed=permit.filed_at.strftime("%b %d, %Y"),
            project_type=permit.project_type or "Major project",
            work=", ".join(permit.legal_work_triggered or []),
            fee=permit.estimated_fee or "TBD",
            urgency=permit.urgency.upper(),
            relationship_line=rel_line,
        ),
        headers=sse_headers(),
    )
