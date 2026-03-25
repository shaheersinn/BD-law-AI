"""
Phase 4 — LLM Training (Groq only) tests.

Tests for:
  - GroqClient: batching, rate limiting, JSON parsing
  - Prompts: structure, few-shot examples, signal_id round-trip
  - PseudoLabeler: classification → GroundTruthLabel creation
  - TrainingDataCurator: deduplication, export, confidence filtering
  - TrainingDataset ORM: fields, status enum
  - Route serializers: dataset_to_dict structure

All tests run without a live DB or real Groq API (fully mocked).
Same sys.modules stub pattern as test_phase3_ground_truth.py.
"""

from __future__ import annotations

import asyncio
import csv
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from types import ModuleType
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch


# ── Inject stubs BEFORE any app imports ───────────────────────────────────────


def _inject_module_stubs() -> None:
    """Prevent pyo3/cryptography panic by stubbing problematic modules."""
    # Stub app.config
    cfg_mod = ModuleType("app.config")
    settings_stub = MagicMock()
    settings_stub.environment = "development"
    settings_stub.groq_api_key = "test-groq-key"
    settings_stub.database_url = "postgresql+asyncpg://test:test@localhost/test"
    settings_stub.mongodb_url = "mongodb://localhost:27017"
    settings_stub.mongodb_db_name = "oracle_test"
    settings_stub.redis_url = "redis://localhost:6379/0"
    cfg_mod.get_settings = lambda: settings_stub  # type: ignore[attr-defined]
    cfg_mod.Settings = MagicMock  # type: ignore[attr-defined]
    sys.modules.setdefault("app.config", cfg_mod)

    # Stub app.database with a proper DeclarativeBase subclass
    import sqlalchemy.orm as _orm

    class _Base(_orm.DeclarativeBase):
        pass

    db_mod = ModuleType("app.database")
    db_mod.Base = _Base  # type: ignore[attr-defined]
    db_mod.AsyncSessionLocal = MagicMock()  # type: ignore[attr-defined]
    db_mod.get_db = MagicMock()  # type: ignore[attr-defined]
    db_mod.get_mongo_db = MagicMock()  # type: ignore[attr-defined]
    sys.modules.setdefault("app.database", db_mod)

    # Stub app.auth.*
    for name in ("app.auth", "app.auth.models", "app.auth.dependencies"):
        m = ModuleType(name)
        m.User = MagicMock()  # type: ignore[attr-defined]
        m.require_partner = MagicMock()  # type: ignore[attr-defined]
        m.require_admin = MagicMock()  # type: ignore[attr-defined]
        m.require_auth = MagicMock()  # type: ignore[attr-defined]
        sys.modules.setdefault(name, m)


_inject_module_stubs()


# ── Helpers ────────────────────────────────────────────────────────────────────


def _make_mock_db(rows: list[tuple[Any, ...]] | None = None) -> AsyncMock:
    result_mock = MagicMock()
    result_mock.fetchall.return_value = rows or []
    result_mock.scalar_one.return_value = 0
    result_mock.scalar_one_or_none.return_value = None
    result_mock.scalars.return_value.all.return_value = []
    db = AsyncMock()
    db.execute = AsyncMock(return_value=result_mock)
    db.add = MagicMock()
    db.get = AsyncMock(return_value=None)
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


# ── TestGroqClient ─────────────────────────────────────────────────────────────


