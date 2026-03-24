"""
app/ground_truth/pipeline.py — Ground Truth Pipeline Orchestrator.

Coordinates the Retrospective Labeler (Agent 016) and Negative Sampler
(Agent 017) through a LabelingRun record that tracks execution state.

Usage:
    pipeline = GroundTruthPipeline()

    # Full run (retrospective + negative sampling)
    result = await pipeline.run_full(db)

    # Individual components
    result = await pipeline.run_retrospective(run_id, db)
    result = await pipeline.run_negative_sampling(run_id, db)
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ground_truth.labeler import RetrospectiveLabeler
from app.ground_truth.negative_sampler import NegativeSampler
from app.models.ground_truth import LabelingRun, RunStatus, RunType

log = structlog.get_logger(__name__)


class GroundTruthPipeline:
    """
    Orchestrates the full ground truth labeling pipeline.

    Creates LabelingRun records to track execution state and provide
    an audit trail of all labeling decisions.
    """

    def __init__(self) -> None:
        self._labeler = RetrospectiveLabeler()
        self._sampler = NegativeSampler()

    async def run_full(
        self,
        db: AsyncSession,
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Run both retrospective labeling and negative sampling.

        Creates one LabelingRun record for the full run.
        Returns summary of all labels created.
        """
        now = datetime.now(tz=UTC)
        run = await self._create_run(
            db=db,
            run_type=RunType.full.value,
            config=config,
            now=now,
        )

        try:
            retro_result = await self.run_retrospective(run_id=run.id, db=db, now=now)
            neg_result = await self.run_negative_sampling(run_id=run.id, db=db, now=now)

            # Update run record
            run.status = RunStatus.completed.value
            run.completed_at = datetime.now(tz=UTC)
            run.companies_processed = retro_result["companies_processed"]
            run.positive_labels_created = retro_result["positive_labels_created"]
            run.negative_labels_created = neg_result["negative_labels_created"]
            await db.commit()

            summary = {
                "run_id": run.id,
                "run_type": RunType.full.value,
                "status": RunStatus.completed.value,
                "companies_processed": run.companies_processed,
                "positive_labels_created": run.positive_labels_created,
                "negative_labels_created": run.negative_labels_created,
                "duration_seconds": run.duration_seconds,
            }
            log.info("Ground truth full run complete", **summary)
            return summary

        except Exception as exc:  # noqa: BLE001
            log.error("Ground truth full run failed", run_id=run.id, error=str(exc))
            run.status = RunStatus.failed.value
            run.completed_at = datetime.now(tz=UTC)
            run.error_message = str(exc)
            await db.commit()
            raise

    async def run_retrospective(
        self,
        run_id: int,
        db: AsyncSession,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        """
        Run only the retrospective labeler (Agent 016).

        Fetches all companies with signal history and generates positive labels.
        """
        if now is None:
            now = datetime.now(tz=UTC)

        company_ids = await self._labeler.get_all_company_ids(db)
        log.info("Starting retrospective labeling", companies=len(company_ids))

        result = await self._labeler.run_batch(
            run_id=run_id,
            company_ids=company_ids,
            db=db,
            now=now,
        )
        await db.commit()
        return result

    async def run_negative_sampling(
        self,
        run_id: int,
        db: AsyncSession,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        """
        Run only the negative sampler (Agent 017).

        Finds companies with no legal engagement signals and creates negatives.
        """
        if now is None:
            now = datetime.now(tz=UTC)

        log.info("Starting negative sampling", run_id=run_id)
        result = await self._sampler.sample(
            run_id=run_id,
            db=db,
            now=now,
        )
        await db.commit()
        return result

    async def get_run_by_id(self, run_id: int, db: AsyncSession) -> LabelingRun | None:
        """Fetch a LabelingRun by ID."""
        try:
            stmt = select(LabelingRun).where(LabelingRun.id == run_id)
            result = await db.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as exc:  # noqa: BLE001
            log.error("Failed to fetch labeling run", run_id=run_id, error=str(exc))
            return None

    async def _create_run(
        self,
        db: AsyncSession,
        run_type: str,
        config: dict[str, Any] | None,
        now: datetime,
    ) -> LabelingRun:
        """Create and persist a LabelingRun record."""
        run = LabelingRun(
            run_type=run_type,
            status=RunStatus.running.value,
            started_at=now,
            config=config or {},
        )
        db.add(run)
        await db.flush()  # assigns run.id
        await db.commit()
        log.info("Labeling run created", run_id=run.id, run_type=run_type)
        return run
