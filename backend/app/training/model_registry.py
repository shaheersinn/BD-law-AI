"""
app/training/model_registry.py — Model registry management.

Records training results and active model selection per practice area.
Persists to PostgreSQL model_registry table.
Read by Orchestrator at startup and refreshed by Agent 023 post-training.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)


class ModelRegistry:
    """
    In-memory registry populated during training, flushed to PostgreSQL at end.
    """

    def __init__(self) -> None:
        self._records: list[dict[str, Any]] = []

    def record(
        self,
        practice_area: str,
        bayesian_f1: float,
        transformer_f1: float,
        active_model: str,
        bayesian_results: list[Any],  # list[TrainingResult]
    ) -> None:
        """Record training outcome for a practice area."""
        now = datetime.now(tz=UTC).isoformat()

        # Best model metadata from 30d horizon result
        best_30 = next(
            (r for r in bayesian_results if r.horizon == 30),
            None,
        )

        self._records.append(
            {
                "practice_area": practice_area,
                "active_model": active_model,
                "bayesian_f1": bayesian_f1,
                "transformer_f1": transformer_f1,
                "bayesian_version": best_30.artifact_path if best_30 else "",
                "n_train": best_30.n_train if best_30 else 0,
                "n_holdout": best_30.n_holdout if best_30 else 0,
                "scale_pos_weight": best_30.scale_pos_weight if best_30 else 5.0,
                "top_features": _top_features_json(best_30) if best_30 else "{}",
                "trained_at": now,
                "is_active": True,
            }
        )

    async def flush_to_db(self, db: AsyncSession) -> None:
        """Upsert all registry records to PostgreSQL model_registry table."""
        if not self._records:
            log.warning("ModelRegistry: no records to flush")
            return

        for rec in self._records:
            try:
                await db.execute(
                    text("""
                        INSERT INTO model_registry (
                            practice_area, active_model, bayesian_f1, transformer_f1,
                            bayesian_version, n_train, n_holdout, scale_pos_weight,
                            top_features, trained_at, is_active
                        ) VALUES (
                            :practice_area, :active_model, :bayesian_f1, :transformer_f1,
                            :bayesian_version, :n_train, :n_holdout, :scale_pos_weight,
                            :top_features::jsonb, :trained_at, :is_active
                        )
                        ON CONFLICT (practice_area)
                        DO UPDATE SET
                            active_model = EXCLUDED.active_model,
                            bayesian_f1 = EXCLUDED.bayesian_f1,
                            transformer_f1 = EXCLUDED.transformer_f1,
                            bayesian_version = EXCLUDED.bayesian_version,
                            n_train = EXCLUDED.n_train,
                            n_holdout = EXCLUDED.n_holdout,
                            scale_pos_weight = EXCLUDED.scale_pos_weight,
                            top_features = EXCLUDED.top_features,
                            trained_at = EXCLUDED.trained_at,
                            is_active = EXCLUDED.is_active
                    """),
                    rec,
                )
            except Exception:
                log.exception(
                    "Failed to flush model_registry record for %s", rec.get("practice_area")
                )

        await db.commit()
        log.info("ModelRegistry: flushed %d records to PostgreSQL", len(self._records))


def _top_features_json(result: Any) -> str:
    """Extract top 10 feature importances as JSON string."""
    import json

    if not result or not result.feature_importances:
        return "{}"
    top10 = dict(sorted(result.feature_importances.items(), key=lambda x: x[1], reverse=True)[:10])
    return json.dumps({k: round(v, 4) for k, v in top10.items()})


async def load_registry_from_db(db: AsyncSession) -> list[dict[str, Any]]:
    """
    Load all active model_registry records from PostgreSQL.
    Called by Orchestrator.load() at API startup.
    """
    try:
        result = await db.execute(
            text("""
                SELECT practice_area, active_model, bayesian_f1, transformer_f1,
                       bayesian_version, n_train, trained_at
                FROM model_registry
                WHERE is_active = true
            """)
        )
        rows = result.fetchall()
        return [
            {
                "practice_area": row[0],
                "active_model": row[1],
                "bayesian_f1": float(row[2] or 0),
                "transformer_f1": float(row[3] or 0),
                "bayesian_version": row[4],
                "n_train": row[5],
                "trained_at": row[6],
            }
            for row in rows
        ]
    except Exception:
        log.exception("Failed to load model registry from DB")
        return []