class TestGroqClient:
    def test_classify_signals_empty_input(self) -> None:
        from app.training.groq_client import GroqClient

        client = GroqClient(api_key="test")
        results = _run(client.classify_signals([]))
        assert results == []

    def test_parse_response_valid_json(self) -> None:
        from app.training.groq_client import GroqClient, SignalInput

        client = GroqClient(api_key="test")
        batch = [SignalInput(signal_id=1, signal_type="ccaa_filing", signal_text="test", company_id=10)]
        raw = json.dumps([
            {"signal_id": 1, "label_type": "positive",
             "practice_areas": ["Insolvency/Restructuring"], "confidence": 0.95, "reasoning": "CCAA"}
        ])
        results = client._parse_response(raw, batch)
        assert len(results) == 1
        assert results[0].signal_id == 1
        assert results[0].label_type == "positive"
        assert results[0].confidence == 0.95
        assert "Insolvency/Restructuring" in results[0].practice_areas

    def test_parse_response_malformed_json_returns_uncertain(self) -> None:
        from app.training.groq_client import GroqClient, SignalInput

        client = GroqClient(api_key="test")
        batch = [SignalInput(signal_id=5, signal_type="news", signal_text="x", company_id=1)]
        results = client._parse_response("NOT JSON {{{", batch)
        assert len(results) == 1
        assert results[0].label_type == "uncertain"
        assert results[0].parse_error is True

    def test_parse_response_strips_markdown_fences(self) -> None:
        from app.training.groq_client import GroqClient, SignalInput

        client = GroqClient(api_key="test")
        batch = [SignalInput(signal_id=2, signal_type="job_posting", signal_text="dev role", company_id=1)]
        raw = "```json\n[{\"signal_id\": 2, \"label_type\": \"negative\", \"practice_areas\": [], \"confidence\": 0.9, \"reasoning\": \"tech role\"}]\n```"
        results = client._parse_response(raw, batch)
        assert len(results) == 1
        assert results[0].label_type == "negative"

    def test_parse_response_fills_missing_signals_with_uncertain(self) -> None:
        from app.training.groq_client import GroqClient, SignalInput

        client = GroqClient(api_key="test")
        batch = [
            SignalInput(signal_id=10, signal_type="a", signal_text="a", company_id=1),
            SignalInput(signal_id=11, signal_type="b", signal_text="b", company_id=1),
        ]
        # Groq only returned signal 10
        raw = json.dumps([
            {"signal_id": 10, "label_type": "negative", "practice_areas": [], "confidence": 0.8, "reasoning": ""}
        ])
        results = client._parse_response(raw, batch)
        assert len(results) == 2
        ids = {r.signal_id for r in results}
        assert 10 in ids and 11 in ids
        for r in results:
            if r.signal_id == 11:
                assert r.label_type == "uncertain"
                assert r.parse_error is True

    def test_parse_response_clamps_confidence(self) -> None:
        from app.training.groq_client import GroqClient, SignalInput

        client = GroqClient(api_key="test")
        batch = [SignalInput(signal_id=3, signal_type="x", signal_text="x", company_id=1)]
        raw = json.dumps([{"signal_id": 3, "label_type": "positive", "practice_areas": [], "confidence": 1.5, "reasoning": ""}])
        results = client._parse_response(raw, batch)
        assert results[0].confidence == 1.0

    def test_parse_response_invalid_label_type_becomes_uncertain(self) -> None:
        from app.training.groq_client import GroqClient, SignalInput

        client = GroqClient(api_key="test")
        batch = [SignalInput(signal_id=4, signal_type="x", signal_text="x", company_id=1)]
        raw = json.dumps([{"signal_id": 4, "label_type": "MAYBE", "practice_areas": [], "confidence": 0.7, "reasoning": ""}])
        results = client._parse_response(raw, batch)
        assert results[0].label_type == "uncertain"

    def test_batch_splits_correctly(self) -> None:
        from app.training.groq_client import GROQ_BATCH_SIZE, GroqClient, SignalInput

        client = GroqClient(api_key="test")
        # Create more signals than one batch
        signals = [
            SignalInput(signal_id=i, signal_type="x", signal_text="text", company_id=1)
            for i in range(GROQ_BATCH_SIZE + 3)
        ]
        call_count = 0

        async def fake_call(prompt: str) -> str:
            nonlocal call_count
            call_count += 1
            # Return uncertain for all signals in the prompt
            # We can't easily parse the prompt, so return empty array
            return "[]"

        client._call_once = fake_call  # type: ignore[method-assign]
        _run(client.classify_signals(signals))
        assert call_count == 2  # ceil((GROQ_BATCH_SIZE + 3) / GROQ_BATCH_SIZE)

    def test_batch_error_falls_back_to_uncertain(self) -> None:
        from app.training.groq_client import GroqClient, SignalInput

        client = GroqClient(api_key="test")
        signals = [SignalInput(signal_id=99, signal_type="x", signal_text="x", company_id=1)]

        async def failing_call(prompt: str) -> str:
            raise ValueError("API down")

        client._call_once = failing_call  # type: ignore[method-assign]
        results = _run(client.classify_signals(signals))
        assert len(results) == 1
        assert results[0].label_type == "uncertain"
        assert results[0].parse_error is True


