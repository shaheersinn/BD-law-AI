"""
tests/test_convergence.py — Unit tests for the Bayesian convergence engine.
Run: pytest tests/ -v
"""

import pytest

from app.ml.convergence import (
    ScoredSignal,
    classify_practice_area,
    convergence_score,
    crossed_threshold,
)


def test_empty_signals_returns_zero():
    assert convergence_score([]) == 0.0


def test_single_strong_signal():
    signals = [ScoredSignal("sedar_confidentiality", days_ago=0)]
    score = convergence_score(signals)
    # Single strong signal decayed 0 days → ~91
    assert 85 <= score <= 95


def test_single_signal_decays_over_time():
    fresh  = convergence_score([ScoredSignal("sedar_material_change", days_ago=0)])
    old    = convergence_score([ScoredSignal("sedar_material_change", days_ago=42)])
    assert fresh > old


def test_convergence_multiplier_applied():
    """3+ categories → 18% boost on top of base score."""
    multi_cat = [
        ScoredSignal("sedar_confidentiality", days_ago=2),   # filings
        ScoredSignal("jet_baystreet_2x",       days_ago=3),   # geospatial
        ScoredSignal("linkedin_gc_spike",      days_ago=5),   # people
    ]
    single_cat = [
        ScoredSignal("sedar_material_change",  days_ago=2),
        ScoredSignal("sedar_confidentiality",  days_ago=3),
        ScoredSignal("sedar_going_concern",    days_ago=5),
    ]
    # Multi-category should score higher even with similar raw weights
    assert convergence_score(multi_cat) >= convergence_score(single_cat) * 0.95


def test_score_capped_at_100():
    """No matter how many signals, score never exceeds 100."""
    many_signals = [
        ScoredSignal(sig, days_ago=0)
        for sig in ["sedar_confidentiality", "edgar_conf_treatment",
                    "canlii_defendant", "jet_baystreet_2x",
                    "osc_enforcement", "linkedin_gc_spike",
                    "news_merger", "job_cco_urgent"]
    ]
    assert convergence_score(many_signals) <= 100.0


def test_practice_area_ma_from_sedar():
    signals = [
        ScoredSignal("sedar_confidentiality",        days_ago=1),
        ScoredSignal("sedar_business_acquisition",   days_ago=2),
    ]
    pa, conf = classify_practice_area(signals)
    assert pa == "Corporate / M&A"
    assert conf >= 0.90


def test_practice_area_litigation_from_canlii():
    signals = [ScoredSignal("canlii_defendant", days_ago=1)]
    pa, conf = classify_practice_area(signals)
    assert pa == "Litigation"


def test_practice_area_unknown_for_empty():
    pa, conf = classify_practice_area([])
    assert pa == "General / Unknown"
    assert conf == 0.0


def test_crossed_threshold_detects_crossing():
    assert crossed_threshold(72.0, 83.0) == "HIGH"
    assert crossed_threshold(88.0, 97.0) == "CRITICAL"
    assert crossed_threshold(50.0, 68.0) == "MODERATE"
    assert crossed_threshold(30.0, 52.0) == "WATCH"


def test_crossed_threshold_no_crossing():
    # Already above threshold — no new crossing
    assert crossed_threshold(85.0, 90.0) is None
    # Score went down
    assert crossed_threshold(95.0, 80.0) is None


def test_decayed_weight_at_zero_days():
    sig = ScoredSignal("sedar_confidentiality", days_ago=0)
    # decay factor at 0 days = e^0 = 1.0
    assert abs(sig.decayed_weight - sig.base_weight) < 0.001


def test_decayed_weight_at_half_life():
    """At 21 days (half-life), weight should be approximately halved."""
    sig = ScoredSignal("sedar_confidentiality", days_ago=21)
    expected = sig.base_weight * 0.5
    assert abs(sig.decayed_weight - expected) < 0.05


def test_five_category_boost():
    """5+ unique categories should get a 30% boost."""
    five_cats = [
        ScoredSignal("sedar_material_change",  days_ago=2),  # filings
        ScoredSignal("canlii_defendant",        days_ago=2),  # litigation
        ScoredSignal("jet_baystreet_2x",        days_ago=2),  # geospatial
        ScoredSignal("news_lawsuit",            days_ago=2),  # news
        ScoredSignal("linkedin_gc_spike",       days_ago=2),  # people
    ]
    three_cats = [
        ScoredSignal("sedar_material_change",  days_ago=2),
        ScoredSignal("sedar_confidentiality",  days_ago=2),
        ScoredSignal("canlii_defendant",        days_ago=2),
        ScoredSignal("canlii_class_action",     days_ago=2),
        ScoredSignal("news_lawsuit",            days_ago=2),
    ]
    assert convergence_score(five_cats) >= convergence_score(three_cats)
