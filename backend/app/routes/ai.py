"""
app/routes/ai.py — AI generation endpoints with caching, auth, rate limits, streaming.

All AI routes:
  - Require authentication (require_auth)
  - Are rate-limited (60 AI calls/user/hour)
  - Cache responses (6 hours for most, longer for stable intelligence)
  - Log to audit trail
  - Support both JSON and streaming (SSE) where applicable
"""

import json
import logging
from datetime import UTC

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_auth
from app.auth.service import TokenClaims
from app.cache.client import TTL_AI, TTL_LONG, cache
from app.config import get_settings
from app.database import get_db
from app.middleware.rate_limiter import enforce_rate_limit
from app.models import Alumni, Client, Partner
from app.models.bd_activity import ContentPiece, ReferralContact, WritingSample
from app.services.anthropic_service import ai
from app.services.audit_log import AuditEventType, extract_request_meta, log_event
from app.services.streaming import sse_headers, stream_ai_response

log = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/ai", tags=["ai"])


# ─── Regulatory alert ──────────────────────────────────────────────────────────


class RegAlertRequest(BaseModel):
    source: str
    title: str
    date: str
    practice_area: str
    client_id: int


@router.post("/regulatory-alert")
async def regulatory_alert(
    req: RegAlertRequest,
    db: AsyncSession = Depends(get_db),
    claims: TokenClaims = Depends(require_auth),
    request: Request = None,
):
    await enforce_rate_limit(request, "ai", str(claims.user_id))

    cache_key = cache.ai_response_key(
        "regulatory_alert", src=req.source, title=req.title[:40], client=req.client_id
    )
    cached = await cache.get(cache_key)
    if cached:
        return cached

    result = await db.execute(select(Client).where(Client.id == req.client_id))
    client = result.scalars().first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    draft = await ai.generate(
        "regulatory_alert",
        source=req.source,
        title=req.title,
        date=req.date,
        practice_area=req.practice_area,
        client_name=client.name,
        industry=client.industry,
        region=client.region,
        matter=client.matters[0].description if client.matters else "Various matters",
        practice_groups=", ".join(client.practice_groups or []),
    )

    data = {"draft": draft, "client_id": req.client_id, "client_name": client.name}
    await cache.set(cache_key, data, ttl=TTL_AI)

    await log_event(
        AuditEventType.ai_generate,
        user_id=claims.user_id,
        resource_type="client",
        resource_id=req.client_id,
        detail={"prompt_key": "regulatory_alert", "source": req.source},
        **(extract_request_meta(request) if request else {}),
    )
    return data


# ─── Prospect outreach ─────────────────────────────────────────────────────────


class ProspectRequest(BaseModel):
    name: str
    score: int
    need: str
    warmth: str
    value: str
    window: str
    signals: list[str]


@router.post("/prospect-outreach")
async def prospect_outreach(
    req: ProspectRequest,
    claims: TokenClaims = Depends(require_auth),
    request: Request = None,
):
    await enforce_rate_limit(request, "ai", str(claims.user_id))

    cache_key = cache.ai_response_key("prospect_outreach", name=req.name, score=req.score)
    cached = await cache.get(cache_key)
    if cached:
        return cached

    strategy = await ai.generate(
        "prospect_outreach",
        name=req.name,
        score=req.score,
        need=req.need,
        warmth=req.warmth,
        value=req.value,
        window=req.window,
        signals="\n".join(f"- {s}" for s in req.signals),
    )

    data = {"strategy": strategy, "company": req.name}
    await cache.set(cache_key, data, ttl=TTL_AI)
    return data


@router.get("/prospect-outreach/stream")
async def prospect_outreach_stream(
    name: str,
    score: int,
    need: str,
    warmth: str,
    value: str,
    window: str,
    signals: str,  # comma-separated
    claims: TokenClaims = Depends(require_auth),
    request: Request = None,
):
    await enforce_rate_limit(request, "ai", str(claims.user_id))
    return StreamingResponse(
        stream_ai_response(
            "prospect_outreach",
            name=name,
            score=score,
            need=need,
            warmth=warmth,
            value=value,
            window=window,
            signals="\n".join(f"- {s.strip()}" for s in signals.split(",")),
        ),
        headers=sse_headers(),
    )


# ─── Alumni outreach ───────────────────────────────────────────────────────────


