"""
app/training/curator.py — Agent 019: Training Data Curator.

Assembles, deduplicates, and exports the final training dataset for Phase 6 ML training.

Pipeline:
  1. Fetch all ground_truth_labels meeting the confidence threshold
  2. Deduplicate: keep highest-confidence label per (company_id, practice_area, horizon_days)
  3. Export as Parquet or CSV to CURATOR_EXPORT_DIR
  4. Create a TrainingDataset record tracking the export

The exported dataset format is the input to Phase 6 XGBoost/LightGBM trainers.
Columns: company_id, practice_area, horizon_days, label_type, label_int,
         confidence_score, label_source
"""

from __future__ import annotations

import csv
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.training import DatasetStatus, TrainingDataset

log = structlog.get_logger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

CURATOR_MIN_CONFIDENCE: float = 0.70
CURATOR_EXPORT_DIR: str = "data/training"  # relative to working directory

# Integer encoding for label types (for ML frameworks)
LABEL_INT_MAP: dict[str, int] = {
    "positive": 1,
    "negative": 0,
    "uncertain": -1,
}


# ── Training Data Curator ─────────────────────────────────────────────────────


class TrainingDataCurator:
    """
    Agent 019 — Training Data Curator.

    Reads all ground_truth_labels (both retrospective from Phase 3 and
    pseudo-labels from Phase 4), applies quality filtering and deduplication,
    and exports a clean training dataset.
    """

    def __init__(self, export_dir: str | None = None) -> None:
        self._export_dir = Path(export_dir or CURATOR_EXPORT_DIR)

    async def curate(
        self,
        db: AsyncSession,
        min_confidence: float = CURATOR_MIN_CONFIDENCE,
        export_format: str = "parquet",
        practice_areas: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Run the full curation pipeline.

        Args:
            db: async DB session
            min_confidence: minimum confidence_score to include (default 0.70)
            export_format: "parquet" or "csv"
            practice_areas: filter to specific practice areas (None = all 34)

        Returns:
            Summary dict with label counts, export path, dataset id.
        """
        dataset = TrainingDataset(
            status=DatasetStatus.running.value,
            min_confidence=min_confidence,
            export_format=export_format,
            practice_areas=practice_areas,
        )
        db.add(dataset)
        await db.flush()  # get dataset.id

        try:
            rows = await self._fetch_labels(
                db=db,
                min_confidence=min_confidence,
                practice_areas=practice_areas,
            )

            deduplicated = self._deduplicate(rows)
            export_path = self._export(deduplicated, fmt=export_format)

            pos = sum(1 for r in deduplicated if r["label_type"] == "positive")
            neg = sum(1 for r in deduplicated if r["label_type"] == "negative")
            unc = sum(1 for r in deduplicated if r["label_type"] == "uncertain")

            dataset.status = DatasetStatus.complete.value
            dataset.label_count = len(deduplicated)
            dataset.positive_count = pos
            dataset.negative_count = neg
            dataset.uncertain_count = unc
            dataset.export_path = export_path
            dataset.horizons = (
                sorted({r["horizon_days"] for r in deduplicated}) if deduplicated else []
            )
            dataset.completed_at = datetime.now(tz=UTC)
            await db.flush()

            summary = {
                "dataset_id": dataset.id,
                "label_count": len(deduplicated),
                "positive_count": pos,
                "negative_count": neg,
                "uncertain_count": unc,
                "export_path": export_path,
                "export_format": export_format,
                "min_confidence": min_confidence,
            }
            log.info("Training data curation complete", **summary)
            return summary

        except Exception as exc:  # noqa: BLE001
            log.error("Training data curation failed", dataset_id=dataset.id, error=str(exc))
            dataset.status = DatasetStatus.failed.value
            dataset.error_message = str(exc)
            dataset.completed_at = datetime.now(tz=UTC)
            await db.flush()
            raise

    async def _fetch_labels(
        self,
        db: AsyncSession,
        min_confidence: float,
        practice_areas: list[str] | None,
    ) -> list[dict[str, Any]]:
        """Fetch qualifying ground_truth_labels with company info."""
        params: dict[str, Any] = {"min_confidence": min_confidence}
        if practice_areas:
            params["practice_areas"] = practice_areas

        # Two pre-defined queries: one with practice_area filter, one without.
        # No f-string SQL construction — the filter value uses parameterized bind.
        _SQL_BASE = """
            SELECT gtl.company_id, gtl.practice_area, gtl.horizon_days,
                   gtl.label_type, gtl.confidence_score, gtl.label_source
            FROM ground_truth_labels gtl
            WHERE (gtl.confidence_score IS NULL
                   OR gtl.confidence_score >= :min_confidence)
            ORDER BY gtl.company_id, gtl.practice_area,
                     gtl.horizon_days, gtl.confidence_score DESC
        """
        _SQL_WITH_PA = """
            SELECT gtl.company_id, gtl.practice_area, gtl.horizon_days,
                   gtl.label_type, gtl.confidence_score, gtl.label_source
            FROM ground_truth_labels gtl
            WHERE (gtl.confidence_score IS NULL
                   OR gtl.confidence_score >= :min_confidence)
              AND gtl.practice_area = ANY(:practice_areas)
            ORDER BY gtl.company_id, gtl.practice_area,
                     gtl.horizon_days, gtl.confidence_score DESC
        """
        stmt = text(_SQL_WITH_PA if practice_areas else _SQL_BASE)
        try:
            result = await db.execute(stmt, params)
            rows = result.fetchall()
            return [
                {
                    "company_id": row[0],
                    "practice_area": row[1],
                    "horizon_days": row[2],
                    "label_type": row[3],
                    "confidence_score": row[4] if row[4] is not None else 1.0,
                    "label_source": row[5],
                }
                for row in rows
            ]
        except Exception as exc:  # noqa: BLE001
            log.error("SQL error fetching labels for curation", error=str(exc))
            raise

    def _deduplicate(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Deduplicate: keep highest-confidence label per (company_id, practice_area, horizon_days).

        When multiple labels exist for the same key, we keep the one with the
        highest confidence_score (retrospective labels typically score higher).
        """
        seen: dict[tuple[int, str | None, int], dict[str, Any]] = {}

        for row in rows:
            key = (row["company_id"], row["practice_area"], row["horizon_days"])
            existing = seen.get(key)
            if existing is None or row["confidence_score"] > existing["confidence_score"]:
                seen[key] = row

        result = list(seen.values())

        # Add integer label column for ML frameworks
        for row in result:
            row["label_int"] = LABEL_INT_MAP.get(row["label_type"], -1)

        return result

    def _export(self, rows: list[dict[str, Any]], fmt: str) -> str:
        """
        Write rows to a timestamped file. Returns the file path.

        Supports: "parquet" (preferred for ML) and "csv" (fallback).
        Falls back to CSV if pyarrow/pandas not available.
        """
        self._export_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")
        filename = f"training_{timestamp}.{fmt}"
        filepath = str(self._export_dir / filename)

        if fmt == "parquet":
            try:
                self._write_parquet(rows, filepath)
                return filepath
            except ImportError:
                log.warning("pyarrow/pandas not installed — falling back to CSV")
                filepath = filepath.replace(".parquet", ".csv")
                self._write_csv(rows, filepath)
                return filepath
        else:
            self._write_csv(rows, filepath)
            return filepath

    def _write_csv(self, rows: list[dict[str, Any]], path: str) -> None:
        """Write rows to CSV."""
        if not rows:
            with open(path, "w", newline="") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=[
                        "company_id",
                        "practice_area",
                        "horizon_days",
                        "label_type",
                        "label_int",
                        "confidence_score",
                        "label_source",
                    ],
                )
                writer.writeheader()
            return

        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    def _write_parquet(self, rows: list[dict[str, Any]], path: str) -> None:
        """Write rows to Parquet using pandas + pyarrow."""
        import pandas as pd  # type: ignore[import-not-found]

        df = (
            pd.DataFrame(rows)
            if rows
            else pd.DataFrame(
                columns=[
                    "company_id",
                    "practice_area",
                    "horizon_days",
                    "label_type",
                    "label_int",
                    "confidence_score",
                    "label_source",
                ]
            )
        )
        df.to_parquet(path, index=False)
