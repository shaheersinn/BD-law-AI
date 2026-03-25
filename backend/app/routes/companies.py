"""
app/routes/companies.py — Phase 7 company search and profile endpoints.

Endpoints:
    GET /api/v1/companies/search?q={name}   Fuzzy name search (rapidfuzz)
    GET /api/v1/companies/{company_id}      Company profile + latest feature values
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_auth
from app.auth.models import User
from app.cache.client import cache
from app.database import get_db

log = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/companies", tags=["companies"])

_ALIASES_CACHE_KEY = "companies:aliases:v1"
_ALIASES_TTL = 3_600  # 1 hour
_PROFILE_TTL = 3_600  # 1 hour


@router.get("/search", summary="Fuzzy company name search")
async def search_companies(
    q: str = Query(..., min_length=2, max_length=200),
    limit: int = Query(default=10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_auth),
) -> list[dict[str, Any]]:
    """
    Fuzzy search over company names and aliases using rapidfuzz WRatio.
    Returns up to `limit` matches with similarity score >= 60.
    """
    try:
        from rapidfuzz import fuzz, process
    except ImportError as exc:
        raise HTTPException(
            status_code=503,
            detail="rapidfuzz is not installed. Run: pip install rapidfuzz",
        ) from exc

    # Load aliases from cache or DB
    alias_data: list[dict[str, Any]] | None = await cache.get(_ALIASES_CACHE_KEY)
    if alias_data is None:
        try:
            result = await db.execute(
                text("""
                    SELECT ca.company_id, ca.alias, c.name AS canonical_name
                    FROM company_aliases ca
                    JOIN companies c ON c.id = ca.company_id
                    ORDER BY ca.confidence DESC
                """)
            )
            alias_data = [
                {
                    "company_id": row["company_id"],
                    "alias": row["alias"],
                    "canonical_name": row["canonical_name"],
                }
                for row in result.mappings()
            ]
            await cache.set(_ALIASES_CACHE_KEY, alias_data, ttl=_ALIASES_TTL)
        except Exception:
            log.exception("companies: failed to load aliases from DB")
            return []

    if not alias_data:
        return []

    # Build search corpus: list of (display_text, index)
    choices = [entry["alias"] for entry in alias_data]

    matches = process.extract(
        q,
        choices,
        scorer=fuzz.WRatio,
        limit=limit * 3,  # over-fetch to deduplicate by company_id
        score_cutoff=60,
    )

    seen: set[int] = set()
    results: list[dict[str, Any]] = []
    for _match_str, score, idx in matches:
        entry = alias_data[idx]
        cid = int(entry["company_id"])
        if cid in seen:
            continue
        seen.add(cid)
        results.append(
            {
                "company_id": cid,
                "name": entry["canonical_name"],
                "matched_alias": entry["alias"],
                "score": round(score / 100.0, 3),
            }
        )
        if len(results) >= limit:
            break

    return results


@router.get("/{company_id}", summary="Company profile with latest feature snapshot")
async def get_company(
    company_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_auth),
) -> dict[str, Any]:
    """Return company metadata and the most recent feature vector snapshot."""
    cache_key = f"company:{company_id}:profile"
    cached = await cache.get(cache_key)
    if cached is not None:
        return cached  # type: ignore[return-value]

    try:
        result = await db.execute(
            text("""
                SELECT
                    c.id,
                    c.name,
                    c.ticker,
                    c.exchange,
                    c.sector,
                    c.industry,
                    c.province,
                    c.country,
                    c.hq_city,
                    c.employee_count,
                    c.market_cap_cad,
                    c.revenue_cad,
                    c.status,
                    c.is_publicly_listed,
                    c.priority_tier,
                    c.last_scraped_at,
                    c.signal_count,
                    c.created_at
                FROM companies c
                WHERE c.id = :company_id
            """),
            {"company_id": company_id},
        )
        company_row = result.mappings().first()
    except Exception as exc:
        log.exception("companies: DB error fetching company %d", company_id)
        raise HTTPException(status_code=500, detail="Database error") from exc

    if company_row is None:
        raise HTTPException(status_code=404, detail=f"Company {company_id} not found")

    # Fetch latest feature snapshot
    features: dict[str, Any] = {}
    try:
        feat_result = await db.execute(
            text("""
                SELECT * FROM company_features
                WHERE company_id = :company_id
                ORDER BY feature_date DESC
                LIMIT 1
            """),
            {"company_id": company_id},
        )
        feat_row = feat_result.mappings().first()
        if feat_row:
            features = {k: v for k, v in dict(feat_row).items() if k not in ("id", "company_id")}
    except Exception:
        log.exception("companies: failed to fetch features for company %d", company_id)

    data: dict[str, Any] = {
        "id": company_row["id"],
        "name": company_row["name"],
        "ticker": company_row["ticker"],
        "exchange": company_row["exchange"],
        "sector": company_row["sector"],
        "industry": company_row["industry"],
        "province": company_row["province"],
        "country": company_row["country"],
        "hq_city": company_row["hq_city"],
        "employee_count": company_row["employee_count"],
        "market_cap_cad": company_row["market_cap_cad"],
        "revenue_cad": company_row["revenue_cad"],
        "status": str(company_row["status"]) if company_row["status"] else None,
        "is_publicly_listed": company_row["is_publicly_listed"],
        "priority_tier": company_row["priority_tier"],
        "last_scraped_at": (
            company_row["last_scraped_at"].isoformat() if company_row["last_scraped_at"] else None
        ),
        "signal_count": company_row["signal_count"],
        "created_at": (
            company_row["created_at"].isoformat() if company_row["created_at"] else None
        ),
        "features": features,
    }

    await cache.set(cache_key, data, ttl=_PROFILE_TTL)
    return data
