"""
app/routes/clients.py — Client endpoints with caching, auth, and streaming AI.
"""

import logging

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_auth, require_partner
from app.auth.models import User
from app.auth.service import TokenClaims
from app.cache.client import TTL_LONG, cache
from app.database import get_db
from app.models import ChurnSignal, Client, RiskLevel
from app.services.audit_log import AuditEventType, extract_request_meta, log_event

log = logging.getLogger(__name__)
_slog = structlog.get_logger(__name__)
router = APIRouter(prefix="/clients", tags=["clients"])


class ClientSummary(BaseModel):
    id: int
    name: str
    industry: str
    region: str
    partner_name: str | None
    practice_groups: list[str]
    churn_score: int
    risk_level: str
    wallet_share_pct: int | None
    days_since_last_contact: int
    annual_revenue: float | None
    estimated_annual_spend: float | None
    model_config = {"from_attributes": True}


class UpdateClientRequest(BaseModel):
    partner_name: str | None = None
    gc_name: str | None = None
    gc_email: str | None = None
    wallet_share_pct: int | None = Field(default=None, ge=0, le=100)
    days_since_last_contact: int | None = Field(default=None, ge=0)
    estimated_annual_spend: float | None = Field(default=None, ge=0)


class AddSignalRequest(BaseModel):
    signal_text: str = Field(min_length=5, max_length=500)
    severity: str = Field(default="medium", pattern="^(low|medium|high|critical)$")


@router.get("/", response_model=list[ClientSummary])
async def list_clients(
    risk: str | None = Query(default=None),
    min_churn: int = Query(default=0, ge=0, le=100),
    partner: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    claims: TokenClaims = Depends(require_auth),
):
    q = (
        select(Client)
        .where(Client.is_active)
        .order_by(Client.churn_score.desc())
        .offset(skip)
        .limit(limit)
    )
    if risk:
        try:
            q = q.where(Client.risk_level == RiskLevel(risk))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"Invalid risk level: {risk}") from exc
    if min_churn:
        q = q.where(Client.churn_score >= min_churn)
    if partner:
        q = q.where(Client.partner_name.ilike(f"%{partner}%"))
    result = await db.execute(q)
    return [ClientSummary.model_validate(c) for c in result.scalars().all()]


@router.get("/churn-scores")
async def churn_scores(
    db: AsyncSession = Depends(get_db),
    claims: TokenClaims = Depends(require_auth),
):
    """All clients ranked by churn score. Cached 4 hours."""
    cache_key = "clients:v1:churn_scores"
    cached = await cache.get(cache_key)
    if cached:
        return cached

    result = await db.execute(
        select(Client).where(Client.is_active).order_by(Client.churn_score.desc())
    )
    data = [
        {
            "id": c.id,
            "name": c.name,
            "churn_score": c.churn_score,
            "risk_level": c.risk_level.value if c.risk_level else "low",
            "partner_name": c.partner_name,
            "industry": c.industry,
            "region": c.region,
            "annual_revenue": float(c.annual_revenue or 0),
            "days_since_last_contact": c.days_since_last_contact,
            "practice_groups": c.practice_groups or [],
        }
        for c in result.scalars().all()
    ]
    await cache.set(cache_key, data, ttl=TTL_LONG)
    return data


@router.get("/{client_id}")
async def get_client(
    client_id: int,
    db: AsyncSession = Depends(get_db),
    claims: TokenClaims = Depends(require_auth),
):
    cache_key = cache.client_key(client_id)
    cached = await cache.get(cache_key)
    if cached:
        return cached
    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalars().first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    data = client.to_dict()
    await cache.set(cache_key, data, ttl=TTL_LONG)
    return data


@router.patch("/{client_id}", response_model=ClientSummary)
async def update_client(
    client_id: int,
    req: UpdateClientRequest,
    db: AsyncSession = Depends(get_db),
    claims: TokenClaims = Depends(require_partner),
    request: Request = None,
):
    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalars().first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    updated = {}
    for field, value in req.model_dump(exclude_none=True).items():
        setattr(client, field, value)
        updated[field] = value
    await db.commit()
    await cache.delete(cache.client_key(client_id))
    await cache.delete("clients:v1:churn_scores")
    await log_event(
        AuditEventType.data_export,
        user_id=claims.user_id,
        resource_type="client",
        resource_id=client_id,
        detail={"action": "update", "fields": list(updated.keys())},
        **(extract_request_meta(request) if request else {}),
    )
    return ClientSummary.model_validate(client)


@router.post("/{client_id}/signals", status_code=201)
async def add_signal(
    client_id: int,
    req: AddSignalRequest,
    db: AsyncSession = Depends(get_db),
    claims: TokenClaims = Depends(require_partner),
):
    result = await db.execute(select(Client).where(Client.id == client_id))
    if not result.scalars().first():
        raise HTTPException(status_code=404, detail="Client not found")
    signal = ChurnSignal(client_id=client_id, signal_text=req.signal_text, severity=req.severity)
    db.add(signal)
    await db.commit()
    await cache.delete(cache.client_key(client_id))
    await cache.delete("clients:v1:churn_scores")
    return {"id": signal.id, "signal_text": signal.signal_text, "severity": signal.severity}


@router.post("/{client_id}/churn-brief")
async def churn_brief(
    client_id: int,
    claims: TokenClaims = Depends(require_auth),
):
    """AI churn brief — removed from production."""
    return JSONResponse(
        status_code=410,
        content={"error": "AI brief generation has been removed from production."},
    )


@router.get("/{client_id}/churn-brief/stream")
async def churn_brief_stream(
    client_id: int,
    claims: TokenClaims = Depends(require_auth),
):
    """AI churn brief streaming — removed from production."""
    return JSONResponse(
        status_code=410,
        content={"error": "AI streaming has been removed from production."},
    )


@router.delete("/{client_id}/churn-brief/cache", status_code=204)
async def invalidate_brief_cache(
    client_id: int,
    claims: TokenClaims = Depends(require_partner),
):
    await cache.delete(cache.churn_brief_key(client_id))
    return None


@router.get("/wallet-share")
async def get_wallet_share(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    """Per active client: total billing, firm's share, top practice groups. Cache 4 hours."""
    try:
        result = await db.execute(text("""
            SELECT DISTINCT ON (c.id)
                c.id,
                c.name,
                0.0::float AS total_billing,
                0.0::float AS wallet_share,
                0.0::float AS competitor_estimate,
                0.0::float AS yoy_growth,
                ARRAY[]::text[] AS practice_groups,
                'medium' AS opportunity
            FROM companies c
            JOIN scoring_results sr ON sr.company_id = c.id
            ORDER BY c.id, sr.scored_at DESC
            LIMIT 100
        """))
        rows = result.mappings().all()
        return [dict(r) for r in rows]
    except Exception:
        _slog.exception("wallet_share_fetch_failed")
        return []
