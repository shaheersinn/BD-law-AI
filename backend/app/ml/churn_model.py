"""
app/ml/churn_model.py — XGBoost churn classifier.

Predicts the probability that a client will stop instructing the firm
in the next 12 months. Score = 0-100 (higher = higher flight risk).

Training:  python -m app.ml.churn_model --train
Inference: ChurnModel().score(client_features)
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import classification_report, precision_score
from sklearn.model_selection import StratifiedKFold, train_test_split
from xgboost import XGBClassifier

from app.config import get_settings

log = logging.getLogger(__name__)
settings = get_settings()

MODEL_PATH = Path(settings.models_dir) / "churn_model.pkl"

# Feature columns — must match what the API extracts from billing data
FEATURE_COLS = [
    "total_billed_this_year",
    "yoy_billing_change_pct",  # % vs prior year — negative is bad
    "matters_opened_this_year",
    "days_since_last_matter",
    "disputes_this_year",
    "writeoff_pct",  # write-offs / billed
    "gc_changed_this_year",  # 0/1
    "days_since_last_contact",
    "practice_area_count",
    "reply_latency_days",  # avg email reply lag
    "billing_trend_3m",  # 3-month billing slope (positive/negative)
    "matter_completion_rate",  # closed / opened
]


@dataclass
class ClientFeatures:
    total_billed_this_year: float
    yoy_billing_change_pct: float
    matters_opened_this_year: int
    days_since_last_matter: int
    disputes_this_year: int
    writeoff_pct: float
    gc_changed_this_year: int
    days_since_last_contact: int
    practice_area_count: int
    reply_latency_days: float = 3.0
    billing_trend_3m: float = 0.0
    matter_completion_rate: float = 1.0

    def to_array(self) -> np.ndarray:
        return np.array(
            [
                [
                    self.total_billed_this_year,
                    self.yoy_billing_change_pct,
                    self.matters_opened_this_year,
                    self.days_since_last_matter,
                    self.disputes_this_year,
                    self.writeoff_pct,
                    self.gc_changed_this_year,
                    self.days_since_last_contact,
                    self.practice_area_count,
                    self.reply_latency_days,
                    self.billing_trend_3m,
                    self.matter_completion_rate,
                ]
            ]
        )


class ChurnModel:
    """XGBoost churn scorer — loads from disk on first call."""

    _instance: Optional["ChurnModel"] = None

    def __init__(self) -> None:
        self._model: CalibratedClassifierCV | None = None

    @classmethod
    def get(cls) -> "ChurnModel":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load(self) -> None:
        if MODEL_PATH.exists():
            self._model = joblib.load(MODEL_PATH)
            log.info("Churn model loaded from %s", MODEL_PATH)
        else:
            log.warning("No trained churn model found at %s — using heuristic fallback", MODEL_PATH)

    def score(self, features: ClientFeatures) -> int:
        """Return 0-100 churn risk score."""
        if self._model is None:
            self._load()

        if self._model is not None:
            try:
                prob = self._model.predict_proba(features.to_array())[0][1]
                return int(round(prob * 100))
            except Exception as e:
                log.error("Churn model inference error: %s", e)

        # Heuristic fallback (no trained model yet)
        return _heuristic_churn_score(features)

    def is_trained(self) -> bool:
        return MODEL_PATH.exists()


def _heuristic_churn_score(f: ClientFeatures) -> int:
    """Simple rule-based fallback before a model is trained."""
    score = 10.0

    # Billing signals
    if f.yoy_billing_change_pct < -20:
        score += 30
    elif f.yoy_billing_change_pct < -5:
        score += 15

    # Contact signals
    if f.days_since_last_contact > 60:
        score += 20
    elif f.days_since_last_contact > 30:
        score += 10

    # Matter cadence
    if f.days_since_last_matter > 180:
        score += 15
    elif f.days_since_last_matter > 90:
        score += 8

    # Disputes and write-offs
    score += f.disputes_this_year * 8
    if f.writeoff_pct > 0.10:
        score += 15

    # GC change
    if f.gc_changed_this_year:
        score += 15

    return min(int(score), 99)


# ── Training ───────────────────────────────────────────────────────────────────


def train(csv_path: str, output_path: Path | None = None) -> dict:
    """
    Train a calibrated XGBoost churn classifier.

    CSV must have columns matching FEATURE_COLS + 'label' (1=churned, 0=stayed).
    Returns evaluation metrics dict.
    """
    output_path = output_path or MODEL_PATH
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(csv_path)
    missing = [c for c in FEATURE_COLS + ["label"] if c not in df.columns]
    if missing:
        raise ValueError(f"Training CSV missing columns: {missing}")

    X = df[FEATURE_COLS].fillna(0)
    y = df["label"]

    log.info("Training on %d rows (%d churned, %d retained)", len(df), y.sum(), (y == 0).sum())

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )

    pos = y_train.sum()
    neg = len(y_train) - pos
    scale_pos_weight = neg / pos if pos > 0 else 1.0

    base_model = XGBClassifier(
        n_estimators=300,
        max_depth=5,
        learning_rate=0.03,
        scale_pos_weight=scale_pos_weight,
        subsample=0.8,
        colsample_bytree=0.8,
        eval_metric="aucpr",
        use_label_encoder=False,
        random_state=42,
        n_jobs=-1,
    )

    # Platt calibration — makes probability outputs reliable
    calibrated = CalibratedClassifierCV(
        base_model,
        cv=StratifiedKFold(n_splits=5, shuffle=True, random_state=42),
        method="sigmoid",
    )
    calibrated.fit(X_train, y_train)

    y_pred = (calibrated.predict_proba(X_test)[:, 1] >= 0.5).astype(int)
    report = classification_report(y_test, y_pred, output_dict=True)
    precision_high = precision_score(
        y_test,
        (calibrated.predict_proba(X_test)[:, 1] >= 0.60).astype(int),
        zero_division=0,
    )

    metrics = {
        "rows": len(df),
        "precision_0.5": round(report["1"]["precision"], 3),
        "recall_0.5": round(report["1"]["recall"], 3),
        "f1_0.5": round(report["1"]["f1-score"], 3),
        "precision_at_60": round(precision_high, 3),
    }
    log.info("Churn model metrics: %s", metrics)

    joblib.dump(calibrated, output_path)
    log.info("Churn model saved → %s", output_path)

    # Reset singleton so next inference loads fresh model
    ChurnModel._instance = None

    return metrics


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Train churn model")
    parser.add_argument("--train", action="store_true")
    parser.add_argument("--csv", default="data/churn_training_data.csv")
    args = parser.parse_args()

    if args.train:
        metrics = train(args.csv)
        print("Training complete:", metrics)
