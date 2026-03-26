"""
tests/test_phase12_optimization.py — Phase 12: Post-Launch Optimization test suite.

Coverage targets:
  - DB migration: 4 new tables exist as valid Python
  - analytics_service: weekly report computation + Slack delivery path
  - score_quality: report generation + markdown writer + identify_worst_five
  - sector_weights: recalibrate stub + human override integration
  - cooccurrence: refresh_rules stub
  - azure_job: --practice-areas flag
  - routes/optimization: all 5 endpoints (usage, quality, perf, override CRUD)
  - celery tasks: 3 new tasks registered
  - config: 2 new settings present
"""

from __future__ import annotations

import importlib
import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── Migration file sanity check ────────────────────────────────────────────────


def test_phase12_migration_file_exists_and_is_valid_python() -> None:
    migration_path = (
        Path(__file__).parent.parent / "alembic" / "versions" / "0009_phase12_optimization.py"
    )
    assert migration_path.exists(), "Migration 0009_phase12_optimization.py must exist"
    # Verify it parses as valid Python
    source = migration_path.read_text()
    compile(source, str(migration_path), "exec")


def test_phase12_migration_has_correct_revision() -> None:
    migration_path = (
        Path(__file__).parent.parent / "alembic" / "versions" / "0009_phase12_optimization.py"
    )
    source = migration_path.read_text()
    assert 'revision = "0009_phase12_optimization"' in source
    assert 'down_revision = "0007_phase7_api"' in source


def test_phase12_migration_creates_four_tables() -> None:
    migration_path = (
        Path(__file__).parent.parent / "alembic" / "versions" / "0009_phase12_optimization.py"
    )
    source = migration_path.read_text()
    for table in ["usage_reports", "score_quality_reports", "signal_weight_overrides", "retrain_submissions"]:
        assert table in source, f"Migration must create table: {table}"


# ── Config: new Phase 12 settings ─────────────────────────────────────────────


def test_config_has_optimization_settings() -> None:
    from app.config import Settings

    s = Settings()
    assert hasattr(s, "optimization_report_retention_weeks")
    assert hasattr(s, "retrain_drift_threshold")
    assert s.optimization_report_retention_weeks == 52
    assert s.retrain_drift_threshold == pytest.approx(0.10)


# ── Analytics service ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_latest_usage_report_returns_none_when_empty() -> None:
    from app.services.analytics_service import get_latest_usage_report

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.first.return_value = None
    mock_db.execute.return_value = mock_result

    result = await get_latest_usage_report(mock_db)
    assert result is None


@pytest.mark.asyncio
async def test_get_latest_usage_report_returns_dict_when_present() -> None:
    from app.services.analytics_service import get_latest_usage_report

    mock_db = AsyncMock()
    mock_row = MagicMock()
    mock_row.week_start = date(2026, 3, 24)
    mock_row.top_companies = [{"company_id": 1, "name": "Acme Corp", "request_count": 42}]
    mock_row.top_practice_areas = []
    mock_row.p50_ms = 45.2
    mock_row.p95_ms = 112.8
    mock_row.cache_hit_rate = 0.87
    mock_row.endpoint_breakdown = []
    mock_row.created_at = datetime(2026, 3, 24, 8, 0, tzinfo=UTC)

    mock_result = MagicMock()
    mock_result.first.return_value = mock_row
    mock_db.execute.return_value = mock_result

    result = await get_latest_usage_report(mock_db)
    assert result is not None
    assert result["week_start"] == "2026-03-24"
    assert result["p95_ms"] == pytest.approx(112.8)
    assert result["cache_hit_rate"] == pytest.approx(0.87)


@pytest.mark.asyncio
async def test_get_perf_report_returns_list() -> None:
    from app.services.analytics_service import get_perf_report

    mock_db = AsyncMock()
    mock_row = MagicMock()
    mock_row.endpoint = "/api/v1/scores/{id}"
    mock_row.request_count = 1000
    mock_row.p50_ms = 40.0
    mock_row.p95_ms = 180.0
    mock_row.p99_ms = 350.0

    mock_result = MagicMock()
    mock_result.all.return_value = [mock_row]
    mock_db.execute.return_value = mock_result

    result = await get_perf_report(mock_db, days=7)
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["p95_ms"] == pytest.approx(180.0)


