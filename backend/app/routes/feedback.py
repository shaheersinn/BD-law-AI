"""
app/routes/feedback.py — Phase 9: Feedback Loop API endpoints.

Endpoints:
    POST /api/v1/feedback/mandate     Partner manually confirms a mandate
    GET  /api/v1/feedback/accuracy    Prediction accuracy summary per practice area
    GET  /api/v1/feedback/drift       Current open model drift alerts
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_auth, require_partner
from app.auth.models import User
from app.database import get_db
from app.services.accuracy_tracker import get_accuracy_summary
from app.services.drift_detector import get_open_alerts
from app.services.mandate_confirmation import confirm_mandate, list_confirmations

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/v1/feedback", tags=["feedback"])


# ── Request / Response Models ──────────────────────────────────────────────────


class MandateConfirmRequest(BaseModel):
    company_id: int = Field(..., description="ORACLE company ID")
    practice_area: str = Field(..., min_length=1, max_length=100)
    confirmed_at: datetime = Field(..., description="Date mandate was confirmed")
    source: str = Field(..., min_length=1, max_length=200, description="Evidence source")
    notes: str | None = Field(None, max_length=1000)
    evidence_url: str | None = Field(None, max_length=2048)


class MandateConfirmResponse(BaseModel):
    confirmation_id: int
    company_id: int
    practice_area: str
    confirmed_at: str
    lead_days: int | None
    source: str
    message: str


class AccuracyRow(BaseModel):
    practice_area: str
    horizon: int
    n_total: int
    n_correct: int
    precision: float
    avg_lead_days: float | None


class DriftAlertRow(BaseModel):
    id: int
    practice_area: str
    detected_at: str | None
    accuracy_before: float
    accuracy_after: float
    delta: float
    ks_statistic: float | None
    ks_pvalue: float | None
    status: str


# ── POST /v1/feedback/mandate ─────────────────────────────────────────────────


@router.post(
    "/mandate",
    response_model=MandateConfirmResponse,
    summary="Manually confirm a mandate outcome",
    description=(
        "Partner-level endpoint. Records that a company retained counsel for a "
        "specific practice area. ORACLE cross-references the prior prediction and "
        "records lead time."
    ),
)
async def post_mandate_confirmation(
    body: MandateConfirmRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_partner),
) -> dict[str, Any]:
    try:
        result = await confirm_mandate(
            db=db,
            company_id=body.company_id,
            practice_area=body.practice_area,
            confirmed_at=body.confirmed_at,
            source=body.source,
            evidence_url=body.evidence_url,
            reviewed_by_user_id=current_user.id,
            is_auto_detected=False,
        )
    except Exception as exc:
        log.exception(
            "mandate confirmation failed",
            company_id=body.company_id,
            practice_area=body.practice_area,
        )
        raise HTTPException(
            status_code=500, detail="Failed to record mandate confirmation"
        ) from exc

    log.info(
        "mandate confirmed by partner",
        user_id=current_user.id,
        company_id=body.company_id,
        practice_area=body.practice_area,
        lead_days=result.get("lead_days"),
    )

    return {
        **result,
        "message": (
            "Mandate confirmed. "
            + (
                f"ORACLE predicted this {result['lead_days']} days in advance."
                if result.get("lead_days") is not None
                else "No prior prediction found at the 0.5 threshold."
            )
        ),
    }


# ── GET /v1/feedback/accuracy ─────────────────────────────────────────────────


@router.get(
    "/accuracy",
    response_model=list[AccuracyRow],
    summary="Prediction accuracy summary per practice area",
    description=(
        "Returns precision, n_confirmed, and avg lead days per practice area × horizon "
        "over the specified lookback window. Only practice areas with confirmed mandates appear."
    ),
)
async def get_accuracy(
    days: int = Query(default=90, ge=7, le=365, description="Lookback window in days"),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_auth),
) -> list[dict[str, Any]]:
    try:
        return await get_accuracy_summary(db, days=days)
    except Exception as exc:
        log.exception("accuracy summary failed")
        raise HTTPException(status_code=500, detail="Failed to retrieve accuracy summary") from exc


# ── GET /v1/feedback/drift ────────────────────────────────────────────────────


@router.get(
    "/drift",
    response_model=list[DriftAlertRow],
    summary="Open model drift alerts",
    description=(
        "Returns practice areas where prediction accuracy has dropped > 10 percentage "
        "points compared to the prior 30-day window. Alerts are created by Agent 031 "
        "(weekly). Acknowledge via PATCH /v1/feedback/drift/{id} (admin only)."
    ),
)
async def get_drift_alerts(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_auth),
) -> list[dict[str, Any]]:
    try:
        return await get_open_alerts(db)
    except Exception as exc:
        log.exception("drift alerts query failed")
        raise HTTPException(status_code=500, detail="Failed to retrieve drift alerts") from exc


# ── GET /v1/feedback/confirmations ───────────────────────────────────────────


@router.get(
    "/confirmations",
    summary="List recent mandate confirmations",
    description="Returns recent confirmations. Optionally filter by company or practice area.",
)
async def get_confirmations(
    company_id: int | None = Query(default=None),
    practice_area: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_auth),
) -> list[dict[str, Any]]:
    try:
        return await list_confirmations(
            db,
            company_id=company_id,
            practice_area=practice_area,
            limit=limit,
        )
    except Exception as exc:
        log.exception("list confirmations failed")
        raise HTTPException(status_code=500, detail="Failed to retrieve confirmations") from exc
