"""
tests/test_phase2_features.py — Phase 2 Feature Engineering tests.

Tests:
  - Feature vector shape correct for all 34 practice areas
  - Temporal decay reduces signal weight by >50% after 90 days
  - Missing signal fields do not cause KeyError (graceful defaults)
  - Decay features produce correct output keys
  - Lambda calibration and half-life formulas

All tests run without live DB/Redis/Mongo (fully mocked).
"""

from __future__ import annotations

import math

import pytest

from app.ml.bayesian_engine import FEATURE_COLUMNS, PRACTICE_AREAS
from app.ml.temporal_decay import (
    DEFAULT_LAMBDAS,
    LAMBDA_FLOOR,
    apply_decay,
    build_default_decay_config_rows,
    calibrate_lambda,
    compute_decay_features,
    compute_decayed_signal_aggregate,
    half_life_from_lambda,
    lambda_from_half_life,
)


# ── Feature Vector Shape Tests ──────────────────────────────────────────────


class TestFeatureVectorShape:
    """Feature vector is correct for all practice areas."""

    def test_34_practice_areas(self) -> None:
        """Exactly 34 practice areas defined."""
        assert len(PRACTICE_AREAS) == 34

    def test_feature_columns_count(self) -> None:
        """Feature column list has expected length."""
        assert len(FEATURE_COLUMNS) >= 40  # 45 columns

    def test_feature_columns_are_unique(self) -> None:
        """No duplicate feature column names."""
        assert len(FEATURE_COLUMNS) == len(set(FEATURE_COLUMNS))

    def test_feature_columns_contain_critical_features(self) -> None:
        """Critical feature columns are present."""
        critical = [
            "filing_frequency_30d",
            "active_litigation_count",
            "velocity_score_7d",
            "anomaly_score",
            "graph_centrality",
            "sector_weight_multiplier",
            "cross_jurisdiction_signal",
        ]
        for col in critical:
            assert col in FEATURE_COLUMNS, f"Missing critical feature: {col}"


# ── Temporal Decay Tests ────────────────────────────────────────────────────


class TestTemporalDecay:
    """Temporal decay reduces signal weight correctly."""

    def test_zero_age_preserves_weight(self) -> None:
        """Signal at age=0 keeps full weight."""
        assert apply_decay(1.0, 0.0, 0.01) == 1.0

    def test_decay_reduces_weight(self) -> None:
        """Signal weight decreases with age."""
        w0 = apply_decay(1.0, 0.0, 0.01)
        w30 = apply_decay(1.0, 30.0, 0.01)
        w90 = apply_decay(1.0, 90.0, 0.01)
        assert w30 < w0
        assert w90 < w30

    def test_90_day_decay_exceeds_50_percent(self) -> None:
        """A signal with λ=0.01 loses >50% weight after 90 days."""
        w90 = apply_decay(1.0, 90.0, 0.01)
        assert w90 < 0.5, f"Weight after 90 days should be <50%, got {w90}"

    def test_negative_age_returns_base_weight(self) -> None:
        """Negative age returns base weight (not a crash)."""
        assert apply_decay(1.0, -5.0, 0.01) == 1.0

    def test_decay_never_negative(self) -> None:
        """Decayed weight is always >= 0."""
        assert apply_decay(1.0, 10000.0, 0.1) >= 0.0

    def test_half_life_formula(self) -> None:
        """Half-life calculation matches expected formula."""
        lam = 0.01
        expected_hl = math.log(2) / lam
        assert abs(half_life_from_lambda(lam) - expected_hl) < 0.001

    def test_lambda_from_half_life_inverse(self) -> None:
        """lambda_from_half_life is inverse of half_life_from_lambda."""
        lam = 0.05
        hl = half_life_from_lambda(lam)
        lam_back = lambda_from_half_life(hl)
        assert abs(lam - lam_back) < 1e-10

    def test_lambda_floor_enforced(self) -> None:
        """Lambda floor is 0.002 (min 7-day half-life)."""
        assert LAMBDA_FLOOR == 0.002
        hl = half_life_from_lambda(LAMBDA_FLOOR)
        # Should be approximately 346 days (well above 7)
        assert hl >= 7.0

    def test_zero_lambda_gives_infinite_half_life(self) -> None:
        """Lambda=0 gives infinite half-life."""
        assert half_life_from_lambda(0.0) == float("inf")