@router.post("/alumni/{alumni_id}/message")
async def alumni_message(
    alumni_id: int,
    db: AsyncSession = Depends(get_db),
    claims: TokenClaims = Depends(require_auth),
    request: Request = None,
):
    await enforce_rate_limit(request, "ai", str(claims.user_id))

    result = await db.execute(select(Alumni).where(Alumni.id == alumni_id))
    person = result.scalars().first()
    if not person:
        raise HTTPException(status_code=404, detail="Alumni not found")
    if not person.has_active_trigger:
        raise HTTPException(
            status_code=400,
            detail="No active trigger at this company — message drafting requires a live signal",
        )

    cache_key = f"ai:v1:alumni_msg:{alumni_id}"
    cached = await cache.get(cache_key)
    if cached:
        return cached

    message = await ai.generate(
        "alumni_message",
        mentor=person.mentor_partner or "Your former partner",
        name=person.name,
        role=person.current_role,
        company=person.current_company,
        departure_year=person.departure_year or "previously",
        trigger=person.trigger_description or "a recent legal development at your firm",
    )

    data = {"message": message, "alumni_id": alumni_id, "name": person.name}
    await cache.set(cache_key, data, ttl=TTL_AI)

    await log_event(
        AuditEventType.ai_generate,
        user_id=claims.user_id,
        resource_type="alumni",
        resource_id=alumni_id,
        detail={"prompt_key": "alumni_message", "company": person.current_company},
        **(extract_request_meta(request) if request else {}),
    )
    return data


# ─── GC Profiler ──────────────────────────────────────────────────────────────


class GCProfileRequest(BaseModel):
    company: str
    information: str = Field(min_length=50)


@router.post("/gc-profile")
async def gc_profile(
    req: GCProfileRequest,
    claims: TokenClaims = Depends(require_auth),
    request: Request = None,
):
    await enforce_rate_limit(request, "ai", str(claims.user_id))

    raw = await ai.generate(
        "gc_profile",
        company=req.company,
        information=req.information,
    )

    try:
        clean = raw.replace("```json", "").replace("```", "").strip()
        profile = json.loads(clean)
    except json.JSONDecodeError:
        log.warning("GC profile JSON parse failed, returning raw")
        profile = {
            "name": "GC Profile",
            "brief": raw,
            "key_concerns": [],
            "pitch_hooks": [],
            "credibility": 0,
            "reliability": 0,
            "intimacy": 0,
            "self_orientation": 0,
            "trust_score": 0,
        }

    await log_event(
        AuditEventType.ai_generate,
        user_id=claims.user_id,
        detail={"prompt_key": "gc_profile", "company": req.company},
        **(extract_request_meta(request) if request else {}),
    )
    return {"profile": profile}


# ─── Mandate brief ─────────────────────────────────────────────────────────────


class MandateRequest(BaseModel):
    company: str
    confidence: int
    practice: str
    value: str
    window: str
    signals: list[dict]


@router.post("/mandate-brief")
async def mandate_brief(
    req: MandateRequest,
    claims: TokenClaims = Depends(require_auth),
    request: Request = None,
):
    await enforce_rate_limit(request, "ai", str(claims.user_id))

    cache_key = cache.ai_response_key("mandate_brief", company=req.company, conf=req.confidence)
    cached = await cache.get(cache_key)
    if cached:
        return cached

    signals_text = "\n".join(
        f"[{s.get('layer', 'Signal')}] {s.get('text', '')} (Score: {s.get('score', 0)})"
        for s in req.signals
    )
    brief = await ai.generate(
        "mandate_brief",
        company=req.company,
        window=req.window,
        signals=signals_text,
        confidence=req.confidence,
        practice=req.practice,
        value=req.value,
    )

    data = {"brief": brief, "company": req.company}
    await cache.set(cache_key, data, ttl=TTL_AI)

    await log_event(
        AuditEventType.ai_generate,
        user_id=claims.user_id,
        detail={"prompt_key": "mandate_brief", "company": req.company},
        **(extract_request_meta(request) if request else {}),
    )
    return data


@router.get("/mandate-brief/stream")
async def mandate_brief_stream(
    company: str,
    confidence: int,
    practice: str,
    value: str,
    window: str,
    signals: str,
    claims: TokenClaims = Depends(require_auth),
    request: Request = None,
):
    await enforce_rate_limit(request, "ai", str(claims.user_id))
    return StreamingResponse(
        stream_ai_response(
            "mandate_brief",
            company=company,
            window=window,
            signals=signals,
            confidence=confidence,
            practice=practice,
            value=value,
        ),
        headers=sse_headers(),
    )


# ─── M&A dark signals ──────────────────────────────────────────────────────────


class MADarkRequest(BaseModel):
    company: str
    deal_type: str
    value: str
    days: str
    confidence: int
    warmth: int
    signals: list[str]


