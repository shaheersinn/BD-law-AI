"""app/ml/convergence — Bayesian signal convergence scoring engine."""

from __future__ import annotations

from app.ml.convergence.engine import (
    PRACTICE_AREA_VOTES,
    SIGNAL_CATEGORIES,
    SIGNAL_WEIGHTS,
    ScoredSignal,
    classify_practice_area,
    convergence_score,
    crossed_threshold,
    threshold_label,
)

__all__ = [
    "SIGNAL_WEIGHTS",
    "SIGNAL_CATEGORIES",
    "PRACTICE_AREA_VOTES",
    "ScoredSignal",
    "convergence_score",
    "classify_practice_area",
    "threshold_label",
    "crossed_threshold",
]