# ── TestPrompts ────────────────────────────────────────────────────────────────


class TestPrompts:
    def test_build_prompt_contains_signal_ids(self) -> None:
        from app.training.groq_client import SignalInput
        from app.training.prompts import build_classification_prompt

        signals = [
            SignalInput(signal_id=42, signal_type="ccaa_filing", signal_text="CCAA protection", company_id=1),
        ]
        prompt = build_classification_prompt(signals)
        assert "42" in prompt

    def test_build_prompt_contains_json_schema_hint(self) -> None:
        from app.training.groq_client import SignalInput
        from app.training.prompts import build_classification_prompt

        signals = [SignalInput(signal_id=1, signal_type="x", signal_text="test", company_id=1)]
        prompt = build_classification_prompt(signals)
        assert "label_type" in prompt
        assert "confidence" in prompt
        assert "practice_areas" in prompt

    def test_build_prompt_contains_practice_areas(self) -> None:
        from app.training.groq_client import SignalInput
        from app.training.prompts import build_classification_prompt

        signals = [SignalInput(signal_id=1, signal_type="x", signal_text="test", company_id=1)]
        prompt = build_classification_prompt(signals)
        assert "Insolvency/Restructuring" in prompt
        assert "M&A/Corporate" in prompt

    def test_build_prompt_has_few_shot_examples(self) -> None:
        from app.training.groq_client import SignalInput
        from app.training.prompts import build_classification_prompt

        signals = [SignalInput(signal_id=1, signal_type="x", signal_text="test", company_id=1)]
        prompt = build_classification_prompt(signals)
        assert "Few-Shot Examples" in prompt
        assert "CCAA" in prompt  # from example

    def test_build_prompt_no_text_signal(self) -> None:
        from app.training.groq_client import SignalInput
        from app.training.prompts import build_classification_prompt

        signals = [SignalInput(signal_id=7, signal_type="no_text_type", signal_text=None, company_id=1)]
        prompt = build_classification_prompt(signals)
        assert "no text" in prompt.lower() or "signal_type only" in prompt.lower()

    def test_system_prompt_not_empty(self) -> None:
        from app.training.prompts import SYSTEM_PROMPT

        assert len(SYSTEM_PROMPT) > 50

    def test_few_shot_examples_valid(self) -> None:
        from app.training.prompts import FEW_SHOT_EXAMPLES

        for ex in FEW_SHOT_EXAMPLES:
            assert ex["label_type"] in ("positive", "negative", "uncertain")
            assert 0.0 <= ex["confidence"] <= 1.0
            assert isinstance(ex["practice_areas"], list)


# ── TestPseudoLabeler ──────────────────────────────────────────────────────────


