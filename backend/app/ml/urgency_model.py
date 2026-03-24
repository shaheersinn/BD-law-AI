"""
app/ml/urgency_model.py — LightGBM Legal Urgency Index (0-100).

Scores every company in the prospect database on how urgently they need
legal counsel in the next 90 days. An 80+ score means call this week.

Key design choices:
  - SMOTE to handle class imbalance (mandates are rare)
  - Isotonic calibration for large datasets, Platt (sigmoid) for small
  - PR-AUC as the primary evaluation metric (correct for imbalanced classes)
  - Auto-retrains every 2 weeks via Celery when ≥50 new labels arrive
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
import pandas as pd
from imblearn.over_sampling import SMOTE
from lightgbm import LGBMClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import average_precision_score, precision_recall_curve
from sklearn.model_selection import StratifiedKFold

from app.config import get_settings

log = logging.getLogger(__name__)
settings = get_settings()

MODEL_PATH = Path(settings.models_dir) / "urgency_model.pkl"

FEATURE_COLS = [
    # Filing signals (count in last 90 days)
    "sedar_material_changes_90d",
    "sedar_confidentiality_90d",
    "edgar_conf_treatment_90d",
    "canlii_filings_90d",
    # Velocity (rate of change vs prior period)
    "sedar_velocity",
    "news_mention_velocity",
    # Job postings
    "legal_job_postings_90d",
    "cco_job_posted",  # binary
    "gc_job_posted",  # binary
    # People / LinkedIn
    "gc_linkedin_spike",  # activity multiplier vs baseline
    "exec_departures_90d",
    # Physical
    "jet_baystreet_trips_90d",
    "has_permit_filing",  # binary
    # Industry baseline
    "industry_mandate_rate",  # historical: what % of companies in this sector got mandated
    # Time
    "quarter",  # 1-4 (Q4 is peak M&A season)
    "days_since_last_signal",
]


@dataclass
class ProspectFeatures:
    sedar_material_changes_90d: int = 0
    sedar_confidentiality_90d: int = 0
    edgar_conf_treatment_90d: int = 0
    canlii_filings_90d: int = 0
    sedar_velocity: float = 0.0
    news_mention_velocity: float = 0.0
    legal_job_postings_90d: int = 0
    cco_job_posted: int = 0
    gc_job_posted: int = 0
    gc_linkedin_spike: float = 1.0
    exec_departures_90d: int = 0
    jet_baystreet_trips_90d: int = 0
    has_permit_filing: int = 0
    industry_mandate_rate: float = 0.12
    quarter: int = 1
    days_since_last_signal: int = 30

    def to_array(self) -> np.ndarray:
        return np.array([[getattr(self, c) for c in FEATURE_COLS]])


class UrgencyModel:
    """LightGBM Legal Urgency Index scorer."""

    _instance: Optional["UrgencyModel"] = None

    def __init__(self) -> None:
        self._model: CalibratedClassifierCV | None = None

    @classmethod
    def get(cls) -> "UrgencyModel":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load(self) -> None:
        if MODEL_PATH.exists():
            self._model = joblib.load(MODEL_PATH)
            log.info("Urgency model loaded from %s", MODEL_PATH)
        else:
            log.warning("No urgency model at %s — using heuristic fallback", MODEL_PATH)

    def score(self, features: ProspectFeatures) -> int:
        """Return 0-100 urgency score."""
        if self._model is None:
            self._load()

        if self._model is not None:
            try:
                prob = self._model.predict_proba(features.to_array())[0][1]
                return int(round(prob * 100))
            except Exception as e:
                log.error("Urgency model inference error: %s", e)

        return _heuristic_urgency(features)


def _heuristic_urgency(f: ProspectFeatures) -> int:
    score = 5.0
    score += f.sedar_material_changes_90d * 22
    score += f.sedar_confidentiality_90d * 28
    score += f.edgar_conf_treatment_90d * 25
    score += f.canlii_filings_90d * 18
    score += f.legal_job_postings_90d * 10
    score += f.cco_job_posted * 25
    score += f.gc_job_posted * 20
    score += max(0, (f.gc_linkedin_spike - 1.5)) * 20
    score += f.exec_departures_90d * 12
    score += f.jet_baystreet_trips_90d * 22
    score += f.has_permit_filing * 18
    if f.quarter == 4:
        score *= 1.1
    return min(int(score), 99)


def find_optimal_threshold(
    y_true: np.ndarray,
    y_scores: np.ndarray,
    target_precision: float = 0.75,
) -> tuple[float, float, float]:
    """Find threshold that achieves target precision. Returns (threshold, precision, recall)."""
    prec, rec, thresh = precision_recall_curve(y_true, y_scores)
    for i, p in enumerate(prec[:-1]):
        if p >= target_precision:
            return float(thresh[i]), float(p), float(rec[i])
    return 0.5, float(prec[-2]), float(rec[-2])


def train(csv_path: str, output_path: Path | None = None) -> dict:
    """
    Train and calibrate the LightGBM urgency model.

    CSV columns: FEATURE_COLS + 'label' (1=mandate within 90d, 0=no mandate)
    """
    output_path = output_path or MODEL_PATH
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(csv_path)
    X = df[FEATURE_COLS].fillna(0)
    y = df["label"]

    # Time-ordered split — never shuffle when data is temporal
    split = int(len(df) * 0.80)
    X_train, X_test = X.iloc[:split], X.iloc[split:]
    y_train, y_test = y.iloc[:split], y.iloc[split:]

    # SMOTE: oversample positives until they are 30% of training set
    pos_rate = y_train.mean()
    if pos_rate < 0.30:
        sm = SMOTE(sampling_strategy=0.30, random_state=42)
        X_train_r, y_train_r = sm.fit_resample(X_train, y_train)
        log.info("SMOTE: %d → %d rows", len(X_train), len(X_train_r))
    else:
        X_train_r, y_train_r = X_train, y_train

    base = LGBMClassifier(
        n_estimators=300,
        num_leaves=31,
        learning_rate=0.05,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
        verbose=-1,
    )

    # Isotonic for ≥1000 samples, Platt otherwise
    method = "isotonic" if len(X_train_r) >= 1000 else "sigmoid"
    calibrated = CalibratedClassifierCV(
        base,
        cv=StratifiedKFold(n_splits=5, shuffle=True, random_state=42),
        method=method,
    )
    calibrated.fit(X_train_r, y_train_r)

    y_scores = calibrated.predict_proba(X_test)[:, 1]
    pr_auc = average_precision_score(y_test, y_scores)
    thresh, prec, rec = find_optimal_threshold(y_test.values, y_scores)

    metrics = {
        "train_rows": len(X_train_r),
        "pr_auc": round(pr_auc, 3),
        "optimal_threshold": round(thresh, 3),
        "precision_at_threshold": round(prec, 3),
        "recall_at_threshold": round(rec, 3),
        "calibration_method": method,
    }
    log.info("Urgency model metrics: %s", metrics)

    joblib.dump(calibrated, output_path)
    log.info("Urgency model saved → %s", output_path)
    UrgencyModel._instance = None

    return metrics
