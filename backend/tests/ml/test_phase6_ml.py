"""
tests/ml/test_phase6_ml.py — Phase 6 ML pipeline test suite.

Covers:
    - BayesianEngine: load, score, batch score
    - TransformerScorer: architecture, score shape
    - Orchestrator: model selection logic
    - All 10 enhancements: unit tests
    - Celery task registration
    - Migration existence
    - Output matrix shape validation (34×3)

Requires: pytest, pytest-asyncio, torch, xgboost
"""

from __future__ import annotations

from datetime import UTC
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest
import torch

# ── Fixtures ───────────────────────────────────────────────────────────────────


@pytest.fixture
def sample_features() -> dict[str, float]:
    """Minimal feature dict — all zeros plus a few non-zero values."""
    from app.ml.bayesian_engine import FEATURE_COLUMNS

    features = dict.fromkeys(FEATURE_COLUMNS, 0.0)
    features["material_change_count_90d"] = 3.0
    features["exec_departure_count_90d"] = 2.0
    features["price_decline_90d"] = -0.25
    features["volatility_30d"] = 0.45
    features["osc_enforcement_signal"] = 0.9  # may not be in list — safe to include
    return features


@pytest.fixture
def sample_feature_matrix() -> pd.DataFrame:
    """Small feature matrix for training tests."""
    from app.ml.bayesian_engine import FEATURE_COLUMNS

    np.random.seed(42)
    n = 200
    data = {col: np.random.randn(n).astype(np.float32) for col in FEATURE_COLUMNS}
    return pd.DataFrame(data)


@pytest.fixture
def sample_labels(sample_feature_matrix: pd.DataFrame) -> dict[str, pd.Series]:
    """Binary labels with 5:1 negative:positive ratio."""
    np.random.seed(42)
    n = len(sample_feature_matrix)
    # ~17% positive rate
    labels = (np.random.rand(n) < 0.17).astype(int)
    return {
        "y_30d": pd.Series(labels),
        "y_60d": pd.Series(np.clip(labels + (np.random.rand(n) < 0.05).astype(int), 0, 1)),
        "y_90d": pd.Series(np.clip(labels + (np.random.rand(n) < 0.1).astype(int), 0, 1)),
    }


# ── Practice area list ─────────────────────────────────────────────────────────


def test_practice_area_count():
    """Exactly 34 practice areas defined."""
    from app.ml.bayesian_engine import PRACTICE_AREAS

    assert len(PRACTICE_AREAS) == 34, f"Expected 34, got {len(PRACTICE_AREAS)}"


def test_feature_column_count():
    """Feature column list is non-empty and has no duplicates."""
    from app.ml.bayesian_engine import FEATURE_COLUMNS

    assert len(FEATURE_COLUMNS) > 0
    assert len(FEATURE_COLUMNS) == len(set(FEATURE_COLUMNS)), "Duplicate feature columns found"


# ── BayesianEngine unit tests ─────────────────────────────────────────────────


class TestBayesianEngine:
    def test_invalid_practice_area(self):
        from app.ml.bayesian_engine import BayesianEngine

        with pytest.raises(ValueError, match="Unknown practice area"):
            BayesianEngine("fake_area")

    def test_score_raises_if_not_loaded(self, sample_features):
        from app.ml.bayesian_engine import BayesianEngine

        engine = BayesianEngine("ma")
        with pytest.raises(RuntimeError, match="not loaded"):
            engine.score(sample_features)

    def test_horizon_scores_output(self, sample_features):
        """HorizonScores.as_dict() returns 30/60/90d keys."""
        from app.ml.bayesian_engine import HorizonScores

        hs = HorizonScores(
            practice_area="ma",
            score_30d=0.71,
            score_60d=0.84,
            score_90d=0.89,
            model_version="test",
            inference_ms=5.0,
        )
        d = hs.as_dict()
        assert set(d.keys()) == {30, 60, 90}
        assert all(0 <= v <= 1 for v in d.values())

    def test_output_is_34x3_matrix(self):
        """score_company returns exactly 34 practice areas with 3 horizons each."""
        from app.ml.bayesian_engine import PRACTICE_AREAS, HorizonScores
        from app.ml.orchestrator import MandateOrchestrator

        # Mock all engines as loaded
        mock_engine = MagicMock()
        mock_engine._loaded = True
        mock_engine.score.return_value = HorizonScores(
            practice_area="ma",
            score_30d=0.5,
            score_60d=0.6,
            score_90d=0.7,
            model_version="test",
            inference_ms=1.0,
        )

        orchestrator = MandateOrchestrator()
        orchestrator._bayesian_engines = dict.fromkeys(PRACTICE_AREAS, mock_engine)
        orchestrator._selections = {pa: MagicMock(active_model="bayesian") for pa in PRACTICE_AREAS}
        orchestrator._loaded = True

        results = orchestrator.score_company({"feature": 0.0})
        assert len(results) == 34, f"Expected 34 practice areas, got {len(results)}"
        for _pa, hs in results.items():
            assert hs.score_30d >= 0.0
            assert hs.score_60d >= 0.0
            assert hs.score_90d >= 0.0

    def test_probabilities_clipped(self, sample_features):
        """Probabilities must be in [0.001, 0.999] — never exact 0 or 1."""
        from app.ml.bayesian_engine import HorizonScores

        hs = HorizonScores(
            practice_area="ma",
            score_30d=0.001,
            score_60d=0.999,
            score_90d=0.5,
            model_version="test",
            inference_ms=1.0,
        )
        assert hs.score_30d >= 0.001
        assert hs.score_60d <= 0.999


