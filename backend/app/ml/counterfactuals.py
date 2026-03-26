"""
app/ml/counterfactuals.py — Enhancement 7: Counterfactual explainability.

For each high-score prediction: what would need to change to lower
the score below 0.4?

Uses SHAP TreeExplainer for XGBoost (fast — 1000× faster than KernelExplainer).
Only exposes features the company can actually change (signal features excluded).

Output:
    scoring_explanations table:
    {company_id, practice_area, horizon, top_shap_features, counterfactuals}
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

log = logging.getLogger(__name__)

# Score threshold above which we compute counterfactuals
EXPLANATION_SCORE_THRESHOLD: float = 0.4
TOP_SHAP_FEATURES: int = 10
COUNTERFACTUAL_FEATURES: int = 3

# Features the company CAN change (actionable levers)
# Regulatory signals, market data, and enforcement actions are excluded —
# they are signals of what happened, not levers the company can pull.
ACTIONABLE_FEATURES: set[str] = {
    "legal_hire_velocity",
    "exec_departure_count_90d",
    "gc_departure_flag",
    "compliance_hire_spike",
    "director_interlocks_count",
    "filing_frequency_30d",
    "material_change_count_90d",
    "hedging_language_score",
    "mda_sentiment_score",
    "layoff_signal_score",
    "going_concern_flag",
    "auditor_change_flag",
    "restatement_flag",
}


def explain_prediction(
    model: Any,  # CalibratedClassifierCV wrapping XGBClassifier
    features: dict[str, float],
    feature_columns: list[str],
    practice_area: str,
    horizon: int,
    score: float,
) -> dict[str, Any] | None:
    """
    Compute SHAP values and counterfactuals for one prediction.

    Args:
        model:           Trained CalibratedClassifierCV from BayesianEngine.
        features:        Feature dict for this company.
        feature_columns: Ordered list of feature column names.
        practice_area:   Practice area being explained.
        horizon:         30, 60, or 90.
        score:           Current mandate probability.

    Returns:
        Explanation dict, or None if score below threshold or SHAP fails.
    """
    if score < EXPLANATION_SCORE_THRESHOLD:
        return None

    try:
        import shap
    except ImportError:
        log.error("shap not installed. Run: pip install shap")
        return None

    x = np.array(
        [features.get(col, 0.0) for col in feature_columns],
        dtype=np.float32,
    ).reshape(1, -1)

    try:
        # Extract the base XGBClassifier from the calibrated wrapper
        base_model = _extract_base_xgb(model)
        if base_model is None:
            log.warning("counterfactuals: could not extract XGBClassifier from calibrated model")
            return None

        explainer = shap.TreeExplainer(base_model)
        shap_values = explainer.shap_values(x)

        # shap_values shape: [1, n_features] for binary classification
        if isinstance(shap_values, list):
            sv = shap_values[1][0]  # positive class SHAP values
        else:
            sv = shap_values[0]

        # Top features by absolute SHAP value
        indices = np.argsort(np.abs(sv))[::-1][:TOP_SHAP_FEATURES]
        top_shap: list[dict[str, Any]] = [
            {
                "feature": feature_columns[i],
                "shap_value": float(sv[i]),
                "feature_value": float(features.get(feature_columns[i], 0.0)),
            }
            for i in indices
        ]

        # Counterfactuals: top actionable features with POSITIVE SHAP values
        # (these are the ones pushing the score up — reducing them would lower it)
        counterfactuals: list[dict[str, Any]] = []
        for i in indices:
            feat_name = feature_columns[i]
            if feat_name not in ACTIONABLE_FEATURES:
                continue
            if sv[i] <= 0:
                continue  # not contributing to high score

            feat_val = float(features.get(feat_name, 0.0))
            counterfactuals.append(
                {
                    "feature": feat_name,
                    "current_value": feat_val,
                    "suggested_direction": "decrease",
                    "estimated_score_reduction": round(abs(float(sv[i])), 4),
                    "shap_contribution": round(float(sv[i]), 4),
                }
            )

            if len(counterfactuals) >= COUNTERFACTUAL_FEATURES:
                break

        return {
            "practice_area": practice_area,
            "horizon": horizon,
            "score": score,
            "top_shap_features": top_shap,
            "counterfactuals": counterfactuals,
            "base_value": float(explainer.expected_value)
            if not isinstance(explainer.expected_value, np.ndarray)
            else float(explainer.expected_value[1]),
        }

    except Exception:
        log.exception("SHAP explanation failed for %s h%d", practice_area, horizon)
        return None


def explain_company(
    models_by_pa: dict[str, Any],  # {practice_area: CalibratedClassifierCV}
    features: dict[str, float],
    feature_columns: list[str],
    scores: dict[str, dict[int, float]],
    top_n_areas: int = 5,
) -> list[dict[str, Any]]:
    """
    Explain the top N highest-scoring practice areas for a company.

    Args:
        models_by_pa:     {practice_area: trained model (30d model used for explanation)}
        features:         Company feature dict.
        feature_columns:  Feature column order.
        scores:           {practice_area: {30: prob, 60: prob, 90: prob}}
        top_n_areas:      How many practice areas to explain.

    Returns:
        List of explanation dicts (may be shorter than top_n_areas if some fail).
    """
    # Sort practice areas by 30d score descending
    sorted_areas = sorted(
        scores.items(),
        key=lambda x: x[1].get(30, 0.0),
        reverse=True,
    )[:top_n_areas]

    explanations: list[dict[str, Any]] = []
    for pa, horizon_scores in sorted_areas:
        model = models_by_pa.get(pa)
        if model is None:
            continue
        score_30 = horizon_scores.get(30, 0.0)
        explanation = explain_prediction(
            model=model,
            features=features,
            feature_columns=feature_columns,
            practice_area=pa,
            horizon=30,
            score=score_30,
        )
        if explanation:
            explanations.append(explanation)

    return explanations


def _extract_base_xgb(calibrated_model: Any) -> Any | None:
    """Extract the underlying XGBClassifier from CalibratedClassifierCV."""
    try:
        # CalibratedClassifierCV stores calibrated classifiers list
        if hasattr(calibrated_model, "calibrated_classifiers_"):
            first = calibrated_model.calibrated_classifiers_[0]
            if hasattr(first, "estimator"):
                return first.estimator
            if hasattr(first, "base_estimator"):
                return first.base_estimator
        # Direct access
        if hasattr(calibrated_model, "estimator"):
            return calibrated_model.estimator
        return None
    except Exception:
        log.exception("Failed to extract XGB from calibrated model")
        return None
