"""
app/ground_truth/labeler.py — Agent 016: Retrospective Labeler.

Looks back at the signal_records history for each company and assigns
positive ground truth labels where a legal engagement event occurred
within the follow-up horizon after the signal window.

Label assignment logic per (company, horizon_days):
  1. Signal window: [scraped_at - horizon_days*2, scraped_at - horizon_days]
     (signals that were present BEFORE the horizon period)
  2. Follow-up window: [scraped_at - horizon_days, scraped_at]
     (period in which legal engagement would have occurred)
  3. If ANY positive signal type appears in the follow-up window →
     assign positive label for the matching practice area(s)
  4. Confidence = 0.75 (default, no manual validation)
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ground_truth.constants import (
    DEFAULT_LABEL_CONFIDENCE,
    HORIZONS,
    MIN_POSITIVE_SIGNALS_FOR_LABEL,
    POSITIVE_SIGNAL_TYPES,
    SIGNAL_TYPE_TO_PRACTICE_AREAS,
)
from app.models.ground_truth import GroundTruthLabel, LabelType

log = structlog.get_logger(__name__)


class RetrospectiveLabeler:
    """
    Agent 016 — Retrospective Labeler.

    Assigns positive ground truth labels by examining historical signal_records.
    For each company × horizon combination, checks whether legal engagement
    signals appeared in the follow-up period after the observation window.
    """

    async def label_company(
        self,
        company_id: int,
        run_id: int,
        now: datetime,
        db: AsyncSession,
    ) -> list[GroundTruthLabel]:
        """
        Generate positive labels for one company across all horizons (30/60/90).

        Returns list of GroundTruthLabel objects (not yet committed to DB).
        Caller is responsible for db.add() and db.commit().
        """
        labels: list[GroundTruthLabel] = []

        for horizon in HORIZONS:
            new_labels = await self._label_for_horizon(
                company_id=company_id,
                run_id=run_id,
                horizon=horizon,
                now=now,
                db=db,
            )
            labels.extend(new_labels)

        return labels

    async def _label_for_horizon(
        self,
        company_id: int,
        run_id: int,
        horizon: int,
        now: datetime,
        db: AsyncSession,
    ) -> list[GroundTruthLabel]:
        """
        For a given horizon, query follow-up window for positive signals.

        Follow-up window: [now - horizon, now]
        Signal window (observation): [now - horizon*2, now - horizon]
        """
        follow_up_start = now - timedelta(days=horizon)
        follow_up_end = now
        signal_window_start = now - timedelta(days=horizon * 2)
        signal_window_end = follow_up_start

        # Query follow-up window for any positive signal types
        try:
            stmt = text(
                """
                SELECT id, signal_type
                FROM signal_records
                WHERE company_id = :company_id
                  AND signal_type = ANY(:positive_types)
                  AND scraped_at >= :window_start
                  AND scraped_at < :window_end
                ORDER BY scraped_at ASC
                """
            )
            result = await db.execute(
                stmt,
                {
                    "company_id": company_id,
                    "positive_types": list(POSITIVE_SIGNAL_TYPES),
                    "window_start": follow_up_start,
                    "window_end": follow_up_end,
                },
            )
            rows = result.fetchall()
        except Exception as exc:  # noqa: BLE001
            log.error(
                "DB error querying follow-up signals",
                company_id=company_id,
                horizon=horizon,
                error=str(exc),
            )
            return []

        if len(rows) < MIN_POSITIVE_SIGNALS_FOR_LABEL:
            return []

        # Group signals by practice area
        practice_area_to_signals: dict[str, list[int]] = {}
        for row in rows:
            signal_id: int = row[0]
            signal_type: str = row[1]
            for practice_area in SIGNAL_TYPE_TO_PRACTICE_AREAS.get(signal_type, []):
                practice_area_to_signals.setdefault(practice_area, []).append(signal_id)

        labels: list[GroundTruthLabel] = []
        for practice_area, evidence_ids in practice_area_to_signals.items():
            label = GroundTruthLabel(
                company_id=company_id,
                labeling_run_id=run_id,
                label_type=LabelType.positive.value,
                practice_area=practice_area,
                horizon_days=horizon,
                signal_window_start=signal_window_start,
                signal_window_end=signal_window_end,
                evidence_signal_ids=evidence_ids,
                label_source="retrospective",
                confidence_score=DEFAULT_LABEL_CONFIDENCE,
                is_validated=False,
            )
            labels.append(label)

        log.info(
            "Positive labels generated",
            company_id=company_id,
            horizon=horizon,
            count=len(labels),
        )
        return labels

    async def run_batch(
        self,
        run_id: int,
        company_ids: list[int],
        db: AsyncSession,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        """
        Process a batch of companies and persist all positive labels.

        Returns summary dict: {companies_processed, positive_labels_created, errors}.
        """
        if now is None:
            now = datetime.now(tz=UTC)

        total_labels = 0
        errors = 0

        for company_id in company_ids:
            try:
                labels = await self.label_company(
                    company_id=company_id,
                    run_id=run_id,
                    now=now,
                    db=db,
                )
                for label in labels:
                    db.add(label)
                total_labels += len(labels)
            except Exception as exc:  # noqa: BLE001
                log.error(
                    "Error labeling company",
                    company_id=company_id,
                    error=str(exc),
                )
                errors += 1

        try:
            await db.flush()
        except Exception as exc:  # noqa: BLE001
            log.error("DB flush error in retrospective labeler", error=str(exc))
            await db.rollback()
            raise

        log.info(
            "Retrospective labeling batch complete",
            companies=len(company_ids),
            labels=total_labels,
            errors=errors,
        )
        return {
            "companies_processed": len(company_ids),
            "positive_labels_created": total_labels,
            "errors": errors,
        }

    async def get_all_company_ids(self, db: AsyncSession) -> list[int]:
        """Return all company IDs that have at least one signal_record."""
        try:
            stmt = text(
                """
                SELECT DISTINCT company_id
                FROM signal_records
                WHERE company_id IS NOT NULL
                ORDER BY company_id
                """
            )
            result = await db.execute(stmt)
            return [row[0] for row in result.fetchall()]
        except Exception as exc:  # noqa: BLE001
            log.error("Failed to fetch company IDs", error=str(exc))
            return []