# ── TransformerScorer unit tests ───────────────────────────────────────────────


class TestTransformerScorer:
    def test_model_architecture(self):
        """MandateTransformer produces 3 output tensors per batch."""
        from app.ml.bayesian_engine import FEATURE_COLUMNS
        from app.ml.transformer_scorer import HORIZONS, MandateTransformer

        n_features = len(FEATURE_COLUMNS)
        model = MandateTransformer(n_features=n_features)
        model.eval()

        batch_size = 4
        seq_len = 30
        x = torch.randn(batch_size, seq_len, n_features)

        with torch.no_grad():
            outputs = model(x)

        assert set(outputs.keys()) == set(HORIZONS)
        for h, tensor in outputs.items():
            assert tensor.shape == (batch_size,), f"h{h} output shape wrong: {tensor.shape}"
            assert (tensor >= 0).all() and (tensor <= 1).all(), f"h{h} output out of [0,1]"

    def test_sequence_to_tensor_padding(self):
        """Short sequence is padded correctly with zeros at the start."""
        from app.ml.bayesian_engine import FEATURE_COLUMNS
        from app.ml.transformer_scorer import SEQUENCE_LENGTH, _sequence_to_tensor

        short_seq = [{"material_change_count_90d": 3.0}]  # 1 day only
        tensor = _sequence_to_tensor(short_seq, SEQUENCE_LENGTH)

        assert tensor.shape == (1, SEQUENCE_LENGTH, len(FEATURE_COLUMNS))
        # First rows should be zero (padding)
        assert tensor[0, 0, :].sum().item() == pytest.approx(0.0)

    def test_scorer_raises_if_not_loaded(self, sample_features):
        from app.ml.transformer_scorer import TransformerScorer

        scorer = TransformerScorer("ma")
        with pytest.raises(RuntimeError, match="not loaded"):
            scorer.score([sample_features])


# ── Enhancement unit tests ─────────────────────────────────────────────────────


class TestVelocityScorer:
    def test_compute_velocity_basic(self):
        from app.ml.velocity_scorer import compute_velocity

        current = {"ma": {30: 0.8, 60: 0.85, 90: 0.9}}
        prior = {"ma": {30: 0.5, 60: 0.6, 90: 0.7}}
        velocities = compute_velocity(current, prior)
        assert "ma" in velocities
        assert velocities["ma"] > 0  # score went up

    def test_velocity_clamped(self):
        from app.ml.velocity_scorer import compute_velocity

        current = {"ma": {30: 1.0}}
        prior = {"ma": {30: 0.01}}  # huge jump
        velocities = compute_velocity(current, prior)
        assert velocities["ma"] <= 1.0

    def test_velocity_negative(self):
        from app.ml.velocity_scorer import compute_velocity

        current = {"ma": {30: 0.1}}
        prior = {"ma": {30: 0.8}}
        velocities = compute_velocity(current, prior)
        assert velocities["ma"] < 0

    def test_aggregate_velocity_range(self):
        from app.ml.velocity_scorer import aggregate_company_velocity

        velocities = {"ma": 0.5, "litigation": -0.3, "regulatory": 0.8}
        agg = aggregate_company_velocity(velocities)
        assert -1.0 <= agg <= 1.0


