"""
Phase 3 — Ground Truth Pipeline tests.

Tests for:
  - constants (practice area mappings, positive signal types)
  - RetrospectiveLabeler (Agent 016) — mocked DB
  - NegativeSampler (Agent 017) — mocked DB
  - GroundTruthPipeline — mocked DB
  - Route serializer functions

All tests run without a live database.
Known env limitation: pymongo/cryptography pyo3 conflict requires sys.modules
mocking for any module that transitively imports app.config or app.database.
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone
from types import ModuleType
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch


# ── Inject stubs for problematic transitively-imported modules ─────────────────
# This prevents the pyo3/cryptography panic caused by the pymongo conflict
# (same known env issue documented in Phase 1B commit).

def _inject_module_stubs() -> None:
    """
    Inject fake modules to break the cryptography import chain.

    IMPORTANT: Do NOT stub 'app' itself — it must remain the real package
    so that subpackages (app.ground_truth, app.models, etc.) can be discovered.
    Only stub the leaf modules that transitively pull in cryptography.
    """
    # Stub app.config (pulls in pydantic-settings → cryptography on this env)
    cfg_mod = ModuleType("app.config")
    settings_stub = MagicMock()
    settings_stub.environment = "development"
    settings_stub.is_development = True
    settings_stub.is_production = False
    settings_stub.database_url = "postgresql+asyncpg://test:test@localhost/test"
    settings_stub.mongodb_url = "mongodb://localhost:27017"
    settings_stub.mongodb_db_name = "oracle_test"
    settings_stub.mongodb_max_pool_size = 10
    settings_stub.redis_url = "redis://localhost:6379/0"
    settings_stub.celery_broker_url = "redis://localhost:6379/0"
    settings_stub.celery_result_backend = "redis://localhost:6379/1"
    settings_stub.celery_task_time_limit = 3600
    settings_stub.celery_task_soft_time_limit = 3300
    settings_stub.celery_worker_concurrency = 4
    settings_stub.db_pool_size = 5
    settings_stub.db_max_overflow = 2
    settings_stub.db_pool_timeout = 10
    settings_stub.db_pool_recycle = 300
    settings_stub.db_echo = False
    settings_stub.log_level = "INFO"
    settings_stub.allowed_origins = ["http://localhost:3000"]
    settings_stub.sentry_dsn = None
    settings_stub.models_dir = "/tmp/models"
    settings_stub.data_dir = "/tmp/data"
    cfg_mod.get_settings = lambda: settings_stub  # type: ignore[attr-defined]
    cfg_mod.Settings = MagicMock  # type: ignore[attr-defined]
    sys.modules.setdefault("app.config", cfg_mod)

    # Stub app.database — Base MUST be a real DeclarativeBase subclass
    # so that ORM model class bodies execute correctly.
    import sqlalchemy.orm as _orm

    class _Base(_orm.DeclarativeBase):
        pass

    db_mod = ModuleType("app.database")
    db_mod.Base = _Base  # type: ignore[attr-defined]
    db_mod.AsyncSessionLocal = MagicMock()  # type: ignore[attr-defined]
    db_mod.get_db = MagicMock()  # type: ignore[attr-defined]
    db_mod.get_mongo_db = MagicMock()  # type: ignore[attr-defined]
    db_mod.get_mongo_db_dep = MagicMock()  # type: ignore[attr-defined]
    db_mod.check_db_connection = AsyncMock(return_value=True)  # type: ignore[attr-defined]
    db_mod.check_mongo_connection = AsyncMock(return_value=True)  # type: ignore[attr-defined]
    db_mod.dispose_engine = AsyncMock()  # type: ignore[attr-defined]
    db_mod.close_mongo_connection = AsyncMock()  # type: ignore[attr-defined]
    sys.modules.setdefault("app.database", db_mod)

    # Stub app.auth.models (User) and app.auth.dependencies
    for name in ("app.auth", "app.auth.models", "app.auth.dependencies"):
        m = ModuleType(name)
        m.User = MagicMock()  # type: ignore[attr-defined]
        m.require_partner = MagicMock()  # type: ignore[attr-defined]
        m.require_admin = MagicMock()  # type: ignore[attr-defined]
        m.require_auth = MagicMock()  # type: ignore[attr-defined]
        sys.modules.setdefault(name, m)


_inject_module_stubs()


# ── Helpers ────────────────────────────────────────────────────────────────────


def _make_mock_db_with_rows(rows: list[tuple[Any, ...]]) -> AsyncMock:
    """Create a mock AsyncSession that returns given rows on execute."""
    result_mock = MagicMock()
    result_mock.fetchall.return_value = rows
    result_mock.scalar_one.return_value = len(rows)
    result_mock.scalar_one_or_none.return_value = None
    result_mock.scalars.return_value.all.return_value = []
    db = AsyncMock()
    db.execute = AsyncMock(return_value=result_mock)
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.rollback = AsyncMock()
    db.commit = AsyncMock()
    return db


def _run(coro: Any) -> Any:
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


# ── Constants Tests ────────────────────────────────────────────────────────────


class TestConstants:
    def test_all_34_practice_areas_present(self) -> None:
        from app.ground_truth.constants import PRACTICE_AREAS

        assert len(PRACTICE_AREAS) == 34

    def test_no_duplicate_practice_areas(self) -> None:
        from app.ground_truth.constants import PRACTICE_AREAS

        assert len(PRACTICE_AREAS) == len(set(PRACTICE_AREAS))

    def test_positive_signal_types_nonempty(self) -> None:
        from app.ground_truth.constants import POSITIVE_SIGNAL_TYPES

        assert len(POSITIVE_SIGNAL_TYPES) > 0

    def test_signal_type_maps_to_known_practice_areas(self) -> None:
        from app.ground_truth.constants import (
            PRACTICE_AREAS,
            SIGNAL_TYPE_TO_PRACTICE_AREAS,
        )

        pa_set = set(PRACTICE_AREAS)
        for signal_type, practice_areas in SIGNAL_TYPE_TO_PRACTICE_AREAS.items():
            for pa in practice_areas:
                assert pa in pa_set, (
                    f"Unknown practice area '{pa}' in mapping for '{signal_type}'"
                )

    def test_insolvency_signals_map_correctly(self) -> None:
        from app.ground_truth.constants import SIGNAL_TYPE_TO_PRACTICE_AREAS

        assert "Insolvency/Restructuring" in SIGNAL_TYPE_TO_PRACTICE_AREAS["ccaa_filing"]
        assert "Insolvency/Restructuring" in SIGNAL_TYPE_TO_PRACTICE_AREAS["osb_insolvency"]

    def test_data_breach_maps_to_privacy_and_data(self) -> None:
        from app.ground_truth.constants import SIGNAL_TYPE_TO_PRACTICE_AREAS

        pas = SIGNAL_TYPE_TO_PRACTICE_AREAS["data_breach"]
        assert "Privacy/Cybersecurity" in pas
        assert "Data Privacy & Technology" in pas

    def test_horizons_are_30_60_90(self) -> None:
        from app.ground_truth.constants import HORIZONS

        assert HORIZONS == [30, 60, 90]

    def test_positive_signal_types_matches_keys(self) -> None:
        from app.ground_truth.constants import (
            POSITIVE_SIGNAL_TYPES,
            SIGNAL_TYPE_TO_PRACTICE_AREAS,
        )

        assert POSITIVE_SIGNAL_TYPES == frozenset(SIGNAL_TYPE_TO_PRACTICE_AREAS.keys())

    def test_negative_signal_types_disjoint_from_positive(self) -> None:
        from app.ground_truth.constants import (
            NEGATIVE_SIGNAL_TYPES,
            POSITIVE_SIGNAL_TYPES,
        )

        overlap = POSITIVE_SIGNAL_TYPES & NEGATIVE_SIGNAL_TYPES
        assert len(overlap) == 0, f"Overlap between positive and negative types: {overlap}"

    def test_default_confidence_is_float(self) -> None:
        from app.ground_truth.constants import DEFAULT_LABEL_CONFIDENCE

        assert isinstance(DEFAULT_LABEL_CONFIDENCE, float)
        assert 0.0 < DEFAULT_LABEL_CONFIDENCE <= 1.0

    def test_max_negative_samples_positive_int(self) -> None:
        from app.ground_truth.constants import MAX_NEGATIVE_SAMPLES_PER_SECTOR

        assert isinstance(MAX_NEGATIVE_SAMPLES_PER_SECTOR, int)
        assert MAX_NEGATIVE_SAMPLES_PER_SECTOR > 0


# ── ORM Model Tests ────────────────────────────────────────────────────────────


class TestLabelingRunModel:
    def test_total_labels_property(self) -> None:
        from app.models.ground_truth import LabelingRun

        run = LabelingRun()
        run.positive_labels_created = 10
        run.negative_labels_created = 20
        assert run.total_labels == 30

    def test_total_labels_zero_when_empty(self) -> None:
        from app.models.ground_truth import LabelingRun

        run = LabelingRun()
        run.positive_labels_created = 0
        run.negative_labels_created = 0
        assert run.total_labels == 0

    def test_duration_seconds_none_when_incomplete(self) -> None:
        from app.models.ground_truth import LabelingRun

        run = LabelingRun()
        run.started_at = None
        run.completed_at = None
        assert run.duration_seconds is None

    def test_duration_seconds_calculated_correctly(self) -> None:
        from datetime import timedelta

        from app.models.ground_truth import LabelingRun

        run = LabelingRun()
        run.started_at = datetime(2026, 3, 24, 10, 0, 0, tzinfo=timezone.utc)
        run.completed_at = run.started_at + timedelta(seconds=150)
        assert run.duration_seconds == 150.0

    def test_duration_seconds_none_when_only_start(self) -> None:
        from app.models.ground_truth import LabelingRun

        run = LabelingRun()
        run.started_at = datetime(2026, 3, 24, 10, 0, 0, tzinfo=timezone.utc)
        run.completed_at = None
        assert run.duration_seconds is None


class TestGroundTruthEnums:
    def test_label_type_values(self) -> None:
        from app.models.ground_truth import LabelType

        assert LabelType.positive == "positive"
        assert LabelType.negative == "negative"
        assert LabelType.uncertain == "uncertain"

    def test_run_type_values(self) -> None:
        from app.models.ground_truth import RunType

        assert RunType.retrospective == "retrospective"
        assert RunType.negative_sampling == "negative_sampling"
        assert RunType.full == "full"

    def test_run_status_values(self) -> None:
        from app.models.ground_truth import RunStatus

        assert RunStatus.running == "running"
        assert RunStatus.completed == "completed"
        assert RunStatus.failed == "failed"

    def test_label_source_values(self) -> None:
        from app.models.ground_truth import LabelSource

        assert LabelSource.retrospective == "retrospective"
        assert LabelSource.manual == "manual"
        assert LabelSource.active_learning == "active_learning"


# ── Retrospective Labeler Tests ────────────────────────────────────────────────


class TestRetrospectiveLabeler:
    def test_no_signals_returns_no_labels(self) -> None:
        from app.ground_truth.labeler import RetrospectiveLabeler

        db = _make_mock_db_with_rows([])
        labeler = RetrospectiveLabeler()
        now = datetime(2026, 3, 24, 12, 0, 0, tzinfo=timezone.utc)
        labels = _run(labeler.label_company(company_id=1, run_id=1, now=now, db=db))
        assert labels == []

    def test_positive_signal_generates_label(self) -> None:
        from app.ground_truth.labeler import RetrospectiveLabeler

        db = _make_mock_db_with_rows([(42, "ccaa_filing")])
        labeler = RetrospectiveLabeler()
        now = datetime(2026, 3, 24, 12, 0, 0, tzinfo=timezone.utc)
        labels = _run(labeler.label_company(company_id=5, run_id=1, now=now, db=db))

        # ccaa_filing → Insolvency/Restructuring, across 3 horizons
        assert len(labels) == 3
        for lbl in labels:
            assert lbl.label_type == "positive"
            assert lbl.practice_area == "Insolvency/Restructuring"
            assert lbl.company_id == 5

    def test_label_contains_evidence_ids(self) -> None:
        from app.ground_truth.labeler import RetrospectiveLabeler

        db = _make_mock_db_with_rows([(99, "insolvency_filing")])
        labeler = RetrospectiveLabeler()
        now = datetime(2026, 3, 24, 12, 0, 0, tzinfo=timezone.utc)
        labels = _run(labeler.label_company(company_id=1, run_id=1, now=now, db=db))
        assert all(99 in (lbl.evidence_signal_ids or []) for lbl in labels)

    def test_horizon_days_set_correctly(self) -> None:
        from app.ground_truth.labeler import RetrospectiveLabeler

        db = _make_mock_db_with_rows([(1, "enforcement_action")])
        labeler = RetrospectiveLabeler()
        now = datetime(2026, 3, 24, 12, 0, 0, tzinfo=timezone.utc)
        labels = _run(labeler.label_company(company_id=1, run_id=1, now=now, db=db))
        horizons = sorted({lbl.horizon_days for lbl in labels})
        assert horizons == [30, 60, 90]

    def test_db_error_returns_empty(self) -> None:
        from app.ground_truth.labeler import RetrospectiveLabeler

        db = AsyncMock()
        db.execute = AsyncMock(side_effect=Exception("DB connection failed"))
        labeler = RetrospectiveLabeler()
        now = datetime(2026, 3, 24, 12, 0, 0, tzinfo=timezone.utc)
        labels = _run(labeler.label_company(company_id=1, run_id=1, now=now, db=db))
        assert labels == []

    def test_multi_practice_area_signal_creates_multiple_labels(self) -> None:
        from app.ground_truth.labeler import RetrospectiveLabeler

        # receivership maps to Insolvency/Restructuring + Banking/Finance
        db = _make_mock_db_with_rows([(10, "receivership")])
        labeler = RetrospectiveLabeler()
        now = datetime(2026, 3, 24, 12, 0, 0, tzinfo=timezone.utc)
        labels = _run(labeler.label_company(company_id=1, run_id=1, now=now, db=db))

        practice_areas = {lbl.practice_area for lbl in labels}
        assert "Insolvency/Restructuring" in practice_areas
        assert "Banking/Finance" in practice_areas

    def test_batch_run_returns_summary(self) -> None:
        from app.ground_truth.labeler import RetrospectiveLabeler

        db = _make_mock_db_with_rows([(1, "ccaa_filing")])
        labeler = RetrospectiveLabeler()
        now = datetime(2026, 3, 24, 12, 0, 0, tzinfo=timezone.utc)
        result = _run(labeler.run_batch(run_id=1, company_ids=[1, 2], db=db, now=now))
        assert "companies_processed" in result
        assert result["companies_processed"] == 2
        assert "positive_labels_created" in result
        assert "errors" in result

    def test_get_all_company_ids_returns_list(self) -> None:
        from app.ground_truth.labeler import RetrospectiveLabeler

        db = _make_mock_db_with_rows([(1,), (2,), (3,)])
        labeler = RetrospectiveLabeler()
        ids = _run(labeler.get_all_company_ids(db))
        assert ids == [1, 2, 3]

    def test_get_all_company_ids_db_error_returns_empty(self) -> None:
        from app.ground_truth.labeler import RetrospectiveLabeler

        db = AsyncMock()
        db.execute = AsyncMock(side_effect=Exception("DB error"))
        labeler = RetrospectiveLabeler()
        ids = _run(labeler.get_all_company_ids(db))
        assert ids == []

    def test_confidence_score_set_to_default(self) -> None:
        from app.ground_truth.constants import DEFAULT_LABEL_CONFIDENCE
        from app.ground_truth.labeler import RetrospectiveLabeler

        db = _make_mock_db_with_rows([(1, "ccaa_filing")])
        labeler = RetrospectiveLabeler()
        now = datetime(2026, 3, 24, 12, 0, 0, tzinfo=timezone.utc)
        labels = _run(labeler.label_company(company_id=1, run_id=1, now=now, db=db))
        for lbl in labels:
            assert lbl.confidence_score == DEFAULT_LABEL_CONFIDENCE

    def test_label_source_is_retrospective(self) -> None:
        from app.ground_truth.labeler import RetrospectiveLabeler

        db = _make_mock_db_with_rows([(1, "enforcement_action")])
        labeler = RetrospectiveLabeler()
        now = datetime(2026, 3, 24, 12, 0, 0, tzinfo=timezone.utc)
        labels = _run(labeler.label_company(company_id=1, run_id=1, now=now, db=db))
        for lbl in labels:
            assert lbl.label_source == "retrospective"

    def test_is_validated_false_by_default(self) -> None:
        from app.ground_truth.labeler import RetrospectiveLabeler

        db = _make_mock_db_with_rows([(1, "enforcement_action")])
        labeler = RetrospectiveLabeler()
        now = datetime(2026, 3, 24, 12, 0, 0, tzinfo=timezone.utc)
        labels = _run(labeler.label_company(company_id=1, run_id=1, now=now, db=db))
        for lbl in labels:
            assert lbl.is_validated is False


# ── Negative Sampler Tests ─────────────────────────────────────────────────────


class TestNegativeSampler:
    def test_no_candidates_returns_zero_labels(self) -> None:
        from app.ground_truth.negative_sampler import NegativeSampler

        db = _make_mock_db_with_rows([])
        sampler = NegativeSampler()
        now = datetime(2026, 3, 24, 12, 0, 0, tzinfo=timezone.utc)
        result = _run(sampler.sample(run_id=1, db=db, now=now))
        assert result["negative_labels_created"] == 0

    def test_creates_negative_label_for_candidate(self) -> None:
        from app.ground_truth.negative_sampler import NegativeSampler

        db = _make_mock_db_with_rows([(7, "Technology", [1, 2])])
        sampler = NegativeSampler(seed=0)
        now = datetime(2026, 3, 24, 12, 0, 0, tzinfo=timezone.utc)
        result = _run(sampler.sample(run_id=1, db=db, now=now))
        assert result["negative_labels_created"] == 1

    def test_sector_cap_limits_samples(self) -> None:
        from app.ground_truth.negative_sampler import NegativeSampler

        rows = [(i, "Finance", [i * 10]) for i in range(1, 11)]
        db = _make_mock_db_with_rows(rows)
        sampler = NegativeSampler(seed=42)
        now = datetime(2026, 3, 24, 12, 0, 0, tzinfo=timezone.utc)
        result = _run(sampler.sample(run_id=1, db=db, now=now, max_per_sector=3))
        assert result["negative_labels_created"] == 3

    def test_multiple_sectors_sampled_independently(self) -> None:
        from app.ground_truth.negative_sampler import NegativeSampler

        rows = [(i, "Finance", [i]) for i in range(1, 6)]
        rows += [(i + 10, "Mining", [i + 10]) for i in range(1, 6)]
        db = _make_mock_db_with_rows(rows)
        sampler = NegativeSampler(seed=42)
        now = datetime(2026, 3, 24, 12, 0, 0, tzinfo=timezone.utc)
        result = _run(sampler.sample(run_id=1, db=db, now=now, max_per_sector=3))
        assert result["negative_labels_created"] == 6

    def test_negative_label_practice_area_is_none(self) -> None:
        from app.ground_truth.negative_sampler import NegativeSampler
        from app.models.ground_truth import GroundTruthLabel

        db = _make_mock_db_with_rows([(1, "Energy", [5])])
        sampler = NegativeSampler(seed=0)
        now = datetime(2026, 3, 24, 12, 0, 0, tzinfo=timezone.utc)

        added_labels: list[GroundTruthLabel] = []
        db.add = lambda lbl: added_labels.append(lbl)

        _run(sampler.sample(run_id=1, db=db, now=now))
        assert len(added_labels) == 1
        assert added_labels[0].practice_area is None
        assert added_labels[0].label_type == "negative"

    def test_sectors_sampled_count_returned(self) -> None:
        from app.ground_truth.negative_sampler import NegativeSampler

        rows = [(1, "Finance", [1]), (2, "Mining", [2])]
        db = _make_mock_db_with_rows(rows)
        sampler = NegativeSampler(seed=0)
        now = datetime(2026, 3, 24, 12, 0, 0, tzinfo=timezone.utc)
        result = _run(sampler.sample(run_id=1, db=db, now=now))
        assert result["sectors_sampled"] == 2

    def test_no_errors_on_clean_run(self) -> None:
        from app.ground_truth.negative_sampler import NegativeSampler

        db = _make_mock_db_with_rows([(1, "Finance", [1])])
        sampler = NegativeSampler(seed=0)
        now = datetime(2026, 3, 24, 12, 0, 0, tzinfo=timezone.utc)
        result = _run(sampler.sample(run_id=1, db=db, now=now))
        assert result["errors"] == 0

    def test_unknown_sector_treated_as_unknown(self) -> None:
        from app.ground_truth.negative_sampler import NegativeSampler

        rows = [(1, None, [1])]  # None sector → "Unknown"
        db = _make_mock_db_with_rows(rows)
        sampler = NegativeSampler(seed=0)
        now = datetime(2026, 3, 24, 12, 0, 0, tzinfo=timezone.utc)
        result = _run(sampler.sample(run_id=1, db=db, now=now))
        assert result["negative_labels_created"] == 1


# ── Pipeline Tests ─────────────────────────────────────────────────────────────


class TestGroundTruthPipeline:
    def test_get_run_by_id_not_found(self) -> None:
        from app.ground_truth.pipeline import GroundTruthPipeline

        pipeline = GroundTruthPipeline()
        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=result_mock)

        run = _run(pipeline.get_run_by_id(run_id=9999, db=db))
        assert run is None

    def test_get_run_by_id_db_error_returns_none(self) -> None:
        from app.ground_truth.pipeline import GroundTruthPipeline

        pipeline = GroundTruthPipeline()
        db = AsyncMock()
        db.execute = AsyncMock(side_effect=Exception("DB error"))

        run = _run(pipeline.get_run_by_id(run_id=1, db=db))
        assert run is None

    def test_get_run_by_id_found(self) -> None:
        from app.ground_truth.pipeline import GroundTruthPipeline
        from app.models.ground_truth import LabelingRun

        pipeline = GroundTruthPipeline()
        db = AsyncMock()
        expected_run = LabelingRun()
        expected_run.id = 5
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = expected_run
        db.execute = AsyncMock(return_value=result_mock)

        run = _run(pipeline.get_run_by_id(run_id=5, db=db))
        assert run is expected_run


# ── Route Serializer Tests ─────────────────────────────────────────────────────


class TestRouteSerializers:
    def test_label_to_dict_structure(self) -> None:
        from app.models.ground_truth import GroundTruthLabel
        from app.routes.ground_truth import _label_to_dict

        label = GroundTruthLabel()
        label.id = 1
        label.company_id = 10
        label.label_type = "positive"
        label.practice_area = "Tax"
        label.horizon_days = 30
        label.label_source = "retrospective"
        label.confidence_score = 0.75
        label.is_validated = False
        label.signal_window_start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        label.signal_window_end = datetime(2026, 2, 1, tzinfo=timezone.utc)
        label.evidence_signal_ids = [1, 2, 3]
        label.labeling_run_id = 5
        label.created_at = datetime(2026, 3, 1, tzinfo=timezone.utc)

        d = _label_to_dict(label)
        assert d["id"] == 1
        assert d["company_id"] == 10
        assert d["label_type"] == "positive"
        assert d["practice_area"] == "Tax"
        assert d["horizon_days"] == 30
        assert d["confidence_score"] == 0.75
        assert d["is_validated"] is False
        assert d["evidence_signal_ids"] == [1, 2, 3]

    def test_run_to_dict_structure(self) -> None:
        from app.models.ground_truth import LabelingRun
        from app.routes.ground_truth import _run_to_dict

        run = LabelingRun()
        run.id = 42
        run.run_type = "full"
        run.status = "completed"
        run.started_at = datetime(2026, 3, 24, 2, 0, tzinfo=timezone.utc)
        run.completed_at = datetime(2026, 3, 24, 2, 5, tzinfo=timezone.utc)
        run.companies_processed = 100
        run.positive_labels_created = 50
        run.negative_labels_created = 200
        run.error_message = None
        run.created_at = datetime(2026, 3, 24, 2, 0, tzinfo=timezone.utc)

        d = _run_to_dict(run)
        assert d["id"] == 42
        assert d["run_type"] == "full"
        assert d["status"] == "completed"
        assert d["total_labels"] == 250
        assert d["duration_seconds"] == 300.0
        assert d["error_message"] is None

    def test_label_to_dict_none_evidence_returns_empty_list(self) -> None:
        from app.models.ground_truth import GroundTruthLabel
        from app.routes.ground_truth import _label_to_dict

        label = GroundTruthLabel()
        label.id = 1
        label.company_id = 1
        label.label_type = "negative"
        label.practice_area = None
        label.horizon_days = 90
        label.label_source = "retrospective"
        label.confidence_score = None
        label.is_validated = False
        label.signal_window_start = None
        label.signal_window_end = None
        label.evidence_signal_ids = None
        label.labeling_run_id = None
        label.created_at = None

        d = _label_to_dict(label)
        assert d["evidence_signal_ids"] == []
        assert d["practice_area"] is None
        assert d["signal_window_start"] is None

    def test_label_to_dict_missing_created_at(self) -> None:
        from app.models.ground_truth import GroundTruthLabel
        from app.routes.ground_truth import _label_to_dict

        label = GroundTruthLabel()
        label.id = 2
        label.company_id = 2
        label.label_type = "uncertain"
        label.practice_area = "M&A/Corporate"
        label.horizon_days = 60
        label.label_source = "manual"
        label.confidence_score = 0.5
        label.is_validated = True
        label.signal_window_start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        label.signal_window_end = datetime(2026, 2, 1, tzinfo=timezone.utc)
        label.evidence_signal_ids = []
        label.labeling_run_id = 1
        label.created_at = None

        d = _label_to_dict(label)
        assert d["created_at"] is None
        assert d["is_validated"] is True
