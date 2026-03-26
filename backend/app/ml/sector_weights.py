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
    human_overrides: dict[str, float] | None = None,
) -> float:
    """
    Compute a single sector_weight_multiplier scalar feature.
    Average of the top N sector weight multipliers for the highest-value features.
    This becomes the sector_weight_multiplier column in company_features.

    Phase 12: If human_overrides is provided ({signal_type: multiplier}), the human
    multiplier wins over the ML-calibrated one for matching features.
    """
    sector_w = weights.get(sector, {})
    if not sector_w:
        return 1.0

    # Sort features by their raw value, take top N
    top = sorted(features.items(), key=lambda x: abs(x[1]), reverse=True)[:top_features]

    multipliers: list[float] = []
    for feat, _ in top:
        if human_overrides and feat in human_overrides:
            multipliers.append(human_overrides[feat])  # human override wins
        else:
            multipliers.append(sector_w.get(feat, 1.0))

    return float(np.mean(multipliers)) if multipliers else 1.0


async def recalibrate_from_confirmations(db: Any) -> dict[str, dict[str, float]]:
    """
    Phase 12: Re-run sector weight calibration using last 30 days of confirmed mandate data.

    Pulls mandate_confirmations + company_features from PostgreSQL,
    re-runs mutual information calibration, and updates sector_signal_weights table.

    Args:
        db: Async SQLAlchemy session.

    Returns:
        New weights dict {sector: {feature: multiplier}}.
    """
    from datetime import UTC, datetime, timedelta

    import pandas as pd
    from sqlalchemy import text

    since = datetime.now(UTC) - timedelta(days=30)

    try:
        # Pull confirmed mandates joined to company features
        rows = (
            await db.execute(
                text(
                    """
                    SELECT cf.signal_data, cf.sector, mc.practice_area
                    FROM mandate_confirmations mc
                    JOIN company_features cf ON cf.company_id = mc.company_id
                    WHERE mc.created_at >= :since
                      AND cf.sector IS NOT NULL
                    LIMIT 50000
                    """
                ),
                {"since": since},
            )
        ).all()
    except Exception:
        log.warning("sector_weights.recalibrate: mandate_confirmations not available (Phase 9 pending)")
        return {}

    if not rows:
        log.info("sector_weights.recalibrate: no confirmed mandates in last 30 days — skipping")
        return {}

    try:
        # Build DataFrame from signal_data JSONB
        records = []
        for row in rows:
            signal_data = row.signal_data or {}
            record = dict(signal_data)
            record["sector"] = row.sector
            record["label"] = 1
            records.append(record)

        df = pd.DataFrame(records).fillna(0)
        feature_cols = [c for c in df.columns if c not in ("sector", "label")]

        if not feature_cols:
            log.warning("sector_weights.recalibrate: no feature columns found")
            return {}

        new_weights = calibrate_sector_weights(df, df["label"], feature_cols)

        # Update sector_signal_weights table
        await _persist_sector_weights(db, new_weights)

        log.info(
            "sector_weights.recalibrated",
            sectors=len(new_weights),
            features=len(feature_cols),
            mandate_count=len(rows),
        )
        return new_weights

    except Exception:
        log.exception("sector_weights.recalibrate: calibration failed")
        return {}


async def _persist_sector_weights(db: Any, weights: dict[str, dict[str, float]]) -> None:
    """Upsert new weights into sector_signal_weights table."""
    from sqlalchemy import text

    for sector, feature_weights in weights.items():
        for feature, multiplier in feature_weights.items():
            try:
                await db.execute(
                    text(
                        """
                        INSERT INTO sector_signal_weights (sector, signal_type, multiplier)
                        VALUES (:sector, :signal_type, :multiplier)
                        ON CONFLICT (sector, signal_type)
                        DO UPDATE SET multiplier = EXCLUDED.multiplier
                        """
                    ),
                    {"sector": sector, "signal_type": feature, "multiplier": multiplier},
                )
            except Exception:
                log.warning(
                    "sector_weights: failed to upsert", sector=sector, signal_type=feature
                )
    await db.commit()
    log.info("sector_weights.persisted", total_entries=sum(len(v) for v in weights.values()))


async def load_human_overrides_from_cache(
    signal_type: str | None = None,
    practice_area: str | None = None,
) -> dict[str, float]:
    """
    Phase 12: Load active signal_weight_overrides from Redis cache.
    Cache key: signal_overrides:v1 (TTL 1h).
    Returns {signal_type: multiplier} filtered by practice_area if provided.
    """
    from app.cache.client import cache

    cache_key = "signal_overrides:v1"
    try:
        cached = await cache.get(cache_key)
        if cached is None:
            return {}

        # cached is a list of {signal_type, practice_area, multiplier} dicts
        overrides: dict[str, float] = {}
        for entry in cached:
            if practice_area and entry.get("practice_area") != practice_area:
                continue
            overrides[entry["signal_type"]] = float(entry["multiplier"])
        return overrides
    except Exception:
        log.warning("sector_weights: failed to load human overrides from cache")
        return {}
