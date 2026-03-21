"""
app/ml/practice_classifier.py — Multi-label practice area classifier.

Phase 1 (day 0): Weighted vote from signal catalogue (no training data needed).
Phase 2 (after 6 months / 150+ labelled alerts): Trained GradientBoosting
  OneVsRest with confirmed alert labels replaces the weighted vote.
"""

import logging
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import f1_score
from sklearn.model_selection import cross_val_score
from sklearn.multiclass import OneVsRestClassifier
from sklearn.preprocessing import MultiLabelBinarizer

from app.config import get_settings
from app.ml.convergence import (
    PRACTICE_AREA_VOTES,
    ScoredSignal,
    classify_practice_area,
)

log = logging.getLogger(__name__)
settings = get_settings()

MODEL_PATH = Path(settings.models_dir) / "pa_classifier.pkl"
MLB_PATH = Path(settings.models_dir) / "pa_mlb.pkl"

SIGNAL_FEATURE_COLS = [
    "sedar_material_change", "sedar_confidentiality", "sedar_going_concern",
    "sedar_director_resign", "edgar_conf_treatment", "edgar_sc13d",
    "canlii_defendant", "canlii_plaintiff", "canlii_ccaa",
    "osc_enforcement", "competition_investigation", "fintrac_noncompliance",
    "job_gc_hire", "job_cco_urgent", "job_privacy_counsel", "job_ma_counsel",
    "jet_baystreet_2x", "satellite_parking_drop", "permit_environmental",
    "news_lawsuit", "news_investigation", "news_breach", "news_restructuring",
    "linkedin_gc_spike", "linkedin_exec_departure",
]


class PracticeAreaClassifier:
    """
    Unified classifier: trained model when available, vote-based fallback.
    """

    _instance: Optional["PracticeAreaClassifier"] = None

    def __init__(self) -> None:
        self._model: Optional[OneVsRestClassifier] = None
        self._mlb: Optional[MultiLabelBinarizer] = None

    @classmethod
    def get(cls) -> "PracticeAreaClassifier":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load(self) -> None:
        if MODEL_PATH.exists() and MLB_PATH.exists():
            self._model = joblib.load(MODEL_PATH)
            self._mlb = joblib.load(MLB_PATH)
            log.info("PA classifier loaded from %s", MODEL_PATH)

    def predict(
        self, signals: list[ScoredSignal]
    ) -> tuple[str, float, list[str]]:
        """
        Returns (primary_pa, confidence, all_predicted_pas).
        Tries trained model first, falls back to weighted vote.
        """
        if self._model is None:
            self._load()

        if self._model is not None and self._mlb is not None:
            try:
                features = _signals_to_features(signals)
                probs = self._model.predict_proba(features)
                predicted = self._mlb.inverse_transform(
                    (probs >= 0.40).astype(int)
                )
                all_pas = list(predicted[0]) if predicted else []

                # Confidence = max probability across predicted classes
                max_prob = float(np.max(probs)) if probs.size else 0.0
                primary = all_pas[0] if all_pas else "General / Unknown"
                return primary, round(max_prob, 3), all_pas
            except Exception as e:
                log.error("PA classifier error: %s", e)

        # Fallback: weighted vote
        primary, conf = classify_practice_area(signals)
        return primary, conf, [primary] if primary != "General / Unknown" else []

    def is_trained(self) -> bool:
        return MODEL_PATH.exists() and MLB_PATH.exists()


def _signals_to_features(signals: list[ScoredSignal]) -> np.ndarray:
    """Convert a list of ScoredSignal to the fixed feature vector."""
    fired = {s.signal_type for s in signals}
    row = [1 if col in fired else 0 for col in SIGNAL_FEATURE_COLS]
    return np.array([row])


def train(csv_path: str) -> dict:
    """
    Train multi-label practice area classifier from confirmed alerts.

    CSV columns: one binary column per SIGNAL_FEATURE_COLS entry +
                 'practice_areas' column (Python list serialised as string).
    """
    df = pd.read_csv(csv_path)
    X = df[SIGNAL_FEATURE_COLS].fillna(0)

    # Parse stringified lists like "['Corporate / M&A', 'Securities']"
    import ast
    y_raw = df["practice_areas"].apply(
        lambda v: ast.literal_eval(v) if isinstance(v, str) else v
    )

    mlb = MultiLabelBinarizer()
    y = mlb.fit_transform(y_raw)

    model = OneVsRestClassifier(
        GradientBoostingClassifier(
            n_estimators=200, max_depth=3, learning_rate=0.05, random_state=42
        )
    )

    scores = cross_val_score(model, X, y, cv=5, scoring="f1_macro")
    log.info("PA classifier CV F1: %.3f ± %.3f", scores.mean(), scores.std())

    model.fit(X, y)

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    joblib.dump(mlb, MLB_PATH)
    PracticeAreaClassifier._instance = None

    return {
        "rows": len(df),
        "classes": list(mlb.classes_),
        "cv_f1_mean": round(scores.mean(), 3),
        "cv_f1_std": round(scores.std(), 3),
    }
