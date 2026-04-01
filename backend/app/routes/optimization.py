"""
app/routes/optimization.py — Phase 12: Post-Launch Optimization API.

Endpoints:
    GET  /api/v1/optimization/usage-report          Latest weekly usage snapshot
    GET  /api/v1/optimization/score-quality         Latest score quality summary
    GET  /api/v1/optimization/perf-report           p50/p95/p99 by endpoint (last N days)
    GET  /api/v1/optimization/signal-overrides      List active signal weight overrides
    POST /api/v1/optimization/signal-override       Create/update a signal weight override
    DELETE /api/v1/optimization/signal-override/{id} Deactivate an override
"""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_partner
from app.auth.models import User
from app.cache.client import cache
from app.database import get_db
from app.services.analytics_service import get_latest_usage_report, get_perf_report
from app.services.score_quality import get_latest_score_quality_report

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/v1/optimization", tags=["optimization"])

# Redis cache key for signal overrides (used by ML scoring layer)
_OVERRIDES_CACHE_KEY = "signal_overrides:v1"
_OVERRIDES_CACHE_TTL = 3600  # 1 hour


# ── Pydantic models ────────────────────────────────────────────────────────────


class SignalOverrideCreate(BaseModel):
    signal_type: str = Field(..., min_length=1, max_length=100)
    practice_area: str = Field(..., min_length=1, max_length=100)
    multiplier: float = Field(..., ge=0.01, le=5.0)
    reason: str | None = Field(None, max_length=500)


class SignalOverrideOut(BaseModel):
    id: int
    signal_type: str
    practice_area: str
    multiplier: float
    reason: str | None
    set_by_user_id: int | None
    is_active: bool
    created_at: str
    updated_at: str


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/usage-report", summary="Latest weekly usage analytics snapshot")
async def get_usage_report(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_partner),
) -> dict[str, Any]:
    """Return the most recently computed weekly usage report."""
    report = await get_latest_usage_report(db)
    if report is None:
        raise HTTPException(
            status_code=404,
            detail="No usage reports found. Agent 033 runs weekly on Monday 08:00 UTC.",
        )
    return report


@router.get("/score-quality", summary="Latest score quality report (per-practice-area precision)")
async def get_score_quality(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_partner),
) -> dict[str, Any]:
    """Return the most recently computed score quality report."""
    report = await get_latest_score_quality_report(db)
    if report is None:
        raise HTTPException(
            status_code=404,
            detail="No score quality reports found. Agent 033 runs weekly on Monday 08:00 UTC.",
        )
    return report


@router.get("/perf-report", summary="API endpoint performance (p50/p95/p99 latency)")
async def get_performance_report(
    days: int = Query(default=7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_partner),
) -> list[dict[str, Any]]:
    """
    Return p50/p95/p99 response times per endpoint from the last N days.
    Sorted by p95 DESC — slowest endpoints first.
    If any p95 > 300ms, the endpoint description flags it for review.
    """
    rows = await get_perf_report(db, days=days)
    for row in rows:
        row["needs_attention"] = (row.get("p95_ms") or 0) > 300
    return rows


@router.get(
    "/signal-overrides",
    response_model=list[SignalOverrideOut],
    summary="List all active signal weight overrides",
)
async def list_signal_overrides(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_partner),
) -> list[dict[str, Any]]:
    """Return all active signal weight overrides set by the BD team."""
    rows = (
        await db.execute(
            text(
                """
                SELECT id, signal_type, practice_area, multiplier, reason,
                       set_by_user_id, is_active, created_at, updated_at
                FROM signal_weight_overrides
                WHERE is_active = TRUE
                ORDER BY practice_area, signal_type
                """
            )
        )
    ).all()

    return [
        {
            "id": row.id,
            "signal_type": row.signal_type,
            "practice_area": row.practice_area,
            "multiplier": row.multiplier,
            "reason": row.reason,
            "set_by_user_id": row.set_by_user_id,
            "is_active": row.is_active,
            "created_at": row.created_at.isoformat(),
            "updated_at": row.updated_at.isoformat(),
        }
        for row in rows
    ]


