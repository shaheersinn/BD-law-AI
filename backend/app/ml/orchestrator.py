"""
app/ml/orchestrator.py — Model orchestrator.

Selects the best scoring model per practice area per inference call.
Decision: use TransformerScorer only if it beats BayesianEngine by
≥ ORCHESTRATOR_F1_THRESHOLD on holdout F1.

Model registry is stored in PostgreSQL model_registry table and cached
in Redis for fast startup. Refreshed every 6 hours by Agent 023.

Usage:
    orchestrator = MandateOrchestrator()
    await orchestrator.load()
    result = orchestrator.score(company_id, features, sequences)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from app.ml.bayesian_engine import (
    ORCHESTRATOR_F1_THRESHOLD,
    PRACTICE_AREAS,
    BayesianEngine,
    HorizonScores,
    load_all_engines,
)

try:
    from app.ml.transformer_scorer import TransformerScorer as TransformerScorer

    _TORCH_AVAILABLE = True
except ImportError:
    _TORCH_AVAILABLE = False
    TransformerScorer = None  # type: ignore[assignment,misc]

log = logging.getLogger(__name__)


# ── Data classes ───────────────────────────────────────────────────────────────


@dataclass
class ModelSelection:
    """Which model is active for a practice area."""

    practice_area: str
    active_model: str  # "bayesian" or "transformer"
    bayesian_f1: float
    transformer_f1: float
    reason: str  # Why this model was selected


@dataclass
class CompanyScoreMatrix:
    """
    34 × 3 mandate probability matrix for a single company.
    The primary output of ORACLE.
    """

    company_id: int
    scores: dict[str, dict[int, float]]  # {practice_area: {30: 0.xx, 60: 0.xx, 90: 0.xx}}
    model_versions: dict[str, str]  # {practice_area: "bayesian_v3" or "transformer_v1"}
    velocity_score: float
    anomaly_score: float
    confidence_low: float
    confidence_high: float
    top_signals: list[dict[str, Any]]
    scored_at: str


# ── Orchestrator ───────────────────────────────────────────────────────────────


class MandateOrchestrator:
    """
    Routes each practice area's scoring to the best available model.

    BayesianEngine is the default — works from day 1.
    TransformerScorer takes over a practice area only when it proves
    superior on held-out data (≥ F1_THRESHOLD improvement).
    """

    def __init__(self) -> None:
        self._bayesian_engines: dict[str, BayesianEngine] = {}
        self._transformer_scorers: dict[str, TransformerScorer] = {}
        self._selections: dict[str, ModelSelection] = {}
        self._loaded = False

    def load(self, registry: list[dict[str, Any]] | None = None) -> None:
        """
        Load all engines and apply model registry decisions.

        Args:
            registry: List of model_registry rows from PostgreSQL.
                      If None, defaults all practice areas to bayesian.
        """
        # Load all Bayesian engines
        load_all_engines()
        from app.ml.bayesian_engine import _LOADED_ENGINES

        self._bayesian_engines = _LOADED_ENGINES.copy()

        # Load Transformer scorers (only for practice areas where they're active)
        if registry:
            transformer_active = {
                row["practice_area"] for row in registry if row.get("active_model") == "transformer"
            }
        else:
            transformer_active = set()

        for pa in transformer_active:
            try:
                if not _TORCH_AVAILABLE or TransformerScorer is None:
                    log.warning("torch not available — TransformerScorer disabled for %s", pa)
                    continue
                scorer = TransformerScorer(pa)
                scorer.load()
                if scorer._loaded:
                    self._transformer_scorers[pa] = scorer
                else:
                    log.warning("TransformerScorer %s failed to load — defaulting to Bayesian", pa)
            except Exception:
                log.exception("TransformerScorer %s load error", pa)

        # Build model selection map
        self._selections = {}
        registry_by_pa: dict[str, dict[str, Any]] = {}
        if registry:
            for row in registry:
                pa = row.get("practice_area", "")
                if pa:
                    registry_by_pa[pa] = row

        for pa in PRACTICE_AREAS:
            row = registry_by_pa.get(pa, {})
            bayesian_f1 = row.get("bayesian_f1", 0.0)
            transformer_f1 = row.get("transformer_f1", 0.0)

            use_transformer = (
                pa in self._transformer_scorers
                and transformer_f1 > bayesian_f1 + ORCHESTRATOR_F1_THRESHOLD
            )

            if use_transformer:
                reason = (
                    f"Transformer F1={transformer_f1:.3f} beats "
                    f"Bayesian F1={bayesian_f1:.3f} by "
                    f"{transformer_f1 - bayesian_f1:.3f} > threshold {ORCHESTRATOR_F1_THRESHOLD}"
                )
                active = "transformer"
            else:
                if pa in self._transformer_scorers and transformer_f1 > 0:
                    delta = transformer_f1 - bayesian_f1
                    reason = (
                        f"Bayesian retained: transformer F1 improvement "
                        f"{delta:.3f} < threshold {ORCHESTRATOR_F1_THRESHOLD}"
                    )
                else:
                    reason = "Bayesian default (no transformer trained yet)"
                active = "bayesian"

            self._selections[pa] = ModelSelection(
                practice_area=pa,
                active_model=active,
                bayesian_f1=bayesian_f1,
                transformer_f1=transformer_f1,
                reason=reason,
            )

        self._loaded = True
        transformer_count = sum(
            1 for s in self._selections.values() if s.active_model == "transformer"
        )
        log.info(
            "Orchestrator loaded: %d practice areas, %d using transformer, %d using bayesian",
            len(PRACTICE_AREAS),
            transformer_count,
            len(PRACTICE_AREAS) - transformer_count,
        )

    def score_company(
        self,
        features: dict[str, float],
        sequences: dict[str, list[dict[str, float]]] | None = None,
    ) -> dict[str, HorizonScores]:
        """
        Score a single company across all 34 practice areas.

        Args:
            features: Flat feature dict (FEATURE_COLUMNS keys → float values).
            sequences: Per-practice-area 30-day feature history for transformer.
                       If None, transformer scoring falls back to bayesian.
        Returns:
            dict: {practice_area → HorizonScores}
        """
        if not self._loaded:
            raise RuntimeError("Orchestrator not loaded. Call .load() first.")

        results: dict[str, HorizonScores] = {}

        for pa in PRACTICE_AREAS:
            selection = self._selections.get(pa)
            if selection is None:
                selection = ModelSelection(pa, "bayesian", 0.0, 0.0, "default")

            if selection.active_model == "transformer" and sequences is not None:
                seq = sequences.get(pa)
                if seq and pa in self._transformer_scorers:
                    try:
                        scorer = self._transformer_scorers[pa]
                        scores = scorer.score(seq)
                        results[pa] = HorizonScores(
                            practice_area=pa,
                            score_30d=scores[30],
                            score_60d=scores[60],
                            score_90d=scores[90],
                            model_version=f"transformer_{scorer._model_version}",
                            inference_ms=0.0,
                        )
                        continue
                    except Exception:
                        log.exception("TransformerScorer %s failed, falling back to Bayesian", pa)

            # Bayesian fallback (or primary)
            engine = self._bayesian_engines.get(pa)
            if engine and engine._loaded:
                try:
                    results[pa] = engine.score(features)
                except Exception:
                    log.exception("BayesianEngine %s failed", pa)
                    results[pa] = _zero_score(pa)
            else:
                results[pa] = _zero_score(pa)

        return results

    def get_selection_report(self) -> list[dict[str, Any]]:
        """Return current model selection for each practice area (for monitoring)."""
        return [
            {
                "practice_area": s.practice_area,
                "active_model": s.active_model,
                "bayesian_f1": s.bayesian_f1,
                "transformer_f1": s.transformer_f1,
                "reason": s.reason,
            }
            for s in self._selections.values()
        ]

    def update_from_registry(self, registry: list[dict[str, Any]]) -> None:
        """
        Hot-reload model selections from updated registry data.
        Called by Agent 023 after retraining completes.
        """
        self.load(registry=registry)
        log.info("Orchestrator selection map reloaded from registry")


# ── Module-level singleton ─────────────────────────────────────────────────────

_ORCHESTRATOR: MandateOrchestrator | None = None


def get_orchestrator() -> MandateOrchestrator:
    """Return module-level orchestrator singleton."""
    global _ORCHESTRATOR
    if _ORCHESTRATOR is None:
        _ORCHESTRATOR = MandateOrchestrator()
    return _ORCHESTRATOR


# ── Helpers ────────────────────────────────────────────────────────────────────


def _zero_score(practice_area: str) -> HorizonScores:
    """Return zero scores — used when model is unavailable."""
    return HorizonScores(
        practice_area=practice_area,
        score_30d=0.0,
        score_60d=0.0,
        score_90d=0.0,
        model_version="unavailable",
        inference_ms=0.0,
    )
