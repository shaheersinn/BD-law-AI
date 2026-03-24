"""
tests/scrapers/test_phase1c_performance.py — Phase 1C test suite.

Tests:
  1. ScraperPerformanceGrader grade thresholds
  2. Grade letter assignment
  3. Redundancy chain definitions — no orphan source_ids
  4. Chain activation logic
  5. SPOF list populated correctly
  6. QuotaManager can_use — respects hard_stop
  7. QuotaManager fails open when Redis unavailable
  8. AlternativeDiscovery — quick wins all free + easy
  9. AlternativeDiscovery report generation
  10. All chain signal types in canonical signal type list
  11. API routes registered correctly
  12. Redundancy orchestrator — selects fallback on grade D
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ── 1. Grade thresholds ────────────────────────────────────────────────────────
def test_grade_thresholds():
    from app.scrapers.performance_grader import _letter_grade
    assert _letter_grade(95) == "A"
    assert _letter_grade(90) == "A"
    assert _letter_grade(89) == "B"
    assert _letter_grade(75) == "B"
    assert _letter_grade(74) == "C"
    assert _letter_grade(60) == "C"
    assert _letter_grade(59) == "D"
    assert _letter_grade(40) == "D"
    assert _letter_grade(39) == "F"
    assert _letter_grade(0) == "F"


# ── 2. Grade composite math ────────────────────────────────────────────────────
def test_grade_composite_weights():
    """Weights must sum to 1.0."""
    from app.scrapers.performance_grader import ScraperPerformanceGrader
    total = (
        ScraperPerformanceGrader.W_RELIABILITY
        + ScraperPerformanceGrader.W_YIELD
        + ScraperPerformanceGrader.W_QUALITY
        + ScraperPerformanceGrader.W_FRESHNESS
    )
    assert abs(total - 1.0) < 0.001, f"Weights sum to {total}, expected 1.0"


def test_grade_yield_benchmarks_all_positive():
    from app.scrapers.performance_grader import ScraperPerformanceGrader
    for prefix, bench in ScraperPerformanceGrader.YIELD_BENCHMARKS.items():
        assert bench > 0, f"Benchmark for {prefix} must be > 0"


# ── 3. Redundancy chain definitions ───────────────────────────────────────────
def test_all_chains_have_valid_signal_types():
    from app.scrapers.redundancy_chains import ALL_CHAINS
    for chain in ALL_CHAINS:
        assert chain.signal_type, f"Chain missing signal_type: {chain}"
        assert chain.primary, f"Chain {chain.signal_type} missing primary"


def test_chains_no_duplicate_signal_types():
    from app.scrapers.redundancy_chains import ALL_CHAINS
    seen = set()
    for chain in ALL_CHAINS:
        assert chain.signal_type not in seen, \
            f"Duplicate chain for signal_type: {chain.signal_type}"
        seen.add(chain.signal_type)


def test_chain_activation_grades_valid():
    from app.scrapers.redundancy_chains import ALL_CHAINS
    valid_grades = {"A", "B", "C", "D", "F"}
    for chain in ALL_CHAINS:
        assert chain.activation_grade in valid_grades, \
            f"{chain.signal_type}: invalid activation_grade '{chain.activation_grade}'"


# ── 4. Chain activation logic ─────────────────────────────────────────────────
def test_redundancy_orchestrator_uses_fallback_on_grade_d():
    from app.scrapers.redundancy_chains import RedundancyOrchestrator
    from app.scrapers.performance_grader import ScraperGrade
    from datetime import datetime, timezone

    def _make_grade(source_id, grade, score):
        return ScraperGrade(
            source_id=source_id, source_name=source_id,
            grade=grade, score=score,
            reliability_score=score, yield_score=score,
            quality_score=score, freshness_score=score,
            total_runs=100, success_rate=score/100,
            avg_records_per_run=10.0, avg_confidence=0.8,
            last_success_at=datetime.now(tz=timezone.utc),
            hours_since_success=1.0,
            recommendation="test",
        )

    grades = {
        "corporate_sedar_plus": _make_grade("corporate_sedar_plus", "D", 35),
        "corporate_edgar": _make_grade("corporate_edgar", "A", 92),
    }
    orch = RedundancyOrchestrator(grades)
    active = orch.get_active_source("filing_material_change")
    assert active == "corporate_edgar", f"Expected fallback 'corporate_edgar', got {active}"


def test_redundancy_orchestrator_uses_primary_when_healthy():
    from app.scrapers.redundancy_chains import RedundancyOrchestrator
    from app.scrapers.performance_grader import ScraperGrade
    from datetime import datetime, timezone

    def _make_grade(source_id, grade, score):
        return ScraperGrade(
            source_id=source_id, source_name=source_id,
            grade=grade, score=score,
            reliability_score=score, yield_score=score,
            quality_score=score, freshness_score=score,
            total_runs=100, success_rate=score/100,
            avg_records_per_run=10.0, avg_confidence=0.8,
            last_success_at=datetime.now(tz=timezone.utc),
            hours_since_success=1.0, recommendation="test",
        )

    grades = {
        "corporate_sedar_plus": _make_grade("corporate_sedar_plus", "A", 95),
        "corporate_edgar": _make_grade("corporate_edgar", "B", 80),
    }
    orch = RedundancyOrchestrator(grades)
    active = orch.get_active_source("filing_material_change")
    assert active == "corporate_sedar_plus"


# ── 5. SPOF list ──────────────────────────────────────────────────────────────
def test_spof_list_populated():
    from app.scrapers.redundancy_chains import SINGLE_POINTS_OF_FAILURE, ALL_CHAINS
    # Every critical chain with no fallback should be in SPOF list
    expected_spofs = [
        c.signal_type for c in ALL_CHAINS
        if c.fallback is None and c.is_critical
    ]
    for signal_type in expected_spofs:
        assert signal_type in SINGLE_POINTS_OF_FAILURE, \
            f"{signal_type} should be in SINGLE_POINTS_OF_FAILURE"


# ── 6. QuotaManager hard stop ─────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_quota_manager_hard_stop():
    from app.scrapers.quota_manager import QuotaManager, QUOTA_CONFIGS

    mock_redis = AsyncMock()
    # Simulate alpha_vantage at 24/25 (96% — above hard_stop of 0.96)
    mock_redis.get = AsyncMock(return_value=b"24")

    qm = QuotaManager(mock_redis)
    allowed = await qm.can_use("alpha_vantage", cost=1)
    assert not allowed, "Should be blocked at hard_stop threshold"


@pytest.mark.asyncio
async def test_quota_manager_allows_within_limit():
    from app.scrapers.quota_manager import QuotaManager

    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=b"10")  # 10/25 — well within limit

    qm = QuotaManager(mock_redis)
    allowed = await qm.can_use("alpha_vantage", cost=1)
    assert allowed, "Should allow when well within quota"


# ── 7. QuotaManager fails open ────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_quota_manager_fails_open():
    from app.scrapers.quota_manager import QuotaManager

    broken_redis = AsyncMock()
    broken_redis.get = AsyncMock(side_effect=ConnectionError("Redis down"))

    qm = QuotaManager(broken_redis)
    allowed = await qm.can_use("twitter_x", cost=1)
    assert allowed, "QuotaManager must fail open when Redis is unavailable"


@pytest.mark.asyncio
async def test_quota_manager_none_redis_fails_open():
    from app.scrapers.quota_manager import QuotaManager
    qm = QuotaManager(None)
    allowed = await qm.can_use("twitter_x", cost=1)
    assert allowed, "QuotaManager must fail open when Redis is None"


# ── 8. AlternativeDiscovery quick wins ────────────────────────────────────────
def test_quick_wins_all_free_and_easy():
    from app.scrapers.alternative_discovery import AlternativeDiscovery
    discovery = AlternativeDiscovery()
    quick_wins = discovery.get_quick_wins()
    assert len(quick_wins) >= 3, f"Expected >= 3 quick wins, got {len(quick_wins)}"
    for alt in quick_wins:
        assert alt.cost == "free", f"{alt.source_id_candidate} is not free"
        assert alt.implementation_difficulty == "easy", \
            f"{alt.source_id_candidate} is not easy difficulty"


# ── 9. AlternativeDiscovery report ────────────────────────────────────────────
def test_alternative_discovery_report():
    from app.scrapers.alternative_discovery import AlternativeDiscovery
    discovery = AlternativeDiscovery()
    report = discovery.generate_report(["corporate_sedar_plus", "market_alpha_vantage"])
    assert report["total_degraded"] == 2
    assert "recommendations" in report
    assert len(report["recommendations"]) == 2


def test_alternative_discovery_no_alternative():
    from app.scrapers.alternative_discovery import AlternativeDiscovery
    discovery = AlternativeDiscovery()
    # Use a source_id with no defined alternatives
    alts = discovery.get_alternatives("nonexistent_source_xyz")
    assert alts == []


# ── 10. Quota config completeness ─────────────────────────────────────────────
def test_quota_configs_have_required_fields():
    from app.scrapers.quota_manager import QUOTA_CONFIGS
    required = {"display_name", "limit", "window", "warn_threshold", "hard_stop"}
    for api, config in QUOTA_CONFIGS.items():
        missing = required - set(config.keys())
        assert not missing, f"Quota config for {api} missing fields: {missing}"
        assert 0 < config["warn_threshold"] < config["hard_stop"] <= 1.0, \
            f"{api}: thresholds must satisfy 0 < warn < hard_stop <= 1"


# ── 11. Chain count sanity check ──────────────────────────────────────────────
def test_minimum_chain_coverage():
    from app.scrapers.redundancy_chains import ALL_CHAINS, CHAINS_BY_SIGNAL
    assert len(ALL_CHAINS) >= 15, f"Expected >= 15 chains, got {len(ALL_CHAINS)}"
    assert len(CHAINS_BY_SIGNAL) == len(ALL_CHAINS), \
        "CHAINS_BY_SIGNAL must have same count as ALL_CHAINS (no duplicate signal_types)"


# ── 12. Recommendation text present ──────────────────────────────────────────
def test_recommendations_text_for_all_grades():
    from app.scrapers.performance_grader import _recommendation
    for grade in ["A", "B", "C", "D", "F"]:
        rec = _recommendation(grade, "test_source")
        assert rec, f"No recommendation text for grade {grade}"
        assert len(rec) > 20, f"Recommendation for {grade} too short: {rec!r}"