class TestPseudoLabeler:
    def test_no_unlabeled_signals_returns_zero(self) -> None:
        from app.training.pseudo_labeler import PseudoLabeler

        db = _make_mock_db(rows=[])
        result = _run(PseudoLabeler().run(run_id=1, db=db))
        assert result["pseudo_labels_created"] == 0
        assert result["signals_processed"] == 0
        assert result["errors"] == 0

    def test_confident_positive_creates_label(self) -> None:
        from app.training.groq_client import ClassificationResult, GroqClient
        from app.training.pseudo_labeler import PseudoLabeler

        db = _make_mock_db(rows=[
            (101, 5, "ccaa_filing", "CCAA protection filing text", None),
        ])

        mock_groq = MagicMock(spec=GroqClient)
        mock_groq.classify_signals = AsyncMock(return_value=[
            ClassificationResult(
                signal_id=101,
                label_type="positive",
                practice_areas=["Insolvency/Restructuring"],
                confidence=0.92,
            )
        ])

        labeler = PseudoLabeler(groq_client=mock_groq)
        result = _run(labeler.run(run_id=1, db=db))

        assert result["pseudo_labels_created"] == 1
        assert result["errors"] == 0
        assert db.add.called

    def test_low_confidence_rejected(self) -> None:
        from app.training.groq_client import ClassificationResult, GroqClient
        from app.training.pseudo_labeler import PSEUDO_LABEL_CONFIDENCE_FLOOR, PseudoLabeler

        db = _make_mock_db(rows=[
            (200, 5, "news_article", "Some news", None),
        ])

        mock_groq = MagicMock(spec=GroqClient)
        mock_groq.classify_signals = AsyncMock(return_value=[
            ClassificationResult(
                signal_id=200,
                label_type="uncertain",
                practice_areas=[],
                confidence=PSEUDO_LABEL_CONFIDENCE_FLOOR - 0.01,  # just below floor
            )
        ])

        result = _run(PseudoLabeler(groq_client=mock_groq).run(run_id=1, db=db))
        assert result["pseudo_labels_created"] == 0
        assert result["rejected_low_confidence"] == 1

    def test_negative_label_created_with_no_practice_area(self) -> None:
        from app.training.groq_client import ClassificationResult, GroqClient
        from app.training.pseudo_labeler import PseudoLabeler

        db = _make_mock_db(rows=[
            (300, 5, "job_posting", "Developer job", None),
        ])

        added_labels: list[Any] = []
        db.add = lambda x: added_labels.append(x)

        mock_groq = MagicMock(spec=GroqClient)
        mock_groq.classify_signals = AsyncMock(return_value=[
            ClassificationResult(
                signal_id=300,
                label_type="negative",
                practice_areas=[],
                confidence=0.88,
            )
        ])

        _run(PseudoLabeler(groq_client=mock_groq).run(run_id=2, db=db))
        assert len(added_labels) == 1
        assert added_labels[0].label_type == "negative"
        assert added_labels[0].practice_area is None

    def test_multi_practice_area_creates_multiple_labels(self) -> None:
        from app.training.groq_client import ClassificationResult, GroqClient
        from app.training.pseudo_labeler import PseudoLabeler

        db = _make_mock_db(rows=[
            (400, 5, "enforcement_action", "SEC + Privacy violation", None),
        ])

        added_labels: list[Any] = []
        db.add = lambda x: added_labels.append(x)

        mock_groq = MagicMock(spec=GroqClient)
        mock_groq.classify_signals = AsyncMock(return_value=[
            ClassificationResult(
                signal_id=400,
                label_type="positive",
                practice_areas=["Securities/Capital Markets", "Privacy/Cybersecurity"],
                confidence=0.85,
            )
        ])

        _run(PseudoLabeler(groq_client=mock_groq).run(run_id=3, db=db))
        assert len(added_labels) == 2
        pas = {label.practice_area for label in added_labels}
        assert "Securities/Capital Markets" in pas
        assert "Privacy/Cybersecurity" in pas

    def test_resolve_practice_areas_case_insensitive(self) -> None:
        from app.training.pseudo_labeler import PseudoLabeler

        labeler = PseudoLabeler.__new__(PseudoLabeler)
        resolved = labeler._resolve_practice_areas(["insolvency/restructuring", "M&A/CORPORATE"])
        assert "Insolvency/Restructuring" in resolved
        assert "M&A/Corporate" in resolved

    def test_resolve_practice_areas_unknown_dropped(self) -> None:
        from app.training.pseudo_labeler import PseudoLabeler

        labeler = PseudoLabeler.__new__(PseudoLabeler)
        resolved = labeler._resolve_practice_areas(["Not A Real Practice Area XYZ"])
        assert resolved == []

    def test_label_source_is_pseudo_label(self) -> None:
        from app.training.groq_client import ClassificationResult, GroqClient
        from app.training.pseudo_labeler import PseudoLabeler

        db = _make_mock_db(rows=[
            (500, 5, "ccaa_filing", "CCAA", None),
        ])

        added_labels: list[Any] = []
        db.add = lambda x: added_labels.append(x)

        mock_groq = MagicMock(spec=GroqClient)
        mock_groq.classify_signals = AsyncMock(return_value=[
            ClassificationResult(
                signal_id=500, label_type="positive",
                practice_areas=["Insolvency/Restructuring"], confidence=0.9,
            )
        ])

        _run(PseudoLabeler(groq_client=mock_groq).run(run_id=4, db=db))
        assert added_labels[0].label_source == "pseudo_label"
        assert added_labels[0].is_validated is False

    def test_groq_failure_returns_error_count(self) -> None:
        from app.training.groq_client import GroqClient
        from app.training.pseudo_labeler import PseudoLabeler

        db = _make_mock_db(rows=[
            (600, 5, "ccaa_filing", "CCAA", None),
        ])

        mock_groq = MagicMock(spec=GroqClient)
        mock_groq.classify_signals = AsyncMock(side_effect=RuntimeError("Groq down"))

        result = _run(PseudoLabeler(groq_client=mock_groq).run(run_id=5, db=db))
        assert result["errors"] == 1
        assert result["pseudo_labels_created"] == 0


