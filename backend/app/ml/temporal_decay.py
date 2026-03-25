"""
app/ml/temporal_decay.py — Enhancement 10: Temporal decay modeling.

Each signal type has a half-life per practice area.
Signal weight = base_weight × exp(-λt)

λ (lambda) calibrated per signal type from training data via grid search.
Decay parameters stored in signal_decay_config table.

Examples from research:
    regulatory_filing:  half-life ~90 days  (λ ≈ 0.0077)
    breach_news:        half-life ~30 days  (λ ≈ 0.023)
    ma_rumour:          half-life ~14 days  (λ ≈ 0.050)

Lambda grid: [0.002, 0.01, 0.03, 0.07, 0.2]
Floor: λ ≥ 0.002 (no signal decays in <7 days minimum half-life floor)
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Any

import numpy as np

log = logging.getLogger(__name__)

# Lambda grid for calibration (grid search over these values)
LAMBDA_GRID: list[float] = [0.002, 0.005, 0.01, 0.02, 0.03, 0.05, 0.07, 0.10, 0.15, 0.20]
LAMBDA_FLOOR: float = 0.002  # no signal can decay in under ~7 days (half-life floor)
HALF_LIFE_FLOOR_DAYS: float = 7.0

# Default lambda values (used before calibration from data)
# Sourced from legal domain knowledge + literature
DEFAULT_LAMBDAS: dict[str, float] = {
    # Corporate filings — long-lived (regulatory / legal consequence takes time)
    "sedar_material_change": 0.008,
    "sedar_business_acquisition": 0.007,
    "sedar_confidentiality": 0.010,
    "sedar_going_concern": 0.006,
    "sedar_auditor_change": 0.007,
    "edgar_8k": 0.012,
    "edgar_merger_confirmed": 0.005,
    # Court / litigation — medium persistence
    "canlii_class_action": 0.010,
    "canlii_ccaa": 0.007,
    "canlii_defendant": 0.012,
    "canlii_injunction": 0.010,
    # Regulatory enforcement — long-lived (process takes months)
    "osc_enforcement": 0.007,
    "osfi_supervisory": 0.007,
    "competition_investigation": 0.008,
    "fintrac_noncompliance": 0.009,
    "eccc_enforcement": 0.008,
    # Job postings — medium (role filled or withdrawn in weeks)
    "job_gc_hire": 0.025,
    "job_cco_urgent": 0.030,
    "job_privacy_counsel": 0.025,
    "job_ma_counsel": 0.030,
    "job_litigation_counsel": 0.025,
    # News — short-lived (news cycle)
    "news_lawsuit": 0.040,
    "news_investigation": 0.035,
    "news_data_breach": 0.023,  # ~30 day half-life
    "news_merger": 0.050,  # ~14 day half-life
    "news_exploring_strategic": 0.050,
    "news_layoffs": 0.040,
    "news_legal_proceedings": 0.030,
    # LinkedIn — medium (executive changes are persistent)
    "linkedin_gc_spike": 0.020,
    "linkedin_exec_departure": 0.018,
    "linkedin_mass_exits": 0.020,
    # Market signals — short-lived
    "volume_anomaly_score": 0.070,
    "short_interest_ratio": 0.050,
    # Geospatial — medium
    "jet_baystreet_2x": 0.035,
    "satellite_parking_drop": 0.040,
}


@dataclass
class DecayConfig:
    """Lambda value for one signal type (optionally per practice area)."""

    signal_type: str
    practice_area: str  # "global" if same decay across all practice areas
    lambda_value: float
    half_life_days: float
    calibrated: bool  # True if calibrated from data, False if default


def half_life_from_lambda(lam: float) -> float:
    """Compute half-life in days from lambda."""
    if lam <= 0:
        return float("inf")
    return math.log(2) / lam


def lambda_from_half_life(half_life_days: float) -> float:
    """Compute lambda from half-life in days."""
    if half_life_days <= 0:
        raise ValueError("half_life_days must be > 0")
    return math.log(2) / half_life_days


def apply_decay(base_weight: float, age_days: float, lam: float) -> float:
    """
    Apply exponential decay to a signal weight.

    weight = base_weight × exp(-λ × age_days)

    Args:
        base_weight: Original signal weight (from convergence.py SIGNAL_WEIGHTS).
        age_days:    Age of the signal in days (time since it was recorded).
        lam:         Decay constant (from signal_decay_config table).
    Returns:
        Decayed weight in [0, base_weight].
    """
    if age_days < 0:
        return base_weight
    decayed = base_weight * math.exp(-lam * age_days)
    return float(max(0.0, decayed))


def compute_decayed_signal_aggregate(
    signals: list[dict[str, Any]],
    decay_configs: dict[str, float],  # {signal_type: lambda}
    base_weights: dict[str, float],  # {signal_type: base_weight}
) -> float:
    """
    Compute convergence score with temporal decay applied.

    Uses: P(mandate) = 1 - ∏(1 - w_i × decay_i)

    Args:
        signals: List of {signal_type, age_days} dicts.
        decay_configs: {signal_type: lambda} — from signal_decay_config table.
        base_weights:  {signal_type: base_weight} — from SIGNAL_WEIGHTS.
    Returns:
        Convergence probability in [0, 1].
    """
    if not signals:
        return 0.0

    product = 1.0
    for sig in signals:
        signal_type = sig.get("signal_type", "")
        age_days = float(sig.get("age_days", 0.0))

        lam = decay_configs.get(signal_type, DEFAULT_LAMBDAS.get(signal_type, 0.01))
        bw = base_weights.get(signal_type, 0.5)

        decayed_weight = apply_decay(bw, age_days, lam)
        product *= 1.0 - decayed_weight

    return float(1.0 - product)


def compute_decay_features(
    signals_by_category: dict[str, list[dict[str, Any]]],
    decay_configs: dict[str, float],
    base_weights: dict[str, float],
) -> dict[str, float]:
    """
    Compute decayed aggregate features per signal category.
    These populate the decayed_*_signal columns in company_features.

    Args:
        signals_by_category: {
            "filing": [...signals],
            "legal": [...],
            "employment": [...],
            "market": [...],
            "nlp": [...]
        }
        decay_configs: Lambda per signal type.
        base_weights:  Base weights per signal type.

    Returns:
        {
            "decayed_filing_signal": float,
            "decayed_legal_signal": float,
            "decayed_employment_signal": float,
            "decayed_market_signal": float,
            "decayed_nlp_signal": float,
        }
    """
    category_map = {
        "filing": "decayed_filing_signal",
        "legal": "decayed_legal_signal",
        "employment": "decayed_employment_signal",
        "market": "decayed_market_signal",
        "nlp": "decayed_nlp_signal",
    }

    result: dict[str, float] = {}
    for category, feature_name in category_map.items():
        signals = signals_by_category.get(category, [])
        result[feature_name] = compute_decayed_signal_aggregate(
            signals, decay_configs, base_weights
        )

    return result


def calibrate_lambda(
    signal_type: str,
    events: list[dict[str, Any]],  # [{signal_age_at_mandate_days: float}]
    lambda_grid: list[float] = LAMBDA_GRID,
) -> float:
    """
    Calibrate lambda for a signal type using maximum likelihood on observed data.

    For each lambda in the grid, compute log-likelihood of observing the
    signal age distribution at mandate time. Pick the lambda maximising it.

    Args:
        signal_type: For logging.
        events:      List of {signal_age_at_mandate_days} — age when mandate was confirmed.
        lambda_grid: Candidate lambda values.
    Returns:
        Best lambda from grid.
    """
    if len(events) < 10:
        log.warning(
            "temporal_decay: only %d events for %s — using default lambda",
            len(events),
            signal_type,
        )
        return DEFAULT_LAMBDAS.get(signal_type, 0.01)

    ages = np.array([float(e.get("signal_age_at_mandate_days", 0)) for e in events])
    ages = ages[ages >= 0]

    if len(ages) == 0:
        return DEFAULT_LAMBDAS.get(signal_type, 0.01)

    best_lambda = lambda_grid[0]
    best_ll = float("-inf")

    for lam in lambda_grid:
        if lam < LAMBDA_FLOOR:
            continue
        # Log-likelihood of exponential distribution: sum(log(λ × exp(-λ × t)))
        ll = float(len(ages) * math.log(lam) - lam * ages.sum())
        if ll > best_ll:
            best_ll = ll
            best_lambda = lam

    # Enforce floor
    best_lambda = max(best_lambda, LAMBDA_FLOOR)

    # Enforce half-life floor (no decay in under 7 days)
    hl = half_life_from_lambda(best_lambda)
    if hl < HALF_LIFE_FLOOR_DAYS:
        best_lambda = lambda_from_half_life(HALF_LIFE_FLOOR_DAYS)

    log.info(
        "temporal_decay: calibrated %s → λ=%.4f (half-life=%.1f days)",
        signal_type,
        best_lambda,
        half_life_from_lambda(best_lambda),
    )
    return best_lambda


def build_default_decay_config_rows() -> list[dict[str, Any]]:
    """
    Build default signal_decay_config table rows from DEFAULT_LAMBDAS.
    Called during Phase 6 seeding — replaced by calibrated values post-training.
    """
    rows: list[dict[str, Any]] = []
    for signal_type, lam in DEFAULT_LAMBDAS.items():
        rows.append(
            {
                "signal_type": signal_type,
                "practice_area": "global",
                "lambda_value": lam,
                "half_life_days": half_life_from_lambda(lam),
                "calibrated": False,
                "source": "default_prior",
            }
        )
    return rows
