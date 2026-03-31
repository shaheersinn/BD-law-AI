"""
app/routes/scores.py — Phase 7 scoring API endpoints.

Endpoints:
    GET  /api/v1/scores/{company_id}          34×3 mandate matrix + velocity + anomaly
    GET  /api/v1/scores/{company_id}/explain  SHAP counterfactuals for top 5 practice areas
    POST /api/v1/scores/batch                 Bulk scores (max 50 companies)
"""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_auth
from app.auth.models import User
from app.database import get_db
from app.services.scoring_service import (
    get_batch_scores,
    get_company_explain,
    get_company_score,
)

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/v1/scores", tags=["scores"])

# Cache TTL for top-velocity endpoint (15 minutes)
# Public constant — referenced by Phase 10 tests and monitoring.
VELOCITY_CACHE_TTL = 900


# ── Pydantic models ────────────────────────────────────────────────────────────


class HorizonScores(BaseModel):
    score_30d: float
    score_60d: float
    score_90d: float


class Confidence(BaseModel):
    low: float | None = None
    high: float | None = None


class ScoreResponse(BaseModel):
    company_id: int
    company_name: str
    scored_at: str
    scores: dict[str, dict[str, float]]
    velocity_score: float | None = None
    anomaly_score: float | None = None
    confidence: Confidence
    top_signals: list[dict[str, Any]] = Field(default_factory=list)
    model_versions: dict[str, str] = Field(default_factory=dict)


class ExplainItem(BaseModel):
    practice_area: str
    horizon: int
    score: float
    top_shap_features: list[dict[str, Any]] = Field(default_factory=list)
    counterfactuals: list[dict[str, Any]] = Field(default_factory=list)
    base_value: float | None = None
    explained_at: str | None = None


class BatchScoreRequest(BaseModel):
    company_ids: list[int] = Field(..., min_length=1, max_length=50)
    practice_areas: list[str] | None = None


# ── Endpoints ─────────────────────────────────────────────────────────────────


TOP_VELOCITY_SQL = """
WITH latest AS (
    SELECT DISTINCT ON (company_id)
        company_id, velocity_score, scores, scored_at, anomaly_score
    FROM scoring_results
    WHERE scored_at >= NOW() - INTERVAL '48 hours'
      AND velocity_score IS NOT NULL
    ORDER BY company_id, scored_at DESC
)
SELECT
    l.company_id,
    l.velocity_score,
    l.scores,
    l.scored_at,
    l.anomaly_score,
    c.name AS company_name,
    c.sector
FROM latest l
JOIN companies c ON c.id = l.company_id
ORDER BY l.velocity_score DESC
LIMIT :limit
"""


@router.get("/top-velocity", summary="Top companies by velocity score")
async def get_top_velocity_companies(
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_auth),
) -> list[dict[str, Any]]:
    """
    Top N companies by 7-day mandate probability velocity.
    Returns company_id, velocity_score, top_practice_area, top_score_30d.
    Reads from most recent scoring_results per company (last 48h).
    Cached 15 minutes.
    """
    import json as json_mod

    from app.cache.client import cache

    cache_key = f"top_velocity:{limit}"
    cached = await cache.get(cache_key)
    if cached:
        return cached

    result = await db.execute(text(TOP_VELOCITY_SQL), {"limit": limit})
    rows = result.fetchall()

    output = []
    for row in rows:
        company_id_val, velocity, scores_json, scored_at, anomaly, name, sector = row

        # Find the highest-scoring practice area at 30d
        top_pa = None
        top_score_30d = 0.0
        if scores_json:
            scores_data = (
                scores_json if isinstance(scores_json, dict) else json_mod.loads(scores_json)
            )
            for pa, horizons in scores_data.items():
                s30 = horizons.get("30d", 0.0) or 0.0
                if s30 > top_score_30d:
                    top_score_30d = s30
                    top_pa = pa

        output.append(
            {
                "company_id": company_id_val,
                "company_name": name,
                "sector": sector,
                "velocity_score": round(float(velocity), 4),
                "top_practice_area": top_pa,
                "top_score_30d": round(top_score_30d, 4),
                "anomaly_score": round(float(anomaly), 4) if anomaly else None,
                "scored_at": scored_at.isoformat() if scored_at else None,
            }
        )

    await cache.set(cache_key, output, ttl=VELOCITY_CACHE_TTL)
    return output


@router.get("/{company_id}", response_model=ScoreResponse, summary="Get company score matrix")
async def get_score(
    company_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_auth),
) -> dict[str, Any]:
    """Return the 34×3 mandate probability matrix for a company."""
    data = await get_company_score(company_id, db)
    if data is None:
        raise HTTPException(
            status_code=404,
            detail=f"No scores found for company {company_id}. Scoring may be pending.",
        )
    return data


@router.get(
    "/{company_id}/explain",
    response_model=list[ExplainItem],
    summary="SHAP explanations for top practice areas",
)
async def get_explain(
    company_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_auth),
) -> list[dict[str, Any]]:
    """Return SHAP counterfactuals for the top 5 highest-scoring practice areas."""
    return await get_company_explain(company_id, db)


@router.post("/batch", summary="Bulk score retrieval (max 50 companies)")
async def batch_scores(
    req: BatchScoreRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_auth),
) -> list[dict[str, Any] | None]:
    """
    Return scores for up to 50 companies in one request.
    Positions in the response correspond to positions in company_ids.
    Null entries indicate companies with no scores yet.
    """
    return await get_batch_scores(req.company_ids, req.practice_areas, db)