# ── TestTrainingDataCurator ────────────────────────────────────────────────────


class TestTrainingDataCurator:
    def test_empty_db_produces_zero_label_dataset(self) -> None:
        from app.training.curator import TrainingDataCurator

        db = _make_mock_db(rows=[])
        dataset_obj: list[Any] = []
        db.add = lambda x: dataset_obj.append(x)

        with tempfile.TemporaryDirectory() as tmpdir:
            curator = TrainingDataCurator(export_dir=tmpdir)
            result = _run(curator.curate(db=db, export_format="csv"))

        assert result["label_count"] == 0
        assert result["positive_count"] == 0
        assert result["export_path"].endswith(".csv")

    def test_deduplicate_keeps_highest_confidence(self) -> None:
        from app.training.curator import TrainingDataCurator

        curator = TrainingDataCurator.__new__(TrainingDataCurator)
        rows = [
            {"company_id": 1, "practice_area": "M&A/Corporate", "horizon_days": 30,
             "label_type": "positive", "confidence_score": 0.75, "label_source": "retrospective"},
            {"company_id": 1, "practice_area": "M&A/Corporate", "horizon_days": 30,
             "label_type": "positive", "confidence_score": 0.90, "label_source": "pseudo_label"},
        ]
        result = curator._deduplicate(rows)
        assert len(result) == 1
        assert result[0]["confidence_score"] == 0.90

    def test_deduplicate_different_keys_kept_separately(self) -> None:
        from app.training.curator import TrainingDataCurator

        curator = TrainingDataCurator.__new__(TrainingDataCurator)
        rows = [
            {"company_id": 1, "practice_area": "Tax", "horizon_days": 30,
             "label_type": "positive", "confidence_score": 0.8, "label_source": "retrospective"},
            {"company_id": 1, "practice_area": "Tax", "horizon_days": 60,  # different horizon
             "label_type": "positive", "confidence_score": 0.7, "label_source": "retrospective"},
        ]
        result = curator._deduplicate(rows)
        assert len(result) == 2

    def test_deduplicate_adds_label_int(self) -> None:
        from app.training.curator import TrainingDataCurator

        curator = TrainingDataCurator.__new__(TrainingDataCurator)
        rows = [
            {"company_id": 1, "practice_area": "Tax", "horizon_days": 30,
             "label_type": "positive", "confidence_score": 0.8, "label_source": "retrospective"},
            {"company_id": 2, "practice_area": "Tax", "horizon_days": 30,
             "label_type": "negative", "confidence_score": 0.8, "label_source": "retrospective"},
            {"company_id": 3, "practice_area": "Tax", "horizon_days": 30,
             "label_type": "uncertain", "confidence_score": 0.8, "label_source": "pseudo_label"},
        ]
        result = curator._deduplicate(rows)
        by_company = {r["company_id"]: r for r in result}
        assert by_company[1]["label_int"] == 1
        assert by_company[2]["label_int"] == 0
        assert by_company[3]["label_int"] == -1

    def test_csv_export_creates_file(self) -> None:
        from app.training.curator import TrainingDataCurator

        with tempfile.TemporaryDirectory() as tmpdir:
            curator = TrainingDataCurator(export_dir=tmpdir)
            rows = [
                {"company_id": 1, "practice_area": "Tax", "horizon_days": 30,
                 "label_type": "positive", "label_int": 1, "confidence_score": 0.8, "label_source": "retrospective"},
            ]
            path = curator._export(rows, fmt="csv")
            assert os.path.exists(path)
            assert path.endswith(".csv")
            with open(path) as f:
                reader = csv.DictReader(f)
                data = list(reader)
            assert len(data) == 1
            assert data[0]["company_id"] == "1"

    def test_csv_export_empty_rows(self) -> None:
        from app.training.curator import TrainingDataCurator

        with tempfile.TemporaryDirectory() as tmpdir:
            curator = TrainingDataCurator(export_dir=tmpdir)
            path = curator._export([], fmt="csv")
            assert os.path.exists(path)

    def test_confidence_filter_applied(self) -> None:
        from app.training.curator import TrainingDataCurator

        db = _make_mock_db(rows=[])
        db.add = MagicMock()
        execute_calls: list[Any] = []
        original_execute = db.execute

        async def capture_execute(stmt: Any, params: Any = None) -> Any:
            execute_calls.append((stmt, params))
            result_mock = MagicMock()
            result_mock.fetchall.return_value = []
            return result_mock

        db.execute = capture_execute

        with tempfile.TemporaryDirectory() as tmpdir:
            curator = TrainingDataCurator(export_dir=tmpdir)
            _run(curator.curate(db=db, min_confidence=0.85, export_format="csv"))

        # Verify confidence was passed to SQL
        assert len(execute_calls) >= 1
        _, params = execute_calls[0]
        if params:
            assert params.get("min_confidence") == 0.85

    def test_curate_creates_training_dataset_record(self) -> None:
        from app.training.curator import TrainingDataCurator

        db = _make_mock_db(rows=[])
        added: list[Any] = []
        db.add = lambda x: added.append(x)

        with tempfile.TemporaryDirectory() as tmpdir:
            curator = TrainingDataCurator(export_dir=tmpdir)
            _run(curator.curate(db=db, export_format="csv"))

        from app.models.training import TrainingDataset

        dataset_records = [x for x in added if isinstance(x, TrainingDataset)]
        assert len(dataset_records) == 1