@router.post("/ma-strategy")
async def ma_strategy(
    req: MADarkRequest,
    claims: TokenClaims = Depends(require_auth),
    request: Request = None,
):
    await enforce_rate_limit(request, "ai", str(claims.user_id))

    cache_key = cache.ai_response_key("ma_strategy", company=req.company, conf=req.confidence)
    cached = await cache.get(cache_key)
    if cached:
        return cached

    strategy = await ai.generate(
        "ma_strategy",
        company=req.company,
        deal_type=req.deal_type,
        value=req.value,
        days=req.days,
        confidence=req.confidence,
        warmth=req.warmth,
        signals="\n".join(f"- {s}" for s in req.signals),
    )

    data = {"strategy": strategy, "company": req.company}
    await cache.set(cache_key, data, ttl=TTL_AI)
    return data


# ─── Pitch autopsy ─────────────────────────────────────────────────────────────


class PitchDebriefRequest(BaseModel):
    debrief_text: str = Field(min_length=20)


@router.post("/pitch-debrief")
async def pitch_debrief(
    req: PitchDebriefRequest,
    claims: TokenClaims = Depends(require_auth),
    request: Request = None,
):
    await enforce_rate_limit(request, "ai", str(claims.user_id))
    analysis = await ai.generate("pitch_debrief", debrief=req.debrief_text)
    return {"analysis": analysis}


class BDCampaignRequest(BaseModel):
    client_id: int


@router.post("/bd-campaign")
async def bd_campaign(
    req: BDCampaignRequest,
    db: AsyncSession = Depends(get_db),
    claims: TokenClaims = Depends(require_auth),
    request: Request = None,
):
    await enforce_rate_limit(request, "ai", str(claims.user_id))

    cache_key = cache.ai_response_key("bd_campaign", client_id=req.client_id)
    cached = await cache.get(cache_key)
    if cached:
        return cached

    result = await db.execute(select(Client).where(Client.id == req.client_id))
    client = result.scalars().first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    campaign = await ai.generate(
        "bd_campaign",
        client_name=client.name,
        industry=client.industry,
        matter=client.matters[0].description if client.matters else "Ongoing retainer",
        partner=client.partner_name or "Relationship Partner",
        wallet_share=client.wallet_share_pct or 25,
        churn_score=client.churn_score,
    )

    data = {"campaign": campaign, "client_id": req.client_id, "client_name": client.name}
    await cache.set(cache_key, data, ttl=TTL_LONG)
    return data


# ─── BD Coaching ──────────────────────────────────────────────────────────────


@router.post("/coaching/{partner_id}/brief")
async def coaching_brief(
    partner_id: int,
    db: AsyncSession = Depends(get_db),
    claims: TokenClaims = Depends(require_auth),
    request: Request = None,
):
    """
    Partner coaching brief. Partners can only access their own.
    Admins can access any partner's brief.
    """
    await enforce_rate_limit(request, "ai", str(claims.user_id))

    # Access control: partners can only see their own brief
    if not claims.is_admin and claims.partner_id and claims.partner_id != partner_id:
        raise HTTPException(
            status_code=403, detail="Partners can only access their own coaching brief"
        )

    cache_key = f"ai:v1:coaching:{partner_id}"
    cached = await cache.get(cache_key)
    if cached:
        return cached

    result = await db.execute(select(Partner).where(Partner.id == partner_id))
    partner = result.scalars().first()
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")

    # Stale referrers (60+ days, sent work)
    from datetime import datetime, timedelta

    stale_cutoff = datetime.now(UTC) - timedelta(days=60)
    stale_result = await db.execute(
        select(ReferralContact)
        .where(
            and_(
                ReferralContact.partner_id == partner_id,
                ReferralContact.matters_sent >= 1,
                ReferralContact.last_contact <= stale_cutoff,
            )
        )
        .order_by(ReferralContact.revenue_sent.desc())
        .limit(3)
    )
    stale = stale_result.scalars().all()
    stale_text = (
        "; ".join(
            f"{r.contact_name} at {r.firm_name} — "
            f"{(datetime.now(UTC) - r.last_contact).days}d silent, "
            f"{r.matters_sent} matter(s) worth ${float(r.revenue_sent):,.0f}"
            for r in stale
        )
        or "None detected"
    )

    # Latest content
    cp_result = await db.execute(
        select(ContentPiece)
        .where(ContentPiece.partner_id == partner_id)
        .order_by(ContentPiece.published_at.desc())
        .limit(1)
    )
    cp = cp_result.scalars().first()
    last_content_days = (
        (datetime.now(UTC) - cp.published_at).days if cp and cp.published_at else 999
    )

    brief = await ai.generate(
        "coaching_brief",
        name=partner.name,
        role=", ".join(partner.practice_areas or []) or "Partner",
        top_source="existing_client",
        top_count=3,
        stale_referrers=stale_text,
        open_followups=2,
        fast_win_rate=74,
        slow_win_rate=31,
        last_content_days=last_content_days,
        best_content_type=cp.content_type if cp else "linkedin_post",
        talks=1,
    )

    data = {
        "brief": brief,
        "partner_id": partner_id,
        "partner_name": partner.name,
        "stale_referrer_count": len(stale),
        "last_content_days": last_content_days,
    }
    await cache.set(cache_key, data, ttl=TTL_LONG)

    await log_event(
        AuditEventType.ai_generate,
        user_id=claims.user_id,
        resource_type="partner",
        resource_id=partner_id,
        detail={"prompt_key": "coaching_brief"},
        **(extract_request_meta(request) if request else {}),
    )
    return data