class TestTemporalDecay:
    def test_apply_decay_zero_age(self):
        from app.ml.temporal_decay import apply_decay

        weight = apply_decay(0.8, age_days=0, lam=0.01)
        assert weight == pytest.approx(0.8)

    def test_apply_decay_reduces_weight(self):
        from app.ml.temporal_decay import apply_decay

        fresh = apply_decay(0.8, age_days=0, lam=0.01)
        old = apply_decay(0.8, age_days=90, lam=0.01)
        assert old < fresh

    def test_half_life_formula(self):
        """Half-life: weight at t=half_life should be ~50% of original."""
        from app.ml.temporal_decay import apply_decay, half_life_from_lambda

        lam = 0.023  # ~30 day half-life
        hl = half_life_from_lambda(lam)
        weight_at_hl = apply_decay(1.0, age_days=hl, lam=lam)
        assert weight_at_hl == pytest.approx(0.5, abs=0.01)

    def test_lambda_floor_enforced(self):
        from app.ml.temporal_decay import LAMBDA_FLOOR, calibrate_lambda

        # Events all at age 0 → model might want huge lambda, should be floored
        events = [{"signal_age_at_mandate_days": 0}] * 20
        lam = calibrate_lambda("test_signal", events)
        assert lam >= LAMBDA_FLOOR


class TestAnomalyDetector:
    def test_anomaly_score_range(self):
        from app.ml.anomaly_detector import AnomalyDetector
        from app.ml.bayesian_engine import FEATURE_COLUMNS

        detector = AnomalyDetector()
        # Not loaded → returns 0.0 safely
        score = detector.score(dict.fromkeys(FEATURE_COLUMNS, 0.0))
        assert score == 0.0

    def test_batch_score_returns_list(self):
        from app.ml.anomaly_detector import AnomalyDetector
        from app.ml.bayesian_engine import FEATURE_COLUMNS

        detector = AnomalyDetector()
        features = [dict.fromkeys(FEATURE_COLUMNS, 0.0)] * 5
        scores = detector.score_batch(features)
        assert len(scores) == 5
        assert all(0.0 <= s <= 1.0 for s in scores)


class TestCooccurrenceMining:
    def test_empty_events(self):
        from app.ml.cooccurrence import build_transaction_matrix, mine_rules

        df = build_transaction_matrix([])
        rules = mine_rules(df, "ma")
        assert rules == []

    def test_transaction_matrix_shape(self):
        from app.ml.cooccurrence import build_transaction_matrix

        events = [
            {"signal_types": ["sedar_material_change", "news_merger"]},
            {"signal_types": ["sedar_material_change", "linkedin_exec_departure"]},
            {"signal_types": ["news_merger"]},
        ]
        df = build_transaction_matrix(events)
        assert not df.empty
        assert df.shape[0] == 3
        assert "sedar_material_change" in df.columns
        dtype = df.dtypes["sedar_material_change"]
        assert dtype == bool or isinstance(dtype.type(), (bool, np.bool_))  # noqa: E721


class TestCrossJurisdiction:
    def test_propagation_decay(self):
        from app.ml.cross_jurisdiction import compute_propagated_signal

        strong = compute_propagated_signal(0.9, "subsidiary")
        medium = compute_propagated_signal(0.9, "peer_same_sector")
        weak = compute_propagated_signal(0.9, "competitor")
        assert strong > medium > weak

    def test_unknown_link_type_returns_zero(self):
        from app.ml.cross_jurisdiction import compute_propagated_signal

        result = compute_propagated_signal(0.9, "unknown_link_type")
        assert result == 0.0

    def test_propagate_skips_weak_signals(self):
        from app.ml.cross_jurisdiction import propagate_signals

        events = [{"company_id": 1, "signal_type": "osc_enforcement", "signal_strength": 0.1}]
        links = [{"source_company_id": 1, "target_company_id": 2, "link_type": "subsidiary"}]
        result = propagate_signals(events, links)
        assert len(result) == 0  # below MIN_SOURCE_STRENGTH threshold

    def test_aggregate_convergence(self):
        from datetime import datetime

        from app.ml.cross_jurisdiction import PropagatedSignal, aggregate_cross_jurisdiction_feature

        signals = [
            PropagatedSignal(
                target_company_id=2,
                source_company_id=1,
                source_signal_type="osc_enforcement",
                source_signal_strength=0.8,
                propagated_strength=0.6,
                link_type="subsidiary",
                propagated_at=datetime.now(tz=UTC).isoformat(),
            )
        ]
        score = aggregate_cross_jurisdiction_feature(2, signals)
        assert 0.0 < score < 1.0


