"""Unit tests for the Class Action Firm Matcher.

Tests pure-function logic (jurisdiction scoring, practice area scoring,
track record scoring) without a real database connection, plus integration
tests for match_firms_to_class_action() with a mocked async session.

Covers:
  - Jurisdiction match: firm in ON > firm in BC for ON company
  - Practice area match: securities-strong firm ranks higher for securities CA
  - Plaintiff vs defence filter: side='plaintiff' excludes defence-only firms
  - Empty firms list → returns empty gracefully
  - Match score bounds: all scores ∈ [0.0, 1.0]
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://oracle:oracle@localhost:5432/oracle_test"
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("MONGODB_URL", "mongodb://localhost:27017")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production-32chars")

from app.services.firm_matcher import (  # noqa: E402
    FirmMatch,
    _jurisdiction_score,
    _practice_score,
    _side_fit,
    _track_record_score,
    match_firms_to_class_action,
)

# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_firm(
    firm_id: int = 1,
    name: str = "Test Firm LLP",
    tier: int = 2,
    hq_province: str = "ON",
    jurisdictions: list[str] | None = None,
    offices: list[dict] | None = None,
    practice_strengths: dict | None = None,
    track_record: list[dict] | None = None,
    is_plaintiff_firm: bool = False,
    is_defence_firm: bool = True,
    lawyer_count: int = 100,
    class_action_lawyers: int = 15,
) -> MagicMock:
    firm = MagicMock()
    firm.id = firm_id
    firm.name = name
    firm.name_normalized = name.lower()
    firm.tier = tier
    firm.hq_province = hq_province
    firm.jurisdictions = jurisdictions or ["ON", "QC", "BC", "AB"]
    firm.offices = offices or [{"city": "Toronto", "province": "ON"}]
    firm.practice_strengths = practice_strengths or {
        "securities": 0.80,
        "product_liability": 0.65,
        "privacy": 0.70,
        "employment": 0.60,
        "environmental": 0.55,
        "competition": 0.75,
    }
    firm.class_action_track_record = (
        track_record
        if track_record is not None
        else [
            {"case_type": "securities_capital_markets", "count": 15, "avg_settlement": 30_000_000},
            {"case_type": "privacy_cybersecurity", "count": 8, "avg_settlement": 18_000_000},
        ]
    )
    firm.is_plaintiff_firm = is_plaintiff_firm
    firm.is_defence_firm = is_defence_firm
    firm.lawyer_count = lawyer_count
    firm.class_action_lawyers = class_action_lawyers
    firm.website = "https://example.com"
    return firm


def _make_company(province: str | None = "ON", sector: str | None = "Technology") -> MagicMock:
    company = MagicMock()
    company.province = province
    company.sector = sector
    company.id = 1
    company.name = "TestCo Inc."
    return company


def _make_ca_score(
    probability: float = 0.75,
    predicted_type: str = "securities_capital_markets",
    confidence: float = 0.8,
    contributing_signals: list | None = None,
) -> MagicMock:
    score = MagicMock()
    score.probability = probability
    score.predicted_type = predicted_type
    score.confidence = confidence
    score.contributing_signals = contributing_signals or [
        {"signal_type": "securities_restatement", "weight": 0.9},
        {"signal_type": "stock_price_drop_20pct", "weight": 0.75},
    ]
    return score


# ── Jurisdiction score tests ──────────────────────────────────────────────────


def test_jurisdiction_match_licensed_province() -> None:
    """Firm licensed in ON scores 1.0 for ON company."""
    firm = _make_firm(jurisdictions=["ON", "QC"])
    company = _make_company(province="ON")
    score, reason = _jurisdiction_score(firm, company)
    assert score == 1.0
    assert "ON" in reason


def test_jurisdiction_match_office_presence() -> None:
    """Firm with office but no full licence in BC scores 0.75."""
    firm = _make_firm(
        jurisdictions=["ON", "QC"],  # not BC
        offices=[{"city": "Vancouver", "province": "BC"}],
    )
    company = _make_company(province="BC")
    score, reason = _jurisdiction_score(firm, company)
    assert score == 0.75
    assert "BC" in reason


def test_jurisdiction_match_no_presence() -> None:
    """Firm with no presence in SK scores 0.15."""
    firm = _make_firm(
        jurisdictions=["ON", "QC"],
        offices=[{"city": "Toronto", "province": "ON"}],
    )
    company = _make_company(province="SK")
    score, _ = _jurisdiction_score(firm, company)
    assert score == 0.15


def test_jurisdiction_on_ranks_higher_than_bc_for_on_company() -> None:
    """Firm in ON ranks higher than firm in BC for an ON-based company."""
    firm_on = _make_firm(firm_id=1, jurisdictions=["ON", "QC", "AB"])
    firm_bc = _make_firm(
        firm_id=2,
        jurisdictions=["BC", "AB"],
        offices=[{"city": "Vancouver", "province": "BC"}],
    )
    company = _make_company(province="ON")
    score_on, _ = _jurisdiction_score(firm_on, company)
    score_bc, _ = _jurisdiction_score(firm_bc, company)
    assert score_on > score_bc


def test_jurisdiction_unknown_province_default() -> None:
    """Company with unknown province → default 0.55 national coverage score."""
    firm = _make_firm(jurisdictions=["ON", "BC"])
    company = _make_company(province=None)
    score, reason = _jurisdiction_score(firm, company)
    assert score == pytest.approx(0.55, abs=0.01)


# ── Practice area score tests ─────────────────────────────────────────────────


def test_practice_area_match_securities_strong_firm() -> None:
    """Firm with high securities strength scores > 0.8 for securities CA."""
    firm = _make_firm(practice_strengths={"securities": 0.90, "product_liability": 0.50})
    ca_score = _make_ca_score(predicted_type="securities_capital_markets")
    score, reason = _practice_score(firm, ca_score.predicted_type)
    assert score >= 0.80
    assert "securities" in reason.lower() or "capital" in reason.lower()


def test_practice_area_match_weak_firm_lower_score() -> None:
    """Firm with low securities strength scores < 0.6 for securities CA."""
    firm = _make_firm(practice_strengths={"securities": 0.45})
    score, _ = _practice_score(firm, "securities_capital_markets")
    assert score < 0.6


def test_practice_area_match_product_liability() -> None:
    """Firm with high product_liability scores higher for product liability CA."""
    firm_strong = _make_firm(practice_strengths={"product_liability": 0.90})
    firm_weak = _make_firm(practice_strengths={"product_liability": 0.40})
    score_strong, _ = _practice_score(firm_strong, "product_liability")
    score_weak, _ = _practice_score(firm_weak, "product_liability")
    assert score_strong > score_weak


def test_practice_area_no_predicted_type_neutral() -> None:
    """No predicted type → neutral 0.5 score."""
    firm = _make_firm()
    score, _ = _practice_score(firm, None)
    assert score == pytest.approx(0.5, abs=0.01)


# ── Track record score tests ──────────────────────────────────────────────────


def test_track_record_matching_type_higher() -> None:
    """Firm with matching track record type scores higher than mismatched type."""
    track_record = [
        {"case_type": "securities_capital_markets", "count": 20, "avg_settlement": 40_000_000},
    ]
    firm = _make_firm(track_record=track_record)
    ca_score = _make_ca_score(predicted_type="securities_capital_markets")
    score, reason = _track_record_score(firm, ca_score.predicted_type)
    assert score > 0.5
    assert "20" in reason or "matched" in reason.lower() or "prior" in reason.lower()


def test_track_record_no_records() -> None:
    """No track record → low score with informative reason."""
    firm = _make_firm(track_record=[])
    score, reason = _track_record_score(firm, "securities_capital_markets")
    assert score <= 0.30
    assert len(reason) > 0


# ── Side fit filter tests ─────────────────────────────────────────────────────


def test_plaintiff_filter_excludes_defence_only_firm() -> None:
    """side='plaintiff' must exclude defence-only firms."""
    defence_firm = _make_firm(is_plaintiff_firm=False, is_defence_firm=True)
    assert not _side_fit("plaintiff", defence_firm)


def test_plaintiff_filter_includes_plaintiff_firm() -> None:
    """side='plaintiff' must include plaintiff firms."""
    plaintiff_firm = _make_firm(is_plaintiff_firm=True, is_defence_firm=False)
    assert _side_fit("plaintiff", plaintiff_firm)


def test_defence_filter_excludes_plaintiff_only_firm() -> None:
    """side='defence' must exclude plaintiff-only firms."""
    plaintiff_firm = _make_firm(is_plaintiff_firm=True, is_defence_firm=False)
    assert not _side_fit("defence", plaintiff_firm)


def test_defence_filter_includes_defence_firm() -> None:
    """side='defence' must include defence firms."""
    defence_firm = _make_firm(is_plaintiff_firm=False, is_defence_firm=True)
    assert _side_fit("defence", defence_firm)


def test_both_filter_includes_all_active_firms() -> None:
    """side='both' includes any firm that handles at least one side."""
    plaintiff_firm = _make_firm(is_plaintiff_firm=True, is_defence_firm=False)
    defence_firm = _make_firm(is_plaintiff_firm=False, is_defence_firm=True)
    dual_firm = _make_firm(is_plaintiff_firm=True, is_defence_firm=True)
    assert _side_fit("both", plaintiff_firm)
    assert _side_fit("both", defence_firm)
    assert _side_fit("both", dual_firm)


# ── match_firms_to_class_action() integration tests (mocked DB) ───────────────


@pytest.mark.asyncio
async def test_empty_firms_returns_empty() -> None:
    """No firms in DB → returns empty list gracefully."""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_result
    mock_db.scalar.return_value = 0  # seed_law_firms check: existing > 0 → skip seed

    ca_score = _make_ca_score()
    company = _make_company()

    with patch("app.services.firm_matcher.seed_law_firms", new_callable=AsyncMock):
        result = await match_firms_to_class_action(mock_db, ca_score, company, top_n=5)

    assert isinstance(result, list)
    assert len(result) == 0


@pytest.mark.asyncio
async def test_match_returns_firm_match_objects() -> None:
    """match_firms_to_class_action() returns FirmMatch instances."""
    firm = _make_firm()
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [firm]
    mock_db.execute.return_value = mock_result

    ca_score = _make_ca_score()
    company = _make_company()

    with patch("app.services.firm_matcher.seed_law_firms", new_callable=AsyncMock):
        results = await match_firms_to_class_action(mock_db, ca_score, company, top_n=5)

    assert isinstance(results, list)
    for m in results:
        assert isinstance(m, FirmMatch)
        assert isinstance(m.score, float)
        assert isinstance(m.reasons, list)
        assert isinstance(m.side_fit, str)


@pytest.mark.asyncio
async def test_match_score_bounds() -> None:
    """All match scores must be in [0.0, 1.0]."""
    firms = [
        _make_firm(firm_id=i, is_plaintiff_firm=(i % 2 == 0), is_defence_firm=(i % 2 != 0))
        for i in range(1, 6)
    ]
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = firms
    mock_db.execute.return_value = mock_result

    ca_score = _make_ca_score()
    company = _make_company()

    with patch("app.services.firm_matcher.seed_law_firms", new_callable=AsyncMock):
        results = await match_firms_to_class_action(mock_db, ca_score, company, top_n=10)

    for m in results:
        assert 0.0 <= m.score <= 1.0, f"Score out of bounds: {m.score}"


@pytest.mark.asyncio
async def test_plaintiff_vs_defence_filter() -> None:
    """side='plaintiff' excludes defence-only firms from results."""
    plaintiff_firm = _make_firm(firm_id=1, is_plaintiff_firm=True, is_defence_firm=False)
    defence_firm = _make_firm(firm_id=2, is_plaintiff_firm=False, is_defence_firm=True)

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [plaintiff_firm, defence_firm]
    mock_db.execute.return_value = mock_result

    ca_score = _make_ca_score()
    company = _make_company()

    with patch("app.services.firm_matcher.seed_law_firms", new_callable=AsyncMock):
        results = await match_firms_to_class_action(
            mock_db, ca_score, company, side="plaintiff", top_n=10
        )

    # Only plaintiff firms should be returned
    for m in results:
        assert m.firm.is_plaintiff_firm is True


@pytest.mark.asyncio
async def test_results_sorted_by_score_desc() -> None:
    """Results must be sorted by score descending."""
    firms = [
        _make_firm(
            firm_id=i,
            practice_strengths={"securities": 0.4 + i * 0.1},
            is_defence_firm=True,
        )
        for i in range(1, 4)
    ]
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = firms
    mock_db.execute.return_value = mock_result

    ca_score = _make_ca_score(predicted_type="securities_capital_markets")
    company = _make_company()

    with patch("app.services.firm_matcher.seed_law_firms", new_callable=AsyncMock):
        results = await match_firms_to_class_action(mock_db, ca_score, company, top_n=10)

    scores = [m.score for m in results]
    assert scores == sorted(scores, reverse=True), "Results must be sorted by score descending"