@router.post(
    "/signal-override",
    response_model=SignalOverrideOut,
    status_code=201,
    summary="Create or update a signal weight override",
)
async def create_signal_override(
    body: SignalOverrideCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_partner),
) -> dict[str, Any]:
    """
    Set a human multiplier for a signal_type × practice_area combination.
    If an active override already exists for this pair, it is replaced.
    Human overrides are applied after ML-calibrated weights (human wins).
    """
    # Deactivate any existing active override for this pair
    await db.execute(
        text(
            """
            UPDATE signal_weight_overrides
            SET is_active = FALSE, updated_at = NOW()
            WHERE signal_type = :signal_type
              AND practice_area = :practice_area
              AND is_active = TRUE
            """
        ),
        {"signal_type": body.signal_type, "practice_area": body.practice_area},
    )

    # Insert new override
    row = (
        await db.execute(
            text(
                """
                INSERT INTO signal_weight_overrides
                    (signal_type, practice_area, multiplier, reason, set_by_user_id)
                VALUES (:signal_type, :practice_area, :multiplier, :reason, :user_id)
                RETURNING id, signal_type, practice_area, multiplier, reason,
                          set_by_user_id, is_active, created_at, updated_at
                """
            ),
            {
                "signal_type": body.signal_type,
                "practice_area": body.practice_area,
                "multiplier": body.multiplier,
                "reason": body.reason,
                "user_id": user.id,
            },
        )
    ).first()

    await db.commit()

    # Invalidate cache so scoring layer picks up the new override
    await _invalidate_overrides_cache()

    log.info(
        "signal_override.created",
        signal_type=body.signal_type,
        practice_area=body.practice_area,
        multiplier=body.multiplier,
        set_by=user.id,
    )

    return {
        "id": row.id,
        "signal_type": row.signal_type,
        "practice_area": row.practice_area,
        "multiplier": row.multiplier,
        "reason": row.reason,
        "set_by_user_id": row.set_by_user_id,
        "is_active": row.is_active,
        "created_at": row.created_at.isoformat(),
        "updated_at": row.updated_at.isoformat(),
    }


@router.delete(
    "/signal-override/{override_id}",
    status_code=204,
    response_class=Response,
    summary="Deactivate a signal weight override",
)
async def delete_signal_override(
    override_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_partner),
) -> None:
    """
    Deactivate a signal weight override by ID.
    The row is kept for audit trail — is_active is set to FALSE.
    """
    result = await db.execute(
        text(
            """
            UPDATE signal_weight_overrides
            SET is_active = FALSE, updated_at = NOW()
            WHERE id = :id AND is_active = TRUE
            RETURNING id
            """
        ),
        {"id": override_id},
    )
    updated = result.first()
    await db.commit()

    if updated is None:
        raise HTTPException(
            status_code=404,
            detail=f"Override {override_id} not found or already inactive.",
        )

    await _invalidate_overrides_cache()
    log.info("signal_override.deactivated", override_id=override_id)
    return Response(status_code=204)


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _invalidate_overrides_cache() -> None:
    """Delete the signal_overrides:v1 Redis cache key."""
    try:
        await cache.delete(_OVERRIDES_CACHE_KEY)
    except Exception:
        log.warning("optimization: failed to invalidate overrides cache")


async def warm_overrides_cache(db: AsyncSession) -> None:
    """
    Load all active signal_weight_overrides into Redis cache.
    Called on app startup and after any override mutation.
    TTL: 1 hour.
    """
    try:
        rows = (
            await db.execute(
                text(
                    """
                    SELECT signal_type, practice_area, multiplier
                    FROM signal_weight_overrides
                    WHERE is_active = TRUE
                    """
                )
            )
        ).all()

        overrides = [
            {
                "signal_type": row.signal_type,
                "practice_area": row.practice_area,
                "multiplier": row.multiplier,
            }
            for row in rows
        ]

        await cache.set(_OVERRIDES_CACHE_KEY, overrides, ttl=_OVERRIDES_CACHE_TTL)
        log.info("optimization.overrides_cache_warmed", count=len(overrides))
    except Exception:
        log.warning("optimization: failed to warm overrides cache")