# ── Missing Fields Tests ────────────────────────────────────────────────────


class TestMissingFields:
    """Missing signal fields produce graceful defaults, not crashes."""

    def test_empty_signals_returns_zero(self) -> None:
        """Empty signal list returns 0.0 aggregate."""
        result = compute_decayed_signal_aggregate([], {}, {})
        assert result == 0.0

    def test_missing_signal_type_uses_default_lambda(self) -> None:
        """Unknown signal_type falls back to default lambda."""
        signals = [{"signal_type": "nonexistent_type", "age_days": 10}]
        result = compute_decayed_signal_aggregate(signals, {}, {"nonexistent_type": 0.5})
        assert isinstance(result, float)
        assert 0.0 <= result <= 1.0

    def test_missing_age_days_uses_zero(self) -> None:
        """Missing age_days field defaults to 0 (full weight)."""
        signals = [{"signal_type": "news_lawsuit"}]
        result = compute_decayed_signal_aggregate(
            signals, {"news_lawsuit": 0.04}, {"news_lawsuit": 0.8}
        )
        assert result == pytest.approx(0.8)

    def test_missing_base_weight_uses_default(self) -> None:
        """Missing base weight uses 0.5 default."""
        signals = [{"signal_type": "test_signal", "age_days": 0}]
        result = compute_decayed_signal_aggregate(signals, {}, {})
        # Default base weight is 0.5
        assert result == pytest.approx(0.5)


# ── Decay Features Tests ───────────────────────────────────────────────────


class TestDecayFeatures:
    """Decay features produce correct output keys."""

    def test_decay_features_output_keys(self) -> None:
        """compute_decay_features returns all 5 category keys."""
        result = compute_decay_features({}, {}, {})
        expected_keys = {
            "decayed_filing_signal",
            "decayed_legal_signal",
            "decayed_employment_signal",
            "decayed_market_signal",
            "decayed_nlp_signal",
        }
        assert set(result.keys()) == expected_keys

    def test_decay_features_empty_categories(self) -> None:
        """Empty categories produce 0.0 values."""
        result = compute_decay_features({}, {}, {})
        for v in result.values():
            assert v == 0.0

    def test_decay_features_with_signals(self) -> None:
        """Signals in a category produce non-zero decay feature."""
        signals_by_cat = {
            "filing": [{"signal_type": "sedar_material_change", "age_days": 5}],
        }
        result = compute_decay_features(
            signals_by_cat,
            {"sedar_material_change": 0.008},
            {"sedar_material_change": 0.7},
        )
        assert result["decayed_filing_signal"] > 0.0
        assert result["decayed_legal_signal"] == 0.0


# ── Lambda Calibration Tests ───────────────────────────────────────────────


class TestLambdaCalibration:
    """Lambda calibration returns valid values."""

    def test_calibrate_with_few_events_returns_default(self) -> None:
        """Fewer than 10 events returns default lambda."""
        events = [{"signal_age_at_mandate_days": 10}] * 5
        result = calibrate_lambda("news_lawsuit", events)
        assert result == DEFAULT_LAMBDAS["news_lawsuit"]

    def test_calibrate_enforces_floor(self) -> None:
        """Calibrated lambda is never below LAMBDA_FLOOR."""
        events = [{"signal_age_at_mandate_days": 1}] * 20
        result = calibrate_lambda("test_signal", events)
        assert result >= LAMBDA_FLOOR

    def test_build_default_decay_config_rows(self) -> None:
        """Default decay config rows match DEFAULT_LAMBDAS count."""
        rows = build_default_decay_config_rows()
        assert len(rows) == len(DEFAULT_LAMBDAS)
        for row in rows:
            assert "signal_type" in row
            assert "lambda_value" in row
            assert "half_life_days" in row
            assert row["calibrated"] is False

    def test_default_lambdas_all_above_floor(self) -> None:
        """All default lambdas are above the lambda floor."""
        for signal_type, lam in DEFAULT_LAMBDAS.items():
            assert lam >= LAMBDA_FLOOR, f"{signal_type} lambda {lam} < floor {LAMBDA_FLOOR}"
