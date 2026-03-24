"""
app/routes/ground_truth.py — Phase 3 Ground Truth REST API.

Endpoints (prefix: /api/v1/ground-truth):
  GET  /labels                     List ground truth labels (partner+)
  GET  /labels/{company_id}        Labels for one company (partner+)
  GET  /stats                      Label distribution stats (partner+)
  POST /runs                       Trigger a labeling run (admin only)
  GET  /runs                       List labeling runs (partner+)
  GET  /runs/{run_id}              Single run status (partner+)
"""

from __future__ import annotations

from datetime import UTC
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_admin, require_partner
from app.auth.models import User
from app.database import get_db
from app.ground_truth.pipeline import GroundTruthPipeline
from app.models.ground_truth import GroundTruthLabel, LabelingRun

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/v1/ground-truth", tags=["ground-truth"])

# Module-level pipeline instance (stateless, safe to share)
_pipeline = GroundTruthPipeline()


# ── Labels ─────────────────────────────────────────────────────────────────────


@router.get("/labels", summary="List ground truth labels")
async def list_labels(
    label_type: str | None = Query(None, description="Filter by label_type"),
    practice_area: str | None = Query(None, description="Filter by practice_area"),
    horizon_days: int | None = Query(None, description="Filter by horizon (30/60/90)"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    _user: User = Depends(require_partner),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    List ground truth labels with optional filters.

    Requires partner or admin role.
    """
    try:
        stmt = select(GroundTruthLabel)
        if label_type is not None:
            stmt = stmt.where(GroundTruthLabel.label_type == label_type)
        if practice_area is not None:
            stmt = stmt.where(GroundTruthLabel.practice_area == practice_area)
        if horizon_days is not None:
            stmt = stmt.where(GroundTruthLabel.horizon_days == horizon_days)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await db.execute(count_stmt)
        total: int = total_result.scalar_one()

        stmt = stmt.order_by(GroundTruthLabel.created_at.desc()).limit(limit).offset(offset)
        result = await db.execute(stmt)
        labels = result.scalars().all()
    except Exception as exc:  # noqa: BLE001
        log.error("Failed to list ground truth labels", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve labels",
        ) from exc

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [_label_to_dict(lbl) for lbl in labels],
    }


@router.get("/labels/{company_id}", summary="Labels for one company")
async def get_company_labels(
    company_id: int,
    _user: User = Depends(require_partner),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Return all ground truth labels for a single company.

    Requires partner or admin role.
    """
    try:
        stmt = (
            select(GroundTruthLabel)
            .where(GroundTruthLabel.company_id == company_id)
            .order_by(
                GroundTruthLabel.horizon_days.asc(),
                GroundTruthLabel.created_at.desc(),
            )
        )
        result = await db.execute(stmt)
        labels = result.scalars().all()
    except Exception as exc:  # noqa: BLE001
        log.error("Failed to fetch company labels", company_id=company_id, error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve labels",
        ) from exc

    return {
        "company_id": company_id,
        "count": len(labels),
        "labels": [_label_to_dict(lbl) for lbl in labels],
    }


# ── Stats ──────────────────────────────────────────────────────────────────────


@router.get("/stats", summary="Label distribution stats")
async def get_label_stats(
    _user: User = Depends(require_partner),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Return aggregate statistics across all ground truth labels.

    Requires partner or admin role.
    """
    try:
        # Label type breakdown
        type_stmt = text(
            """
            SELECT label_type, COUNT(*) AS cnt
            FROM ground_truth_labels
            GROUP BY label_type
            ORDER BY label_type
            """
        )
        type_result = await db.execute(type_stmt)
        by_type = {row[0]: row[1] for row in type_result.fetchall()}

        # Horizon breakdown
        horizon_stmt = text(
            """
            SELECT horizon_days, label_type, COUNT(*) AS cnt
            FROM ground_truth_labels
            GROUP BY horizon_days, label_type
            ORDER BY horizon_days, label_type
            """
        )
        horizon_result = await db.execute(horizon_stmt)
        by_horizon: dict[str, dict[str, int]] = {}
        for row in horizon_result.fetchall():
            h_key = str(row[0])
            by_horizon.setdefault(h_key, {})[row[1]] = row[2]

        # Top practice areas (positive labels only)
        pa_stmt = text(
            """
            SELECT practice_area, COUNT(*) AS cnt
            FROM ground_truth_labels
            WHERE label_type = 'positive'
              AND practice_area IS NOT NULL
            GROUP BY practice_area
            ORDER BY cnt DESC
            LIMIT 10
            """
        )
        pa_result = await db.execute(pa_stmt)
        top_practice_areas = [
            {"practice_area": row[0], "count": row[1]} for row in pa_result.fetchall()
        ]

        # Total unique companies labeled
        company_stmt = text("SELECT COUNT(DISTINCT company_id) FROM ground_truth_labels")
        company_result = await db.execute(company_stmt)
        unique_companies: int = company_result.scalar_one() or 0

    except Exception as exc:  # noqa: BLE001
        log.error("Failed to compute label stats", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to compute stats",
        ) from exc

    total = sum(by_type.values())
    return {
        "total_labels": total,
        "unique_companies_labeled": unique_companies,
        "by_type": by_type,
        "by_horizon": by_horizon,
        "top_practice_areas": top_practice_areas,
    }


# ── Runs ───────────────────────────────────────────────────────────────────────


@router.post("/runs", status_code=status.HTTP_202_ACCEPTED, summary="Trigger labeling run")
async def trigger_run(
    run_type: str = Query(
        "full",
        description="Run type: retrospective | negative_sampling | full",
    ),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Trigger a ground truth labeling run.

    Requires admin role. Run executes synchronously (use Celery for async in production).
    Returns the run summary on completion.
    """
    valid_types = {"retrospective", "negative_sampling", "full"}
    if run_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid run_type. Must be one of: {', '.join(sorted(valid_types))}",
        )

    log.info("Labeling run triggered via API", run_type=run_type)

    try:
        if run_type == "full":
            result = await _pipeline.run_full(db=db)
        elif run_type == "retrospective":
            # Create a run record first
            from datetime import datetime

            now = datetime.now(tz=UTC)
            run = await _pipeline._create_run(  # noqa: SLF001
                db=db, run_type=run_type, config={}, now=now
            )
            result = await _pipeline.run_retrospective(run_id=run.id, db=db, now=now)
            result["run_id"] = run.id
        else:  # negative_sampling
            from datetime import datetime

            now = datetime.now(tz=UTC)
            run = await _pipeline._create_run(  # noqa: SLF001
                db=db, run_type=run_type, config={}, now=now
            )
            result = await _pipeline.run_negative_sampling(run_id=run.id, db=db, now=now)
            result["run_id"] = run.id
    except Exception as exc:  # noqa: BLE001
        log.error("Labeling run failed", run_type=run_type, error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Labeling run failed: {exc!s}",
        ) from exc

    return result


@router.get("/runs", summary="List labeling runs")
async def list_runs(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _user: User = Depends(require_partner),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    List all labeling runs, newest first.

    Requires partner or admin role.
    """
    try:
        count_stmt = select(func.count()).select_from(LabelingRun)
        total_result = await db.execute(count_stmt)
        total: int = total_result.scalar_one()

        stmt = (
            select(LabelingRun).order_by(LabelingRun.created_at.desc()).limit(limit).offset(offset)
        )
        result = await db.execute(stmt)
        runs = result.scalars().all()
    except Exception as exc:  # noqa: BLE001
        log.error("Failed to list labeling runs", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve runs",
        ) from exc

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [_run_to_dict(r) for r in runs],
    }


@router.get("/runs/{run_id}", summary="Get labeling run by ID")
async def get_run(
    run_id: int,
    _user: User = Depends(require_partner),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Return the status and summary of a single labeling run.

    Requires partner or admin role.
    """
    run = await _pipeline.get_run_by_id(run_id=run_id, db=db)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Labeling run {run_id} not found",
        )
    return _run_to_dict(run)


# ── Serializers ────────────────────────────────────────────────────────────────


def _label_to_dict(label: GroundTruthLabel) -> dict[str, Any]:
    return {
        "id": label.id,
        "company_id": label.company_id,
        "label_type": label.label_type,
        "practice_area": label.practice_area,
        "horizon_days": label.horizon_days,
        "label_source": label.label_source,
        "confidence_score": label.confidence_score,
        "is_validated": label.is_validated,
        "signal_window_start": label.signal_window_start.isoformat()
        if label.signal_window_start
        else None,
        "signal_window_end": label.signal_window_end.isoformat()
        if label.signal_window_end
        else None,
        "evidence_signal_ids": label.evidence_signal_ids or [],
        "labeling_run_id": label.labeling_run_id,
        "created_at": label.created_at.isoformat() if label.created_at else None,
    }


def _run_to_dict(run: LabelingRun) -> dict[str, Any]:
    return {
        "id": run.id,
        "run_type": run.run_type,
        "status": run.status,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "companies_processed": run.companies_processed,
        "positive_labels_created": run.positive_labels_created,
        "negative_labels_created": run.negative_labels_created,
        "total_labels": run.total_labels,
        "duration_seconds": run.duration_seconds,
        "error_message": run.error_message,
        "created_at": run.created_at.isoformat() if run.created_at else None,
    }