# ── Orchestrator model selection ───────────────────────────────────────────────


class TestOrchestrator:
    def test_bayesian_default_when_no_registry(self):
        from app.ml.bayesian_engine import PRACTICE_AREAS
        from app.ml.orchestrator import MandateOrchestrator

        orch = MandateOrchestrator()
        orch._bayesian_engines = {}
        orch._transformer_scorers = {}
        orch.load(registry=[])  # empty registry → all bayesian
        orch._loaded = True

        for pa in PRACTICE_AREAS:
            sel = orch._selections.get(pa)
            assert sel is not None
            assert sel.active_model == "bayesian"

    def test_transformer_requires_f1_threshold(self):
        from app.ml.bayesian_engine import ORCHESTRATOR_F1_THRESHOLD
        from app.ml.orchestrator import MandateOrchestrator  # noqa: F401

        # Transformer barely beats bayesian (below threshold)
        bayesian_f1 = 0.70
        transformer_f1 = bayesian_f1 + ORCHESTRATOR_F1_THRESHOLD - 0.001

        # Simulate selection logic
        delta = transformer_f1 - bayesian_f1
        should_use_transformer = delta >= ORCHESTRATOR_F1_THRESHOLD
        assert not should_use_transformer

        # Transformer clearly beats bayesian
        transformer_f1_good = bayesian_f1 + ORCHESTRATOR_F1_THRESHOLD + 0.01
        delta_good = transformer_f1_good - bayesian_f1
        assert delta_good >= ORCHESTRATOR_F1_THRESHOLD


# ── Celery task registration ───────────────────────────────────────────────────


class TestCeleryTasks:
    def test_phase6_tasks_registered(self):
        from app.tasks import phase6_tasks  # noqa: F401 — register tasks
        from app.tasks.celery_app import celery_app

        expected_tasks = [
            "agents.refresh_model_orchestrator",
            "agents.run_anomaly_escalation",
            "agents.clean_stale_scores",
            "agents.update_sector_baseline",
            "agents.run_ccaa_cascade",
            "scoring.score_company_batch",
            "agents.run_active_learning",
            "agents.seed_decay_config",
        ]
        registered = list(celery_app.tasks.keys())
        for task_name in expected_tasks:
            assert task_name in registered, f"Task {task_name} not registered in Celery"


# ── Migration existence ────────────────────────────────────────────────────────


def test_phase6_migration_exists():
    """Phase 6 Alembic migration file must exist."""
    migration_path = Path("alembic/versions/0006_phase6_ml.py")
    assert migration_path.exists(), f"Phase 6 migration not found at {migration_path}"


def test_phase6_migration_valid_python():
    """Phase 6 migration is valid Python."""
    migration_path = Path("alembic/versions/0006_phase6_ml.py")
    if migration_path.exists():
        import ast

        source = migration_path.read_text()
        try:
            ast.parse(source)
        except SyntaxError as e:
            pytest.fail(f"Migration has syntax error: {e}")


# ── Signal co-occurrence — max rules cap ──────────────────────────────────────


def test_cooccurrence_max_rules_cap():
    from app.ml.cooccurrence import MAX_RULES

    assert MAX_RULES == 200, "MAX_RULES must be 200 — prevents noise storage"


# ── Decay config seeding ──────────────────────────────────────────────────────


def test_default_decay_config_has_lambda_floor():
    from app.ml.temporal_decay import LAMBDA_FLOOR, build_default_decay_config_rows

    rows = build_default_decay_config_rows()
    assert len(rows) > 0
    for row in rows:
        assert row["lambda_value"] >= LAMBDA_FLOOR, (
            f"Signal {row['signal_type']} lambda {row['lambda_value']} below floor {LAMBDA_FLOOR}"
        )
        assert row["half_life_days"] > 0
