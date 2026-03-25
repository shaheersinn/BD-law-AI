"""
app/routes/training.py — Phase 4: LLM Training REST API.

Endpoints (prefix /v1/training, admin-only):
  POST /pseudo-label    — trigger a pseudo-labeling run (Agent 018)
  POST /curate          — trigger training data curation (Agent 019)
  GET  /datasets        — list TrainingDataset records (paginated)
  GET  /datasets/{id}   — single dataset record

Background tasks are dispatched via FastAPI BackgroundTasks so the endpoint
returns immediately while the work runs in the background.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_admin
from app.database import get_db
from app.models.training import TrainingDataset

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/v1/training", tags=["training"])


# ── Serializers ────────────────────────────────────────────────────────────────


def _dataset_to_dict(ds: TrainingDataset) -> dict[str, Any]:
    return {
        "id": ds.id,
        "status": ds.status,
        "label_count": ds.label_count,
        "positive_count": ds.positive_count,
        "negative_count": ds.negative_count,
        "uncertain_count": ds.uncertain_count,
        "practice_areas": ds.practice_areas,
        "horizons": ds.horizons,
        "min_confidence": ds.min_confidence,
        "export_path": ds.export_path,
        "export_format": ds.export_format,
        "error_message": ds.error_message,
        "created_at": ds.created_at.isoformat() if ds.created_at else None,
        "completed_at": ds.completed_at.isoformat() if ds.completed_at else None,
        "duration_seconds": ds.duration_seconds,
    }


# ── Background Task Implementations ───────────────────────────────────────────


async def _run_pseudo_label_task(run_id: int, max_signals: int) -> None:
    """Background task: run PseudoLabeler inside its own DB session."""
    from app.database import AsyncSessionLocal
    from app.models.ground_truth import LabelingRun, RunStatus
    from app.training.pseudo_labeler import PseudoLabeler

    async with AsyncSessionLocal() as db:
        try:
            result = await PseudoLabeler().run(run_id=run_id, db=db, max_signals=max_signals)
            # Update LabelingRun status
            run = await db.get(LabelingRun, run_id)
            if run:
                run.status = RunStatus.completed.value
                run.completed_at = datetime.now(tz=UTC)
                run.positive_labels_created = result.get("pseudo_labels_created", 0)
            await db.commit()
            log.info("Pseudo-labeling background task complete", run_id=run_id, **result)
        except Exception as exc:  # noqa: BLE001
            log.error("Pseudo-labeling background task failed", run_id=run_id, error=str(exc))
            try:
                run = await db.get(LabelingRun, run_id)  # type: ignore[assignment]
                if run:
                    run.status = RunStatus.failed.value
                    run.error_message = str(exc)
                    run.completed_at = datetime.now(tz=UTC)
                await db.commit()
            except Exception as inner_exc:  # noqa: BLE001
                log.error("Failed to update run status on failure", error=str(inner_exc))


async def _run_curate_task(
    min_confidence: float,
    export_format: str,
    practice_areas: list[str] | None,
) -> None:
    """Background task: run TrainingDataCurator inside its own DB session."""
    from app.database import AsyncSessionLocal
    from app.training.curator import TrainingDataCurator

    async with AsyncSessionLocal() as db:
        try:
            result = await TrainingDataCurator().curate(
                db=db,
                min_confidence=min_confidence,
                export_format=export_format,
                practice_areas=practice_areas,
            )
            await db.commit()
            log.info("Curation background task complete", **result)
        except Exception as exc:  # noqa: BLE001
            log.error("Curation background task failed", error=str(exc))


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post("/pseudo-label")
async def trigger_pseudo_label(
    background_tasks: BackgroundTasks,
    max_signals: int = Query(default=5000, ge=1, le=50000),
    db: AsyncSession = Depends(get_db),
    _: Any = Depends(require_admin),
) -> dict[str, Any]:
    """
    Trigger Agent 018 (Pseudo-Labeler) to classify unlabeled signal records.

    Creates a LabelingRun record and dispatches classification in the background.
    Returns immediately with the run_id for status polling.
    """
    from app.models.ground_truth import LabelingRun, RunStatus, RunType

    run = LabelingRun(
        run_type=RunType.pseudo_label.value,
        status=RunStatus.running.value,
        started_at=datetime.now(tz=UTC),
        config={"max_signals": max_signals},
    )
    db.add(run)
    await db.flush()
    await db.commit()

    background_tasks.add_task(_run_pseudo_label_task, run.id, max_signals)

    log.info("Pseudo-label run dispatched", run_id=run.id, max_signals=max_signals)
    return {
        "status": "dispatched",
        "run_id": run.id,
        "max_signals": max_signals,
        "message": "Pseudo-labeling run started. Poll /api/v1/ground-truth/runs/{run_id} for status.",
    }


@router.post("/curate")
async def trigger_curate(
    background_tasks: BackgroundTasks,
    min_confidence: float = Query(default=0.70, ge=0.0, le=1.0),
    export_format: str = Query(default="parquet", pattern="^(parquet|csv)$"),
    _: Any = Depends(require_admin),
) -> dict[str, Any]:
    """
    Trigger Agent 019 (Training Data Curator) to build and export a training dataset.

    Dispatches curation in the background. Returns immediately.
    """
    background_tasks.add_task(
        _run_curate_task,
        min_confidence=min_confidence,
        export_format=export_format,
        practice_areas=None,
    )
    log.info("Curation run dispatched", min_confidence=min_confidence, format=export_format)
    return {
        "status": "dispatched",
        "min_confidence": min_confidence,
        "export_format": export_format,
        "message": "Curation run started. Poll /api/v1/training/datasets for results.",
    }


@router.get("/datasets")
async def list_datasets(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: Any = Depends(require_admin),
) -> dict[str, Any]:
    """List TrainingDataset records (most recent first)."""
    try:
        stmt = (
            select(TrainingDataset)
            .order_by(TrainingDataset.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(stmt)
        datasets = result.scalars().all()

        count_stmt = select(TrainingDataset)
        count_result = await db.execute(count_stmt)
        total = len(count_result.scalars().all())

        return {
            "items": [_dataset_to_dict(ds) for ds in datasets],
            "total": total,
            "skip": skip,
            "limit": limit,
        }
    except Exception as exc:  # noqa: BLE001
        log.error("Failed to list training datasets", error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to retrieve datasets") from exc


@router.get("/datasets/{dataset_id}")
async def get_dataset(
    dataset_id: int,
    db: AsyncSession = Depends(get_db),
    _: Any = Depends(require_admin),
) -> dict[str, Any]:
    """Retrieve a single TrainingDataset record by ID."""
    try:
        ds = await db.get(TrainingDataset, dataset_id)
        if ds is None:
            raise HTTPException(status_code=404, detail="Dataset not found")
        return _dataset_to_dict(ds)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        log.error("Failed to get training dataset", dataset_id=dataset_id, error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to retrieve dataset") from exc
