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
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
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
