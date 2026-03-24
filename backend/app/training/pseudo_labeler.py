"""
app/training/pseudo_labeler.py — Agent 018: Pseudo-Label Quality.

Queries unlabeled signal_records, sends them to Groq for classification,
and persists results as GroundTruthLabel rows with label_source='pseudo_label'.

Sampling strategy:
  - Only processes signal_records that have signal_text (need text for classification)
  - Only processes is_resolved=True records (company_id is known)
  - Excludes signals already pseudo-labeled in a prior run
  - Caps per run at PSEUDO_LABEL_MAX_SIGNALS_PER_RUN to control Groq costs
  - Rejects results with confidence < PSEUDO_LABEL_CONFIDENCE_FLOOR
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ground_truth.constants import PRACTICE_AREAS
from app.models.ground_truth import GroundTruthLabel, LabelSource, LabelType
from app.training.groq_client import ClassificationResult, GroqClient, SignalInput

log = structlog.get_logger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

PSEUDO_LABEL_CONFIDENCE_FLOOR: float = 0.60  # reject results below this
PSEUDO_LABEL_MAX_SIGNALS_PER_RUN: int = 5000  # cost control
PSEUDO_LABEL_HORIZON: int = 90  # use longest horizon for pseudo-labels

# Canonical practice area set for validation (lowercase → canonical)
_PA_LOWER: dict[str, str] = {pa.lower(): pa for pa in PRACTICE_AREAS}


# ── Pseudo Labeler ────────────────────────────────────────────────────────────


class PseudoLabeler:
    """
    Agent 018 — Pseudo-Label Quality.

    Uses Groq LLM to classify unlabeled signal records and create
    GroundTruthLabel records for Phase 6 ML training.
    """

    def __init__(self, groq_client: GroqClient | None = None) -> None:
        self._groq = groq_client or GroqClient()

    async def run(
        self,
        run_id: int,
        db: AsyncSession,
        now: datetime | None = None,
        max_signals: int = PSEUDO_LABEL_MAX_SIGNALS_PER_RUN,
    ) -> dict[str, Any]:
        """
        Find unlabeled signals, classify via Groq, persist labels.

        Returns summary: {pseudo_labels_created, signals_processed,
                          rejected_low_confidence, errors}
        """
        if now is None:
            now = datetime.now(tz=UTC)

        # Step 1: fetch candidate signals
        try:
            signals_data = await self._get_unlabeled_signals(db=db, limit=max_signals)
        except Exception as exc:  # noqa: BLE001
            log.error("Failed to fetch unlabeled signals", error=str(exc))
            return {
                "pseudo_labels_created": 0,
                "signals_processed": 0,
                "rejected_low_confidence": 0,
                "errors": 1,
            }

        if not signals_data:
            log.info("No unlabeled signals found")
            return {
                "pseudo_labels_created": 0,
                "signals_processed": 0,
                "rejected_low_confidence": 0,
                "errors": 0,
            }

        inputs = [
            SignalInput(
                signal_id=row["id"],
                signal_type=row["signal_type"],
                signal_text=row.get("signal_text"),
                company_id=row["company_id"],
                practice_area_hint=row.get("practice_area_hints"),
            )
            for row in signals_data
        ]

        log.info("Starting pseudo-label classification", signal_count=len(inputs), run_id=run_id)

        # Step 2: classify via Groq
        try:
            results = await self._groq.classify_signals(inputs)
        except Exception as exc:  # noqa: BLE001
            log.error("Groq classification failed", error=str(exc))
            return {
                "pseudo_labels_created": 0,
                "signals_processed": len(inputs),
                "rejected_low_confidence": 0,
                "errors": 1,
            }

        # Step 3: persist valid labels
        signal_to_company = {row["id"]: row["company_id"] for row in signals_data}
        window_start = now - timedelta(days=PSEUDO_LABEL_HORIZON * 2)
        window_end = now - timedelta(days=PSEUDO_LABEL_HORIZON)

        labels_created = 0
        rejected = 0
        errors = 0

        for result in results:
            if result.confidence < PSEUDO_LABEL_CONFIDENCE_FLOOR:
                rejected += 1
                continue

            company_id = signal_to_company.get(result.signal_id)
            if company_id is None:
                errors += 1
                continue

            try:
                created = self._create_labels(
                    result=result,
                    company_id=company_id,
                    run_id=run_id,
                    window_start=window_start,
                    window_end=window_end,
                    db=db,
                )
                labels_created += created
            except Exception as exc:  # noqa: BLE001
                log.error(
                    "Error creating pseudo-label",
                    signal_id=result.signal_id,
                    error=str(exc),
                )
                errors += 1

        try:
            await db.flush()
        except Exception as exc:  # noqa: BLE001
            log.error("DB flush error in pseudo-labeler", error=str(exc))
            await db.rollback()
            raise

        log.info(
            "Pseudo-labeling complete",
            signals_processed=len(results),
            labels_created=labels_created,
            rejected=rejected,
            errors=errors,
            run_id=run_id,
        )
        return {
            "pseudo_labels_created": labels_created,
            "signals_processed": len(results),
            "rejected_low_confidence": rejected,
            "errors": errors,
        }

    def _create_labels(
        self,
        result: ClassificationResult,
        company_id: int,
        run_id: int,
        window_start: datetime,
        window_end: datetime,
        db: AsyncSession,
    ) -> int:
        """
        Persist GroundTruthLabel objects for a classification result.

        One label per practice area (or one generic label for negatives/uncertain).
        Returns count of labels created.
        """
        # label_type is already validated as "positive"/"negative"/"uncertain"
        label_type_value = result.label_type

        resolved_pas = self._resolve_practice_areas(result.practice_areas)

        if label_type_value == LabelType.negative or not resolved_pas:
            # Single label with no practice area (generic)
            label = GroundTruthLabel(
                company_id=company_id,
                labeling_run_id=run_id,
                label_type=label_type_value,
                practice_area=None,
                horizon_days=PSEUDO_LABEL_HORIZON,
                signal_window_start=window_start,
                signal_window_end=window_end,
                evidence_signal_ids=[result.signal_id],
                label_source=LabelSource.pseudo_label.value,
                confidence_score=result.confidence,
                is_validated=False,
            )
            db.add(label)
            return 1

        count = 0
        for pa in resolved_pas:
            label = GroundTruthLabel(
                company_id=company_id,
                labeling_run_id=run_id,
                label_type=label_type_value,
                practice_area=pa,
                horizon_days=PSEUDO_LABEL_HORIZON,
                signal_window_start=window_start,
                signal_window_end=window_end,
                evidence_signal_ids=[result.signal_id],
                label_source=LabelSource.pseudo_label.value,
                confidence_score=result.confidence,
                is_validated=False,
            )
            db.add(label)
            count += 1

        return count

    def _resolve_practice_areas(self, raw_pas: list[str]) -> list[str]:
        """
        Normalize LLM-returned practice area strings to canonical names.

        Matches case-insensitively against the 34 canonical practice areas.
        Unrecognized strings are silently dropped.
        """
        resolved: list[str] = []
        for raw in raw_pas:
            canonical = _PA_LOWER.get(raw.strip().lower())
            if canonical:
                resolved.append(canonical)
            else:
                log.debug("Unknown practice area from Groq — dropped", raw=raw)
        return resolved

    async def _get_unlabeled_signals(
        self,
        db: AsyncSession,
        limit: int,
    ) -> list[dict[str, Any]]:
        """
        Return signal_records not yet pseudo-labeled.

        Conditions:
        - is_resolved = TRUE (company_id is known)
        - signal_text IS NOT NULL (need text for classification)
        - NOT already in ground_truth_labels with label_source = 'pseudo_label'
          via evidence_signal_ids
        """
        stmt = text(
            """
            SELECT
                sr.id,
                sr.company_id,
                sr.signal_type,
                sr.signal_text,
                sr.practice_area_hints
            FROM signal_records sr
            WHERE sr.is_resolved = TRUE
              AND sr.signal_text IS NOT NULL
              AND sr.signal_text != ''
              AND NOT EXISTS (
                  SELECT 1
                  FROM ground_truth_labels gtl
                  WHERE gtl.label_source = 'pseudo_label'
                    AND gtl.evidence_signal_ids @> ARRAY[sr.id]
              )
            ORDER BY sr.scraped_at DESC
            LIMIT :limit
            """
        )
        try:
            result = await db.execute(stmt, {"limit": limit})
            rows = result.fetchall()
            return [
                {
                    "id": row[0],
                    "company_id": row[1],
                    "signal_type": row[2],
                    "signal_text": row[3],
                    "practice_area_hints": row[4],
                }
                for row in rows
            ]
        except Exception as exc:  # noqa: BLE001
            log.error("SQL error fetching unlabeled signals", error=str(exc))
            raise