# ── TestTrainingDatasetModel ───────────────────────────────────────────────────


class TestTrainingDatasetModel:
    def test_dataset_status_values(self) -> None:
        from app.models.training import DatasetStatus

        assert DatasetStatus.pending == "pending"
        assert DatasetStatus.running == "running"
        assert DatasetStatus.complete == "complete"
        assert DatasetStatus.failed == "failed"

    def test_duration_seconds_none_when_incomplete(self) -> None:
        from app.models.training import TrainingDataset

        ds = TrainingDataset()
        ds.created_at = None
        ds.completed_at = None
        assert ds.duration_seconds is None

    def test_duration_seconds_calculated(self) -> None:
        from datetime import timedelta

        from app.models.training import TrainingDataset

        ds = TrainingDataset()
        ds.created_at = datetime(2026, 3, 24, 5, 0, 0, tzinfo=timezone.utc)
        ds.completed_at = ds.created_at + timedelta(seconds=120)
        assert ds.duration_seconds == 120.0

    def test_dataset_has_tablename(self) -> None:
        from app.models.training import TrainingDataset

        assert TrainingDataset.__tablename__ == "training_datasets"


# ── TestGroundTruthEnumExtensions ─────────────────────────────────────────────


class TestGroundTruthEnumExtensions:
    def test_label_source_pseudo_label_exists(self) -> None:
        from app.models.ground_truth import LabelSource

        assert LabelSource.pseudo_label == "pseudo_label"

    def test_run_type_pseudo_label_exists(self) -> None:
        from app.models.ground_truth import RunType

        assert RunType.pseudo_label == "pseudo_label"

    def test_label_source_all_values(self) -> None:
        from app.models.ground_truth import LabelSource

        values = {ls.value for ls in LabelSource}
        assert "retrospective" in values
        assert "manual" in values
        assert "active_learning" in values
        assert "pseudo_label" in values

    def test_run_type_all_values(self) -> None:
        from app.models.ground_truth import RunType

        values = {rt.value for rt in RunType}
        assert "retrospective" in values
        assert "negative_sampling" in values
        assert "full" in values
        assert "pseudo_label" in values


