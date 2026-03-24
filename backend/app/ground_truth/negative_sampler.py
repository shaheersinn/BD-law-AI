"""
app/ground_truth/negative_sampler.py — Agent 017: Negative Sampler.

Finds companies that had signal activity but NO positive signal types
(no legal engagement events) within the observation window, and assigns
negative ground truth labels.

Sampling strategy:
  - Group eligible companies by sector
  - Sample up to MAX_NEGATIVE_SAMPLES_PER_SECTOR per sector
  - This prevents over-representation of large sectors in the training set
  - Horizon: uses the longest horizon (90 days) for negative sampling
    (if a company shows no legal signals in 90 days, it's a strong negative)
"""

from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ground_truth.constants import (
    DEFAULT_LABEL_CONFIDENCE,
    MAX_NEGATIVE_SAMPLES_PER_SECTOR,
    POSITIVE_SIGNAL_TYPES,
)
from app.models.ground_truth import GroundTruthLabel, LabelType

log = structlog.get_logger(__name__)

# Horizon used for negative sampling (longest, strongest negative signal)
NEGATIVE_SAMPLING_HORIZON: int = 90


class NegativeSampler:
    """
    Agent 017 — Negative Sampler.

    Identifies companies with signal history but no legal engagement events,
    then samples stratified negatives for ML training balance.
    """

    def __init__(self, seed: int = 42) -> None:
        self._rng = random.Random(seed)  # noqa: S311

    async def sample(
        self,
        run_id: int,
        db: AsyncSession,
        now: datetime | None = None,
        max_per_sector: int = MAX_NEGATIVE_SAMPLES_PER_SECTOR,
    ) -> dict[str, Any]:
        """
        Find and persist negative labels, stratified by sector.

        Returns summary dict: {negative_labels_created, sectors_sampled, errors}.
        """
        if now is None:
            now = datetime.now(tz=UTC)

        window_start = now - timedelta(days=NEGATIVE_SAMPLING_HORIZON * 2)
        window_end = now - timedelta(days=NEGATIVE_SAMPLING_HORIZON)

        # Step 1: find companies with signal activity but NO positive signals
        try:
            candidates = await self._find_negative_candidates(
                db=db,
                window_start=window_start,
                window_end=window_end,
            )
        except Exception as exc:  # noqa: BLE001
            log.error("Failed to find negative candidates", error=str(exc))
            return {"negative_labels_created": 0, "sectors_sampled": 0, "errors": 1}

        if not candidates:
            log.info("No negative candidates found")
            return {"negative_labels_created": 0, "sectors_sampled": 0, "errors": 0}

        # Step 2: group by sector, sample per-sector cap
        by_sector: dict[str, list[dict[str, Any]]] = {}
        for row in candidates:
            sector = row["sector"] or "Unknown"
            by_sector.setdefault(sector, []).append(row)

        # Step 3: sample and create labels
        labels: list[GroundTruthLabel] = []
        errors = 0

        for _sector, companies in by_sector.items():
            # Random sample up to max_per_sector
            sampled = self._rng.sample(companies, min(len(companies), max_per_sector))
            for company in sampled:
                try:
                    label = GroundTruthLabel(
                        company_id=company["company_id"],
                        labeling_run_id=run_id,
                        label_type=LabelType.negative.value,
                        practice_area=None,  # generic negative — no specific PA
                        horizon_days=NEGATIVE_SAMPLING_HORIZON,
                        signal_window_start=window_start,
                        signal_window_end=window_end,
                        evidence_signal_ids=company.get("signal_ids"),
                        label_source="retrospective",
                        confidence_score=DEFAULT_LABEL_CONFIDENCE,
                        is_validated=False,
                    )
                    db.add(label)
                    labels.append(label)
                except Exception as exc:  # noqa: BLE001
                    log.error(
                        "Error creating negative label",
                        company_id=company["company_id"],
                        error=str(exc),
                    )
                    errors += 1

        try:
            await db.flush()
        except Exception as exc:  # noqa: BLE001
            log.error("DB flush error in negative sampler", error=str(exc))
            await db.rollback()
            raise

        log.info(
            "Negative sampling complete",
            sectors=len(by_sector),
            candidates=len(candidates),
            labels=len(labels),
            errors=errors,
        )
        return {
            "negative_labels_created": len(labels),
            "sectors_sampled": len(by_sector),
            "errors": errors,
        }

    async def _find_negative_candidates(
        self,
        db: AsyncSession,
        window_start: datetime,
        window_end: datetime,
    ) -> list[dict[str, Any]]:
        """
        Return companies that:
        - Have signal_records in [window_start, window_end]
        - Have NO positive signal types in [window_start, window_end]
        - Have already been labeled positive (excluded from negatives)
        """
        stmt = text(
            """
            WITH companies_with_signals AS (
                SELECT
                    sr.company_id,
                    c.sector,
                    ARRAY_AGG(sr.id ORDER BY sr.scraped_at) AS signal_ids
                FROM signal_records sr
                JOIN companies c ON c.id = sr.company_id
                WHERE sr.company_id IS NOT NULL
                  AND sr.scraped_at >= :window_start
                  AND sr.scraped_at < :window_end
                GROUP BY sr.company_id, c.sector
            ),
            companies_with_positive AS (
                SELECT DISTINCT company_id
                FROM signal_records
                WHERE company_id IS NOT NULL
                  AND signal_type = ANY(:positive_types)
                  AND scraped_at >= :window_start
                  AND scraped_at < :window_end
            ),
            already_labeled_positive AS (
                SELECT DISTINCT company_id
                FROM ground_truth_labels
                WHERE label_type = 'positive'
            )
            SELECT
                cws.company_id,
                cws.sector,
                cws.signal_ids
            FROM companies_with_signals cws
            WHERE cws.company_id NOT IN (
                SELECT company_id FROM companies_with_positive
            )
            AND cws.company_id NOT IN (
                SELECT company_id FROM already_labeled_positive
            )
            ORDER BY cws.company_id
            """
        )
        try:
            result = await db.execute(
                stmt,
                {
                    "positive_types": list(POSITIVE_SIGNAL_TYPES),
                    "window_start": window_start,
                    "window_end": window_end,
                },
            )
            rows = result.fetchall()
            return [
                {
                    "company_id": row[0],
                    "sector": row[1],
                    "signal_ids": list(row[2]) if row[2] else [],
                }
                for row in rows
            ]
        except Exception as exc:  # noqa: BLE001
            log.error("SQL error finding negative candidates", error=str(exc))
            raise
