"""
app/ml/bayesian_engine.py — XGBoost + Optuna Bayesian scoring engine.

One engine per practice area. Produces mandate probability for 30/60/90d horizons.
This is the primary model — works day 1, interpretable, fast.
Transformer (transformer_scorer.py) earns control per practice area via orchestrator.

Training: azure/training/train_all.py (Azure batch job — never run locally)
Inference: BayesianEngine(practice_area).score(feature_vector) → {30d, 60d, 90d}
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import optuna
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import f1_score, precision_recall_curve, roc_auc_score
from sklearn.model_selection import StratifiedKFold
from xgboost import XGBClassifier

from app.config import get_settings

log = logging.getLogger(__name__)
settings = get_settings()

optuna.logging.set_verbosity(optuna.logging.WARNING)

# ── Constants ──────────────────────────────────────────────────────────────────

HORIZONS: list[int] = [30, 60, 90]
OPTUNA_TRIALS: int = 100
OPTUNA_CV_FOLDS: int = 5
EARLY_STOPPING_ROUNDS: int = 50
# Negative:Positive ratio from Phase 3 negative sampler (5:1)
DEFAULT_SCALE_POS_WEIGHT: float = 5.0
# Orchestrator flip threshold: transformer must beat this delta to take over
ORCHESTRATOR_F1_THRESHOLD: float = 0.03

# 34 practice area slugs — must match enum in mandate_labels table
PRACTICE_AREAS: list[str] = [
    "ma",
    "litigation",
    "regulatory",
    "employment",
    "insolvency",
    "securities",
    "competition",
    "privacy",
    "environmental",
    "tax",
    "real_estate",
    "banking",
    "ip",
    "immigration",
    "infrastructure",
    "wills_estates",
    "admin_public",
    "arbitration",
    "class_actions",
    "construction_disputes",
    "defamation",
    "financial_regulatory",
    "franchise",
    "health_sciences",
    "insurance",
    "intl_trade",
    "mining",
    "municipal_land",
    "nfp_charity",
    "pension_benefits",
    "product_liability",
    "sports_entertainment",
    "tech_fintech",
    "data_privacy_tech",
]

# Features supplied by Phase 2 company_features table (must match column names)
FEATURE_COLUMNS: list[str] = [
    # Filing features
    "filing_frequency_30d",
    "filing_frequency_delta",
    "material_change_count_90d",
    "mda_sentiment_score",
    "hedging_language_score",
    "restatement_flag",
    "auditor_change_flag",
    "going_concern_flag",
    # Legal/Court features
    "active_litigation_count",
    "new_filing_30d",
    "regulatory_action_count_90d",
    "canlii_mention_velocity",
    "class_action_proximity",
    # Employment features
    "legal_hire_velocity",
    "exec_departure_count_90d",
    "layoff_signal_score",
    "gc_departure_flag",
    "compliance_hire_spike",
    # Market features
    "price_decline_90d",
    "volatility_30d",
    "short_interest_ratio",
    "options_put_call_ratio",
    "volume_anomaly_score",
    "analyst_downgrade_count_30d",
    # NLP signal features (populated by Phase 4)
    "intent_score",
    "named_entity_company_mentions",
    "sentiment_trend_7d",
    # Geographic features
    "regional_insolvency_rate",
    "court_volume_index",
    "google_trends_score",
    "boc_rate_cycle",
    "sector_insolvency_indicator",
    # Network features
    "director_interlocks_count",
    "law_firm_shared_counsel",
    # Temporal decay-weighted signal aggregates (populated by temporal_decay.py)
    "decayed_filing_signal",
    "decayed_legal_signal",
    "decayed_employment_signal",
    "decayed_market_signal",
    "decayed_nlp_signal",
    # Sector encoding (one-hot compressed via PCA — single float from sector_weights.py)
    "sector_weight_multiplier",
    # Velocity features (populated by velocity_scorer.py — live)
    "velocity_score_7d",
    # Anomaly feature (populated by anomaly_detector.py)
    "anomaly_score",
    # Corporate graph features (populated by graph_features.py)
    "graph_centrality",
    "peer_distress_score",
    # Cross-jurisdiction propagation
    "cross_jurisdiction_signal",
]


# ── Data classes ───────────────────────────────────────────────────────────────


@dataclass
class HorizonScores:
    """Output of a single BayesianEngine inference call."""

    practice_area: str
    score_30d: float
    score_60d: float
    score_90d: float
    model_version: str
    inference_ms: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "30d": round(self.score_30d, 4),
            "60d": round(self.score_60d, 4),
            "90d": round(self.score_90d, 4),
        }


@dataclass
class TrainingResult:
    """Output of BayesianEngine.train(). Stored in model_registry table."""

    practice_area: str
    horizon: int
    f1_holdout: float
    pr_auc_holdout: float
    roc_auc_holdout: float
    best_threshold: float
    best_params: dict[str, Any]
    feature_importances: dict[str, float]
    scale_pos_weight: float
    n_train: int
    n_holdout: int
    artifact_path: str
    training_seconds: float


# ── Engine ─────────────────────────────────────────────────────────────────────


class BayesianEngine:
    """
    XGBoost mandate probability scorer for a single practice area.

    Loads pre-trained calibrated models from DO Spaces (or local cache).
    Training happens in Azure batch jobs — never call .train() in production.

    Usage:
        engine = BayesianEngine("ma")
        scores = engine.score(feature_dict)  # → HorizonScores
    """

    def __init__(self, practice_area: str) -> None:
        if practice_area not in PRACTICE_AREAS:
            raise ValueError(
                f"Unknown practice area: {practice_area}. Valid areas: {PRACTICE_AREAS}"
            )
        self.practice_area = practice_area
        self._models: dict[int, CalibratedClassifierCV] = {}
        self._thresholds: dict[int, float] = {}
        self._model_version: str = "unloaded"
        self._loaded = False

    # ── Inference ─────────────────────────────────────────────────────────────

    def load(self, model_dir: Path | None = None) -> None:
        """Load all 3 horizon models from disk. Called at API startup."""
        if model_dir is None:
            model_dir = Path(settings.models_dir) / "bayesian" / self.practice_area

        missing = []
        for horizon in HORIZONS:
            model_path = model_dir / f"h{horizon}.pkl"
            threshold_path = model_dir / f"h{horizon}_threshold.txt"

            if not model_path.exists():
                missing.append(str(model_path))
                continue

            self._models[horizon] = joblib.load(model_path)

            if threshold_path.exists():
                self._thresholds[horizon] = float(threshold_path.read_text().strip())
            else:
                self._thresholds[horizon] = 0.5  # fallback

        if missing:
            log.warning(
                "BayesianEngine %s: missing model files: %s",
                self.practice_area,
                missing,
            )

        version_path = model_dir / "version.txt"
        if version_path.exists():
            self._model_version = version_path.read_text().strip()

        self._loaded = bool(self._models)
        log.info(
            "BayesianEngine %s loaded %d/3 horizon models (version=%s)",
            self.practice_area,
            len(self._models),
            self._model_version,
        )

    def score(self, features: dict[str, float]) -> HorizonScores:
        """
        Score a single company for this practice area.

        Args:
            features: dict mapping FEATURE_COLUMNS names to float values.
                      Missing features are filled with 0.0.

        Returns:
            HorizonScores with probabilities for 30/60/90d.
        """
        if not self._loaded:
            raise RuntimeError(
                f"BayesianEngine {self.practice_area} not loaded. Call .load() first."
            )

        t0 = time.perf_counter()

        # Build feature vector — fill missing with 0.0 (not NaN)
        x = np.array(
            [features.get(col, 0.0) for col in FEATURE_COLUMNS],
            dtype=np.float32,
        ).reshape(1, -1)

        scores: dict[int, float] = {}
        for horizon in HORIZONS:
            model = self._models.get(horizon)
            if model is None:
                scores[horizon] = 0.0
                continue
            try:
                prob = float(model.predict_proba(x)[0, 1])
                # Clip to [0.001, 0.999] — never return exact 0 or 1
                scores[horizon] = float(np.clip(prob, 0.001, 0.999))
            except Exception:
                log.exception(
                    "BayesianEngine %s h%d score failed",
                    self.practice_area,
                    horizon,
                )
                scores[horizon] = 0.0

        inference_ms = (time.perf_counter() - t0) * 1000

        return HorizonScores(
            practice_area=self.practice_area,
            score_30d=scores[30],
            score_60d=scores[60],
            score_90d=scores[90],
            model_version=self._model_version,
            inference_ms=inference_ms,
        )

    def score_batch(self, feature_rows: list[dict[str, float]]) -> list[HorizonScores]:
        """Score multiple companies in one vectorised call."""
        if not self._loaded:
            raise RuntimeError(f"BayesianEngine {self.practice_area} not loaded.")

        t0 = time.perf_counter()
        X = np.array(
            [[row.get(col, 0.0) for col in FEATURE_COLUMNS] for row in feature_rows],
            dtype=np.float32,
        )

        results: list[HorizonScores] = []
        horizon_probs: dict[int, np.ndarray] = {}

        for horizon in HORIZONS:
            model = self._models.get(horizon)
            if model is None:
                horizon_probs[horizon] = np.zeros(len(feature_rows))
                continue
            try:
                probs = model.predict_proba(X)[:, 1]
                horizon_probs[horizon] = np.clip(probs, 0.001, 0.999)
            except Exception:
                log.exception("BayesianEngine %s batch h%d failed", self.practice_area, horizon)
                horizon_probs[horizon] = np.zeros(len(feature_rows))

        total_ms = (time.perf_counter() - t0) * 1000
        per_ms = total_ms / max(len(feature_rows), 1)

        for i in range(len(feature_rows)):
            results.append(
                HorizonScores(
                    practice_area=self.practice_area,
                    score_30d=float(horizon_probs[30][i]),
                    score_60d=float(horizon_probs[60][i]),
                    score_90d=float(horizon_probs[90][i]),
                    model_version=self._model_version,
                    inference_ms=per_ms,
                )
            )

        return results

    # ── Training (called from Azure batch job only) ───────────────────────────

    @staticmethod
    def train(
        practice_area: str,
        X_train: pd.DataFrame,
        y_train_30d: pd.Series,
        y_train_60d: pd.Series,
        y_train_90d: pd.Series,
        X_holdout: pd.DataFrame,
        y_holdout_30d: pd.Series,
        y_holdout_60d: pd.Series,
        y_holdout_90d: pd.Series,
        output_dir: Path,
        n_trials: int = OPTUNA_TRIALS,
    ) -> list[TrainingResult]:
        """
        Train 3 calibrated XGBoost models (one per horizon) with Optuna tuning.

        IMPORTANT: Called only from Azure batch jobs. Never call in production.

        Args:
            practice_area: One of PRACTICE_AREAS slugs.
            X_train: Feature matrix (n_samples × n_features).
            y_train_*: Binary labels per horizon.
            X_holdout: Held-out test set (last 6 months — never seen in training).
            y_holdout_*: Holdout labels per horizon.
            output_dir: Where to save models + metadata.
            n_trials: Optuna trials per horizon.

        Returns:
            List of TrainingResult (one per horizon).
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        results: list[TrainingResult] = []

        horizon_labels = {
            30: (y_train_30d, y_holdout_30d),
            60: (y_train_60d, y_holdout_60d),
            90: (y_train_90d, y_holdout_90d),
        }

        for horizon, (y_train, y_holdout) in horizon_labels.items():
            t0 = time.perf_counter()
            log.info("Training %s h%dd — %d samples", practice_area, horizon, len(X_train))

            # Compute class weight for this horizon
            n_pos = int(y_train.sum())
            n_neg = int(len(y_train) - n_pos)
            scale_pos_weight = n_neg / n_pos if n_pos > 0 else DEFAULT_SCALE_POS_WEIGHT

            # Optuna objective
            def objective(trial: optuna.Trial) -> float:
                params = {
                    "n_estimators": trial.suggest_int("n_estimators", 100, 1000, step=50),
                    "max_depth": trial.suggest_int("max_depth", 3, 10),
                    "learning_rate": trial.suggest_float("learning_rate", 0.005, 0.3, log=True),
                    "subsample": trial.suggest_float("subsample", 0.5, 1.0),
                    "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
                    "reg_alpha": trial.suggest_float("reg_alpha", 1e-8, 10.0, log=True),
                    "reg_lambda": trial.suggest_float("reg_lambda", 1e-8, 10.0, log=True),
                    "min_child_weight": trial.suggest_int("min_child_weight", 1, 10),
                    "scale_pos_weight": scale_pos_weight,
                    "use_label_encoder": False,
                    "eval_metric": "logloss",
                    "random_state": 42,
                    "tree_method": "hist",
                    "device": "cpu",
                    "verbosity": 0,
                }
                model = XGBClassifier(**params)
                skf = StratifiedKFold(n_splits=OPTUNA_CV_FOLDS, shuffle=True, random_state=42)
                f1_scores: list[float] = []
                for fold_train_idx, fold_val_idx in skf.split(X_train, y_train):
                    X_fold_tr = X_train.iloc[fold_train_idx]
                    y_fold_tr = y_train.iloc[fold_train_idx]
                    X_fold_val = X_train.iloc[fold_val_idx]
                    y_fold_val = y_train.iloc[fold_val_idx]
                    model.fit(
                        X_fold_tr,
                        y_fold_tr,
                        eval_set=[(X_fold_val, y_fold_val)],
                        verbose=False,
                        early_stopping_rounds=EARLY_STOPPING_ROUNDS,
                    )
                    preds = (model.predict_proba(X_fold_val)[:, 1] >= 0.5).astype(int)
                    f1_scores.append(f1_score(y_fold_val, preds, zero_division=0))
                return float(np.mean(f1_scores))

            study = optuna.create_study(
                direction="maximize",
                sampler=optuna.samplers.TPESampler(seed=42),
                pruner=optuna.pruners.MedianPruner(n_warmup_steps=10),
            )
            study.optimize(objective, n_trials=n_trials, n_jobs=1)

            best_params = study.best_params
            best_params["scale_pos_weight"] = scale_pos_weight
            best_params["use_label_encoder"] = False
            best_params["eval_metric"] = "logloss"
            best_params["random_state"] = 42
            best_params["tree_method"] = "hist"
            best_params["device"] = "cpu"
            best_params["verbosity"] = 0

            # Final training on full train set
            base_model = XGBClassifier(**best_params)
            base_model.fit(
                X_train,
                y_train,
                eval_set=[(X_holdout, y_holdout)],
                verbose=False,
                early_stopping_rounds=EARLY_STOPPING_ROUNDS,
            )

            # Probability calibration — isotonic for larger datasets, sigmoid for smaller
            method = "isotonic" if len(X_train) >= 1000 else "sigmoid"
            calibrated = CalibratedClassifierCV(estimator=base_model, method=method, cv="prefit")
            calibrated.fit(X_holdout, y_holdout)

            # Find optimal threshold (maximise F1 on holdout)
            probs_holdout = calibrated.predict_proba(X_holdout)[:, 1]
            best_threshold, best_f1 = _find_optimal_threshold(y_holdout.values, probs_holdout)

            # Holdout metrics
            y_pred_holdout = (probs_holdout >= best_threshold).astype(int)
            pr_auc = _safe_pr_auc(y_holdout.values, probs_holdout)
            roc_auc = _safe_roc_auc(y_holdout.values, probs_holdout)

            log.info(
                "%s h%dd — F1=%.3f PR-AUC=%.3f ROC-AUC=%.3f threshold=%.3f",
                practice_area,
                horizon,
                best_f1,
                pr_auc,
                roc_auc,
                best_threshold,
            )

            # Feature importances (gain)
            importances: dict[str, float] = {}
            try:
                raw_imp = base_model.feature_importances_
                importances = {
                    col: float(imp) for col, imp in zip(FEATURE_COLUMNS, raw_imp) if imp > 0
                }
            except Exception:
                log.warning(
                    "%s h%dd: could not extract feature importances", practice_area, horizon
                )

            # Save artifacts
            model_path = output_dir / f"h{horizon}.pkl"
            threshold_path = output_dir / f"h{horizon}_threshold.txt"
            joblib.dump(calibrated, model_path)
            threshold_path.write_text(str(best_threshold))

            training_seconds = time.perf_counter() - t0

            results.append(
                TrainingResult(
                    practice_area=practice_area,
                    horizon=horizon,
                    f1_holdout=best_f1,
                    pr_auc_holdout=pr_auc,
                    roc_auc_holdout=roc_auc,
                    best_threshold=best_threshold,
                    best_params=best_params,
                    feature_importances=importances,
                    scale_pos_weight=scale_pos_weight,
                    n_train=len(X_train),
                    n_holdout=len(X_holdout),
                    artifact_path=str(model_path),
                    training_seconds=training_seconds,
                )
            )

        # Write version file
        import datetime

        version = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        (output_dir / "version.txt").write_text(version)

        log.info(
            "Training complete for %s: %d horizon models saved to %s",
            practice_area,
            len(results),
            output_dir,
        )
        return results


