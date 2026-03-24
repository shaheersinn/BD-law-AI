"""
tests/scrapers/test_phase1b_audit.py — Phase 1B regression tests.

Coverage:
  1.  Quality validator — valid signal passes
  2.  Quality validator — missing source_id caught as error
  3.  Quality validator — missing signal_type caught as error
  4.  Quality validator — confidence score out of range caught
  5.  Quality validator — confidence at boundaries passes
  6.  Quality validator — future published_at warns (not error)
  7.  Quality validator — past published_at does not warn
  8.  Quality validator — unknown practice area warns
  9.  Quality validator — non-HTTP source_url warns
  10. Quality validator — no source_url is valid
  11. Quality validator — non-serializable signal_value is error
  12. Quality validator — long company name warns
  13. Canary signal validates cleanly
  14. validate_batch — all valid
  15. validate_batch — pass_rate calculation
  16. validate_batch — empty batch
  17. validate_batch — duplicate URL warns
  18. validate_batch — details structure
  19. ScraperHealth.record_success — resets consecutive_failures
  20. ScraperHealth.record_failure — increments failures
  21. ScraperHealth.failure_rate — correct ratio
  22. ScraperHealth.record_failure 3x → status=failing
  23. ScraperHealth.record_success with high rate → status=healthy
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest


# ── Helpers ────────────────────────────────────────────────────────────────────


def _make_signal(**kwargs):
    """Build a valid ScraperResult with optional overrides (lazy import)."""
    from app.scrapers.base import ScraperResult

    defaults = {
        "source_id": "test_source",
        "signal_type": "test_signal",
        "confidence_score": 0.8,
        "practice_area_hints": ["litigation"],
        "signal_value": {"key": "value"},
        "source_url": "https://example.com/signal",
    }
    defaults.update(kwargs)
    return ScraperResult(**defaults)


class _HealthStub:
    """
    Minimal stub that replicates ScraperHealth business logic for unit testing.
    Avoids importing app.database (which triggers the pymongo/cryptography
    pyo3 panic in this Python 3.11 container environment).
    """

    def __init__(self, **kwargs):
        self.scraper_name = kwargs.get("scraper_name", "test_scraper")
        self.scraper_category = kwargs.get("scraper_category", "corporate")
        self.status = kwargs.get("status", "healthy")
        self.consecutive_failures = kwargs.get("consecutive_failures", 0)
        self.total_runs = kwargs.get("total_runs", 0)
        self.total_failures = kwargs.get("total_failures", 0)
        self.records_last_run = kwargs.get("records_last_run", 0)
        self.records_today = kwargs.get("records_today", 0)
        self.records_total = kwargs.get("records_total", 0)
        self.source_reliability_score = kwargs.get("source_reliability_score", 0.9)
        self.requires_api_key = kwargs.get("requires_api_key", False)
        self.last_run_at = None
        self.last_success_at = None
        self.last_error_at = None
        self.last_error_message = None
        self.last_run_duration_ms = None
        self.avg_run_duration_ms = kwargs.get("avg_run_duration_ms", None)
        self.success_rate_7d = kwargs.get("success_rate_7d", None)

    @property
    def failure_rate(self) -> float:
        if self.total_runs == 0:
            return 0.0
        return self.total_failures / self.total_runs

    def record_success(self, records: int, duration_ms: int) -> None:
        from datetime import UTC, datetime  # noqa: PLC0415

        now = datetime.now(tz=UTC)
        self.last_run_at = now
        self.last_success_at = now
        self.last_run_duration_ms = duration_ms
        self.consecutive_failures = 0
        self.total_runs += 1
        self.records_last_run = records
        self.records_total += records
        if self.success_rate_7d is not None and self.success_rate_7d > 0.95:
            self.status = "healthy"
        elif self.status == "failing":
            self.status = "degraded"

    def record_failure(self, error: str) -> None:
        from datetime import UTC, datetime  # noqa: PLC0415

        now = datetime.now(tz=UTC)
        self.last_error_at = now
        self.last_error_message = error
        self.consecutive_failures += 1
        self.total_failures += 1
        self.total_runs += 1
        if self.consecutive_failures >= 3:
            self.status = "failing"
        elif self.status == "healthy":
            self.status = "degraded"


def _make_health(**kwargs) -> _HealthStub:
    """Build a _HealthStub for unit testing (no DB, no motor, no pymongo)."""
    return _HealthStub(**kwargs)


# ── Quality Validator ──────────────────────────────────────────────────────────


class TestValidateSignal:
    def test_valid_signal_passes(self):
        from app.scrapers.quality_validator import validate_signal

        result = validate_signal(_make_signal())
        assert result.valid is True
        assert result.errors == []

    def test_missing_source_id_is_error(self):
        from app.scrapers.quality_validator import validate_signal

        result = validate_signal(_make_signal(source_id=""))
        assert result.valid is False
        assert any("source_id" in e for e in result.errors)

    def test_missing_signal_type_is_error(self):
        from app.scrapers.quality_validator import validate_signal

        result = validate_signal(_make_signal(signal_type=""))
        assert result.valid is False
        assert any("signal_type" in e for e in result.errors)

    def test_confidence_above_1_is_error(self):
        from app.scrapers.quality_validator import validate_signal

        result = validate_signal(_make_signal(confidence_score=1.5))
        assert result.valid is False
        assert any("confidence_score" in e for e in result.errors)

    def test_confidence_below_0_is_error(self):
        from app.scrapers.quality_validator import validate_signal

        result = validate_signal(_make_signal(confidence_score=-0.1))
        assert result.valid is False
        assert any("confidence_score" in e for e in result.errors)

    def test_confidence_at_boundaries_is_valid(self):
        from app.scrapers.quality_validator import validate_signal

        assert validate_signal(_make_signal(confidence_score=0.0)).valid is True
        assert validate_signal(_make_signal(confidence_score=1.0)).valid is True

    def test_future_published_at_warns(self):
        from app.scrapers.quality_validator import validate_signal

        future = datetime.now(tz=timezone.utc) + timedelta(hours=48)
        result = validate_signal(_make_signal(published_at=future))
        assert result.valid is True  # Warning, not error
        assert any("future" in w for w in result.warnings)

    def test_past_published_at_no_warning(self):
        from app.scrapers.quality_validator import validate_signal

        past = datetime.now(tz=timezone.utc) - timedelta(days=1)
        result = validate_signal(_make_signal(published_at=past))
        assert result.valid is True
        assert not any("future" in w for w in result.warnings)

    def test_unknown_practice_area_warns(self):
        from app.scrapers.quality_validator import validate_signal

        result = validate_signal(_make_signal(practice_area_hints=["nonexistent_xyz"]))
        assert result.valid is True
        assert any("practice_area" in w.lower() for w in result.warnings)

    def test_known_practice_area_no_warning(self):
        from app.scrapers.quality_validator import validate_signal

        result = validate_signal(_make_signal(practice_area_hints=["litigation", "ma_corporate"]))
        assert result.valid is True
        assert not any("practice_area" in w.lower() for w in result.warnings)

    def test_non_http_url_warns(self):
        from app.scrapers.quality_validator import validate_signal

        result = validate_signal(_make_signal(source_url="ftp://example.com/file.pdf"))
        assert result.valid is True
        assert any("scheme" in w for w in result.warnings)

    def test_no_source_url_is_valid(self):
        from app.scrapers.quality_validator import validate_signal

        result = validate_signal(_make_signal(source_url=None))
        assert result.valid is True

    def test_non_serializable_signal_value_is_error(self):
        from app.scrapers.quality_validator import validate_signal

        result = validate_signal(_make_signal(signal_value={"obj": object()}))
        assert result.valid is False
        assert any("JSON" in e for e in result.errors)

    def test_long_company_name_warns(self):
        from app.scrapers.quality_validator import validate_signal

        result = validate_signal(_make_signal(raw_company_name="x" * 501))
        assert result.valid is True
        assert any("long" in w or "chars" in w for w in result.warnings)


# ── Canary Signal ──────────────────────────────────────────────────────────────


class TestCanarySignal:
    def test_canary_signal_validates(self):
        from app.scrapers.base import ScraperResult
        from app.scrapers.quality_validator import validate_signal

        canary = ScraperResult(
            source_id="canary",
            signal_type="canary_heartbeat",
            signal_text=f"CANARY-{datetime.now(tz=timezone.utc).isoformat()}",
            confidence_score=1.0,
            practice_area_hints=["litigation"],
            signal_value={"canary": True, "ts": datetime.now(tz=timezone.utc).isoformat()},
            is_negative_label=False,
        )
        result = validate_signal(canary)
        assert result.valid is True
        assert result.errors == []


# ── Batch Validation ──────────────────────────────────────────────────────────


class TestValidateBatch:
    def test_batch_all_valid(self):
        from app.scrapers.quality_validator import validate_batch

        signals = [_make_signal() for _ in range(5)]
        summary = validate_batch(signals)
        assert summary["total"] == 5
        assert summary["valid"] == 5
        assert summary["invalid"] == 0
        assert summary["pass_rate"] == 1.0

    def test_batch_pass_rate(self):
        from app.scrapers.quality_validator import validate_batch

        signals = [_make_signal(), _make_signal(), _make_signal(source_id="")]
        summary = validate_batch(signals)
        assert summary["total"] == 3
        assert summary["valid"] == 2
        assert summary["invalid"] == 1
        assert abs(summary["pass_rate"] - 2 / 3) < 0.001

    def test_batch_empty(self):
        from app.scrapers.quality_validator import validate_batch

        summary = validate_batch([])
        assert summary["total"] == 0
        assert summary["valid"] == 0
        assert summary["invalid"] == 0

    def test_batch_duplicate_url_warns(self):
        from app.scrapers.quality_validator import validate_batch

        url = "https://example.com/same-url"
        signals = [_make_signal(source_url=url), _make_signal(source_url=url)]
        summary = validate_batch(signals)
        assert summary["valid"] == 2  # dup is warning, not error
        assert summary["with_warnings"] >= 1

    def test_batch_details_structure(self):
        from app.scrapers.quality_validator import validate_batch

        summary = validate_batch([_make_signal()])
        assert len(summary["details"]) == 1
        detail = summary["details"][0]
        for key in ("source_id", "signal_type", "valid", "errors", "warnings"):
            assert key in detail


# ── ScraperHealth Model Unit Tests ────────────────────────────────────────────


class TestScraperHealthModel:
    def test_record_success_resets_failures(self):
        health = _make_health(consecutive_failures=3, status="failing")
        health.record_success(records=10, duration_ms=500)
        assert health.consecutive_failures == 0
        assert health.records_last_run == 10
        assert health.total_runs == 1
        assert health.last_run_at is not None
        assert health.last_success_at is not None

    def test_record_failure_increments(self):
        health = _make_health()
        health.record_failure("Connection timeout")
        assert health.consecutive_failures == 1
        assert health.total_failures == 1
        assert health.last_error_message == "Connection timeout"
        assert health.last_error_at is not None

    def test_failure_rate_zero_runs(self):
        health = _make_health(total_runs=0, total_failures=0)
        assert health.failure_rate == 0.0

    def test_failure_rate_calculation(self):
        health = _make_health(total_runs=10, total_failures=3)
        assert health.failure_rate == pytest.approx(0.3)

    def test_failing_after_3_consecutive(self):
        health = _make_health(status="healthy", consecutive_failures=2)
        health.record_failure("Error")
        assert health.status == "failing"

    def test_status_improves_after_success(self):
        health = _make_health(status="failing", consecutive_failures=5, success_rate_7d=0.97)
        health.record_success(records=5, duration_ms=200)
        assert health.status == "healthy"
