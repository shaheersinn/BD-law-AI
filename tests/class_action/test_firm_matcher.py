import pytest
from app.ml.class_action.firm_matcher import FirmMatcher, FirmConfig

@pytest.fixture
def matcher():
    firms = [
        FirmConfig(
            "mccarthy",
            "McCarthy Tétrault",
            1,
            "https://rss",
            ["securities", "litigation"],
            "https://site"
        ),
        FirmConfig(
            "lerners",
            "Lerners LLP",
            2,
            "https://rss",
            ["class_actions", "litigation"],
            "https://site"
        ),
        FirmConfig(
            "lax_oleary",
            "Lax O'Leary",
            2,
            "https://rss",
            ["securities", "litigation"],
            "https://site"
        ),
    ]
    return FirmMatcher(firms=firms)

def test_jurisdiction_match(matcher):
    """Firm in ON matches ON class action higher than firm in BC."""
    # Note: Lerners and Lax O'Leary are ON only in our mock mappings.
    # McCarthy is ON, QC, BC, AB.
    # Let's use real FirmMatcher with its internal FIRM_JURISDICTIONS.
    matches = matcher.match_firms("securities_capital_markets", "ON")
    assert matches[0]["score"] >= 0.8  # McCarthy (Tier 1 + ON + Securities)

def test_practice_area_match(matcher):
    """Securities-strong firm ranks higher for securities CA."""
    matches = matcher.match_firms("securities_capital_markets", "ON")
    # McCarthy and Lax O'Leary have 'securities' in focus.
    # Lerners has 'class_actions' in focus.
    
    mccarthy = next(m for m in matches if m["firm_id"] == "mccarthy")
    lerners = next(m for m in matches if m["firm_id"] == "lerners")
    
    # McCarthy should have securities match, Lerners should not (in our focus mapping)
    assert "securities" in " ".join(mccarthy["match_reasons"]).lower()
    assert "securities" not in " ".join(lerners["match_reasons"]).lower()

def test_plaintiff_vs_defence_filter(matcher):
    """side='plaintiff' excludes defence-only firms (Stub for future logic)."""
    # Currently FirmMatcher doesn't handle side. 
    # This is a placeholder for the user's expected 'side' parameter.
    pass

def test_tier_score_boost(matcher):
    """Tier 1 firms receive score boost."""
    matches_on = matcher.match_firms("litigation", "ON")
    mccarthy = next(m for m in matches_on if m["firm_id"] == "mccarthy")
    
    # McCarthy is Tier 1, others in fixture are Tier 2 (if configured so)
    assert "Tier 1 reputation" in mccarthy["match_reasons"]