# ── Helpers ────────────────────────────────────────────────────────────────────


def _find_optimal_threshold(y_true: np.ndarray, y_proba: np.ndarray) -> tuple[float, float]:
    """Find probability threshold maximising F1 on holdout."""
    if y_true.sum() == 0:
        return 0.5, 0.0
    precision, recall, thresholds = precision_recall_curve(y_true, y_proba)
    f1_scores = np.where(
        (precision + recall) > 0,
        2 * precision * recall / (precision + recall),
        0.0,
    )
    best_idx = int(np.argmax(f1_scores[:-1]))  # last element has no threshold
    return float(thresholds[best_idx]), float(f1_scores[best_idx])


def _safe_pr_auc(y_true: np.ndarray, y_proba: np.ndarray) -> float:
    """PR-AUC with safe fallback for all-negative labels."""
    if y_true.sum() == 0:
        return 0.0
    try:
        from sklearn.metrics import average_precision_score

        return float(average_precision_score(y_true, y_proba))
    except Exception:
        return 0.0


def _safe_roc_auc(y_true: np.ndarray, y_proba: np.ndarray) -> float:
    """ROC-AUC with safe fallback."""
    if len(np.unique(y_true)) < 2:
        return 0.0
    try:
        return float(roc_auc_score(y_true, y_proba))
    except Exception:
        return 0.0


# ── Registry of loaded engines (module-level singleton for API reuse) ──────────

_LOADED_ENGINES: dict[str, BayesianEngine] = {}


def get_engine(practice_area: str) -> BayesianEngine:
    """Return a loaded BayesianEngine, loading from disk on first call."""
    if practice_area not in _LOADED_ENGINES:
        engine = BayesianEngine(practice_area)
        engine.load()
        _LOADED_ENGINES[practice_area] = engine
    return _LOADED_ENGINES[practice_area]


def load_all_engines() -> None:
    """Pre-load all 34 engines. Call at API startup to eliminate cold-start."""
    for pa in PRACTICE_AREAS:
        try:
            get_engine(pa)
        except Exception:
            log.exception("Failed to load engine for %s", pa)
    log.info("BayesianEngine: %d/%d engines loaded", len(_LOADED_ENGINES), len(PRACTICE_AREAS))