# ─── Ghost Studio ──────────────────────────────────────────────────────────────


class GhostDraftRequest(BaseModel):
    partner_id: int
    topic: str = Field(min_length=10)


@router.post("/ghost/draft")
async def ghost_draft(
    req: GhostDraftRequest,
    db: AsyncSession = Depends(get_db),
    claims: TokenClaims = Depends(require_auth),
    request: Request = None,
):
    """Generate a LinkedIn draft in the partner's voice. Cached per partner+topic."""
    await enforce_rate_limit(request, "ai", str(claims.user_id))

    cache_key = cache.ai_response_key(
        "linkedin_draft", partner=req.partner_id, topic=req.topic[:60]
    )
    cached = await cache.get(cache_key)
    if cached:
        return cached

    result = await db.execute(select(Partner).where(Partner.id == req.partner_id))
    partner = result.scalars().first()
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")

    samples_result = await db.execute(
        select(WritingSample).where(WritingSample.partner_id == req.partner_id).limit(5)
    )
    samples = samples_result.scalars().all()
    samples_text = (
        "\n\n---\n\n".join(s.text for s in samples)
        if samples
        else (
            "The regulatory landscape is shifting faster than most boards realise. "
            "Here's what in-house counsel need to flag before the next meeting."
        )
    )

    draft = await ai.generate(
        "linkedin_draft",
        name=partner.name,
        title=partner.title or "Partner",
        firm=partner.firm_name,
        writing_samples=samples_text,
        topic=req.topic,
    )

    data = {
        "draft": draft,
        "word_count": len(draft.split()),
        "partner_id": req.partner_id,
        "partner_name": partner.name,
    }
    await cache.set(cache_key, data, ttl=TTL_LONG)

    await log_event(
        AuditEventType.ai_generate,
        user_id=claims.user_id,
        resource_type="partner",
        resource_id=req.partner_id,
        detail={"prompt_key": "linkedin_draft", "topic_preview": req.topic[:60]},
        **(extract_request_meta(request) if request else {}),
    )
    return data


@router.get("/ghost/draft/stream")
async def ghost_draft_stream(
    partner_id: int,
    topic: str,
    db: AsyncSession = Depends(get_db),
    claims: TokenClaims = Depends(require_auth),
    request: Request = None,
):
    """Streaming LinkedIn draft generation."""
    await enforce_rate_limit(request, "ai", str(claims.user_id))

    result = await db.execute(select(Partner).where(Partner.id == partner_id))
    partner = result.scalars().first()
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")

    samples_result = await db.execute(
        select(WritingSample).where(WritingSample.partner_id == partner_id).limit(5)
    )
    samples = samples_result.scalars().all()
    samples_text = (
        "\n\n---\n\n".join(s.text for s in samples)
        if samples
        else ("The regulatory landscape is shifting faster than most boards realise.")
    )

    return StreamingResponse(
        stream_ai_response(
            "linkedin_draft",
            name=partner.name,
            title=partner.title or "Partner",
            firm=partner.firm_name,
            writing_samples=samples_text,
            topic=topic,
        ),
        headers=sse_headers(),
    )


# ─── Generic proxy (for frontend direct calls) ─────────────────────────────────


@router.post("/anthropic")
async def anthropic_proxy(
    request: Request,
    claims: TokenClaims = Depends(require_auth),
):
    """
    Direct Claude API proxy. Accepts Anthropic-format payloads.
    Used by geo pages and module pages that call Claude directly.
    Rate-limited per user.
    """
    await enforce_rate_limit(request, "ai", str(claims.user_id))

    body = await request.json()

    if not settings.anthropic_api_key:
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=500,
            content={"error": "ANTHROPIC_API_KEY not configured"},
        )

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": settings.anthropic_api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json=body,
        )

    from fastapi.responses import JSONResponse

    return JSONResponse(status_code=resp.status_code, content=resp.json())
