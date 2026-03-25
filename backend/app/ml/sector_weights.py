"""
app/ml/sector_weights.py — Enhancement 6: Industry-specific signal weighting.

Per-sector multipliers calibrated from training data.
E.g., oil price signal matters 3× more for energy than tech.
Weights stored in sector_signal_weights table and cached in Redis.
Never manually set — always calibrated from data.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

log = logging.getLogger(__name__)

# Sector slugs (must match NAICS codes in company table)
SECTORS: list[str] = [
    "energy",
    "mining",
    "tech",
    "financial_services",
    "real_estate",
    "healthcare",
    "manufacturing",
    "retail",
    "construction",
    "telecom",
    "media",
    "agriculture",
    "transportation",
    "utilities",
    "other",
]


def calibrate_sector_weights(
    X_train: Any,  # pd.DataFrame with feature columns + sector column
    y_train: Any,  # pd.Series (binary labels)
    feature_columns: list[str],
    sector_column: str = "sector",
) -> dict[str, dict[str, float]]:
    """
    Calibrate per-sector signal weights using mutual information.

    For each sector, compute mutual information between each feature and label.
    Normalize: sector_weight = sector_MI / global_MI.
    If sector_weight > 3.0, cap at 3.0 to prevent runaway amplification.

    Returns:
        {sector: {feature: weight_multiplier}}
    """
    try:
        from sklearn.feature_selection import mutual_info_classif

        weights: dict[str, dict[str, float]] = {}

        # Global MI across all sectors
        X_features = X_train[feature_columns].fillna(0)
        global_mi = mutual_info_classif(X_features, y_train, random_state=42)
        global_mi_map = dict(zip(feature_columns, global_mi))

        sectors_in_data = X_train[sector_column].unique()

        for sector in sectors_in_data:
            mask = X_train[sector_column] == sector
            if mask.sum() < 30:
                # Not enough data for this sector — use global weights
                weights[sector] = dict.fromkeys(feature_columns, 1.0)
                continue

            X_sector = X_train.loc[mask, feature_columns].fillna(0)
            y_sector = y_train[mask]

            if y_sector.sum() == 0:
                weights[sector] = dict.fromkeys(feature_columns, 1.0)
                continue

            sector_mi = mutual_info_classif(X_sector, y_sector, random_state=42)

            sector_weights: dict[str, float] = {}
            for feat, smi, gmi in zip(feature_columns, sector_mi, global_mi):
                if gmi < 1e-6:
                    sector_weights[feat] = 1.0
                else:
                    raw = smi / gmi
                    sector_weights[feat] = float(min(raw, 3.0))  # cap at 3x
            weights[sector] = sector_weights

        log.info("Calibrated sector weights for %d sectors", len(weights))
        return weights

    except Exception:
        log.exception("sector_weights: calibration failed")
        return {}


def apply_sector_weights(
    features: dict[str, float],
    sector: str,
    weights: dict[str, dict[str, float]],
) -> dict[str, float]:
    """
    Apply sector-specific multipliers to a feature dict.

    Args:
        features: Raw feature dict.
        sector:   Company sector slug.
        weights:  Output of calibrate_sector_weights().
    Returns:
        Weighted feature dict.
    """
    sector_w = weights.get(sector, {})
    if not sector_w:
        return features
    return {feat: val * sector_w.get(feat, 1.0) for feat, val in features.items()}


def compute_aggregate_multiplier(
    features: dict[str, float],
    sector: str,
    weights: dict[str, dict[str, float]],
    top_features: int = 5,
) -> float:
    """
    Compute a single sector_weight_multiplier scalar feature.
    Average of the top N sector weight multipliers for the highest-value features.
    This becomes the sector_weight_multiplier column in company_features.
    """
    sector_w = weights.get(sector, {})
    if not sector_w:
        return 1.0

    # Sort features by their raw value, take top N
    top = sorted(features.items(), key=lambda x: abs(x[1]), reverse=True)[:top_features]
    multipliers = [sector_w.get(feat, 1.0) for feat, _ in top]
    return float(np.mean(multipliers)) if multipliers else 1.0