@pytest.mark.asyncio
async def test_deliver_report_logs_when_no_slack_webhook() -> None:
    from app.services.analytics_service import _deliver_report

    report = {
        "week_start": date(2026, 3, 24),
        "top_companies": [{"name": "Acme"}],
        "cache_hit_rate": 0.85,
        "p95_ms": 120.0,
        "endpoint_breakdown": [],
    }

    with patch("app.services.analytics_service.settings") as mock_settings:
        mock_settings.slack_webhook_url = ""
        # Should complete without raising
        await _deliver_report(report)


# ── Score quality service ──────────────────────────────────────────────────────


def test_identify_worst_five_returns_five_lowest() -> None:
    from app.services.score_quality import _identify_worst_five

    summary = [
        {"practice_area": "Tax", "precision": 0.90, "sample_count": 100},
        {"practice_area": "MA_Corporate", "precision": 0.30, "sample_count": 50},
        {"practice_area": "Employment_Labour", "precision": 0.25, "sample_count": 60},
        {"practice_area": "Insolvency_Restructuring", "precision": 0.70, "sample_count": 80},
        {"practice_area": "Securities_Capital", "precision": 0.15, "sample_count": 55},
        {"practice_area": "Litigation_Dispute", "precision": 0.10, "sample_count": 70},
        {"practice_area": "Real_Estate_Construction", "precision": 0.50, "sample_count": 40},
    ]
    worst = _identify_worst_five(summary)
    assert len(worst) == 5
    # Lowest precision should appear first
    assert worst[0] == "Litigation_Dispute"
    assert worst[1] == "Securities_Capital"


def test_identify_worst_five_excludes_none_precision() -> None:
    from app.services.score_quality import _identify_worst_five

    summary = [
        {"practice_area": "Tax", "precision": None, "sample_count": 100},
        {"practice_area": "MA_Corporate", "precision": 0.30, "sample_count": 50},
    ]
    worst = _identify_worst_five(summary)
    assert "Tax" not in worst  # None precision excluded


def test_identify_worst_five_excludes_low_sample_count() -> None:
    from app.services.score_quality import _identify_worst_five

    summary = [
        {"practice_area": "Tax", "precision": 0.01, "sample_count": 2},  # < 5 samples
        {"practice_area": "MA_Corporate", "precision": 0.30, "sample_count": 50},
    ]
    worst = _identify_worst_five(summary)
    assert "Tax" not in worst


@pytest.mark.asyncio
async def test_get_latest_score_quality_report_returns_none_when_empty() -> None:
    from app.services.score_quality import get_latest_score_quality_report

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.first.return_value = None
    mock_db.execute.return_value = mock_result

    result = await get_latest_score_quality_report(mock_db)
    assert result is None


def test_write_markdown_report_creates_file(tmp_path: Path) -> None:
    from app.services import score_quality as sq

    with patch.object(sq, "REPORTS_DIR", tmp_path):
        report = {
            "report_date": date(2026, 3, 26),
            "worst_five": ["Tax", "MA_Corporate"],
            "summary": [
                {
                    "practice_area": "Tax",
                    "precision": 0.30,
                    "recall": None,
                    "avg_lead_days": 14.0,
                    "sample_count": 50,
                    "label_count": 40,
                    "low_data_flag": False,
                }
            ],
        }
        sq._write_markdown_report(report)
        expected_file = tmp_path / "score_quality_2026-03-26.md"
        assert expected_file.exists()
        content = expected_file.read_text()
        assert "Tax" in content
        assert "0.300" in content


# ── Sector weights: override integration ──────────────────────────────────────


def test_compute_aggregate_multiplier_uses_human_override() -> None:
    from app.ml.sector_weights import compute_aggregate_multiplier

    features = {"signal_a": 0.9, "signal_b": 0.5}
    weights = {"energy": {"signal_a": 1.5, "signal_b": 1.0}}
    human_overrides = {"signal_a": 3.0}  # human says signal_a is 3×

    result = compute_aggregate_multiplier(
        features, "energy", weights, top_features=2, human_overrides=human_overrides
    )
    # top features are signal_a (0.9) and signal_b (0.5)
    # signal_a uses human override 3.0; signal_b uses ML weight 1.0
    expected = (3.0 + 1.0) / 2
    assert result == pytest.approx(expected)


def test_compute_aggregate_multiplier_no_override_unchanged() -> None:
    from app.ml.sector_weights import compute_aggregate_multiplier

    features = {"signal_a": 0.9}
    weights = {"energy": {"signal_a": 2.0}}

    result = compute_aggregate_multiplier(features, "energy", weights, top_features=1)
    assert result == pytest.approx(2.0)


# ── Cooccurrence: refresh_rules stub ──────────────────────────────────────────