# ── TestRouteSerializers ───────────────────────────────────────────────────────


class TestRouteSerializers:
    def test_dataset_to_dict_structure(self) -> None:
        from app.models.training import DatasetStatus, TrainingDataset
        from app.routes.training import _dataset_to_dict

        ds = TrainingDataset()
        ds.id = 1
        ds.status = DatasetStatus.complete.value
        ds.label_count = 100
        ds.positive_count = 60
        ds.negative_count = 30
        ds.uncertain_count = 10
        ds.practice_areas = ["M&A/Corporate"]
        ds.horizons = [30, 60, 90]
        ds.min_confidence = 0.70
        ds.export_path = "/data/training/training_20260324_050000.csv"
        ds.export_format = "csv"
        ds.error_message = None
        ds.created_at = datetime(2026, 3, 24, 5, 0, 0, tzinfo=timezone.utc)
        ds.completed_at = datetime(2026, 3, 24, 5, 2, 0, tzinfo=timezone.utc)

        d = _dataset_to_dict(ds)
        assert d["id"] == 1
        assert d["status"] == "complete"
        assert d["label_count"] == 100
        assert d["positive_count"] == 60
        assert d["negative_count"] == 30
        assert d["uncertain_count"] == 10
        assert d["practice_areas"] == ["M&A/Corporate"]
        assert d["horizons"] == [30, 60, 90]
        assert d["min_confidence"] == 0.70
        assert d["export_format"] == "csv"
        assert d["duration_seconds"] == 120.0
        assert "created_at" in d
        assert "completed_at" in d

    def test_dataset_to_dict_none_timestamps(self) -> None:
        from app.models.training import TrainingDataset
        from app.routes.training import _dataset_to_dict

        ds = TrainingDataset()
        ds.id = 2
        ds.status = "pending"
        ds.label_count = 0
        ds.positive_count = 0
        ds.negative_count = 0
        ds.uncertain_count = 0
        ds.practice_areas = None
        ds.horizons = None
        ds.min_confidence = 0.70
        ds.export_path = None
        ds.export_format = "parquet"
        ds.error_message = None
        ds.created_at = None
        ds.completed_at = None

        d = _dataset_to_dict(ds)
        assert d["created_at"] is None
        assert d["completed_at"] is None
        assert d["duration_seconds"] is None