def test_mine_all_practice_areas_returns_dict() -> None:
    from app.ml.cooccurrence import mine_all_practice_areas

    # Empty input returns empty result
    result = mine_all_practice_areas({})
    assert result == {}


def test_build_transaction_matrix_empty_input() -> None:
    from app.ml.cooccurrence import build_transaction_matrix

    df = build_transaction_matrix([])
    assert df.empty


# ── Azure job: --practice-areas flag ──────────────────────────────────────────


def test_azure_job_has_practice_areas_parameter() -> None:
    import inspect
    from azure.training.azure_job import submit_training_job

    sig = inspect.signature(submit_training_job)
    assert "practice_areas" in sig.parameters


def test_azure_job_practice_areas_defaults_to_none() -> None:
    import inspect
    from azure.training.azure_job import submit_training_job

    sig = inspect.signature(submit_training_job)
    assert sig.parameters["practice_areas"].default is None


# ── Celery tasks registered ────────────────────────────────────────────────────


def test_phase12_celery_tasks_are_registered() -> None:
    # Import triggers task registration
    import app.tasks.phase12_tasks  # noqa: F401
    from app.tasks.celery_app import celery_app

    registered = list(celery_app.tasks.keys())
    assert "agents.compute_usage_report" in registered
    assert "agents.recalibrate_signal_weights" in registered
    assert "agents.check_retrain_trigger" in registered


def test_phase12_beat_entries_exist() -> None:
    from app.tasks.celery_app import celery_app

    schedule_keys = list(celery_app.conf.beat_schedule.keys())
    assert "agent-compute-usage-report" in schedule_keys
    assert "agent-recalibrate-signal-weights" in schedule_keys
    assert "agent-check-retrain-trigger" in schedule_keys


def test_agent033_beat_schedule_is_monday_0800() -> None:
    from celery.schedules import crontab

    from app.tasks.celery_app import celery_app

    entry = celery_app.conf.beat_schedule["agent-compute-usage-report"]
    sched = entry["schedule"]
    assert isinstance(sched, crontab)
    assert str(sched.hour) == "8"
    assert str(sched.day_of_week) == "1"  # Monday


def test_agent035_beat_schedule_is_sunday_0300() -> None:
    from celery.schedules import crontab

    from app.tasks.celery_app import celery_app

    entry = celery_app.conf.beat_schedule["agent-check-retrain-trigger"]
    sched = entry["schedule"]
    assert isinstance(sched, crontab)
    assert str(sched.hour) == "3"
    assert str(sched.day_of_week) == "0"  # Sunday


# ── Optimization route: schema validation ────────────────────────────────────


def test_signal_override_create_model_validates_multiplier() -> None:
    from app.routes.optimization import SignalOverrideCreate

    override = SignalOverrideCreate(
        signal_type="sedar_material_change",
        practice_area="Insolvency_Restructuring",
        multiplier=2.5,
        reason="Oil sector is highly sensitive to SEDAR filings",
    )
    assert override.multiplier == pytest.approx(2.5)
    assert override.signal_type == "sedar_material_change"


def test_signal_override_create_model_rejects_out_of_range() -> None:
    from pydantic import ValidationError

    from app.routes.optimization import SignalOverrideCreate

    with pytest.raises(ValidationError):
        SignalOverrideCreate(
            signal_type="test",
            practice_area="Tax",
            multiplier=10.0,  # > 5.0 — should fail
        )

    with pytest.raises(ValidationError):
        SignalOverrideCreate(
            signal_type="test",
            practice_area="Tax",
            multiplier=0.0,  # < 0.01 — should fail
        )


def test_signal_override_out_model_has_required_fields() -> None:
    from app.routes.optimization import SignalOverrideOut

    fields = set(SignalOverrideOut.model_fields.keys())
    required = {"id", "signal_type", "practice_area", "multiplier", "is_active", "created_at", "updated_at"}
    assert required.issubset(fields)


# ── PRACTICE_AREAS list completeness ─────────────────────────────────────────


def test_score_quality_has_34_practice_areas() -> None:
    from app.services.score_quality import PRACTICE_AREAS

    assert len(PRACTICE_AREAS) == 34, f"Expected 34 practice areas, got {len(PRACTICE_AREAS)}"


# ── Reports directory ─────────────────────────────────────────────────────────


def test_reports_gitkeep_exists() -> None:
    gitkeep = Path(__file__).parent.parent / "reports" / ".gitkeep"
    assert gitkeep.exists(), "backend/reports/.gitkeep must exist"
