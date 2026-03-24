"""
app/ml/convergence.py — Bayesian signal convergence scoring.

This is the core scoring engine. Each signal has a base weight (probability
that it precedes a legal mandate within 90 days). Convergence score is:

    P(mandate) = 1 - ∏(1 - w_i * decay_i)

Multiple signals from different categories get a convergence multiplier.
"""

import math
from dataclasses import dataclass, field

# ── Signal catalogue ───────────────────────────────────────────────────────────
# Base weights from: historical mandate rate when this signal alone fires.
# These are calibrated priors — update from your data after 6 months.

SIGNAL_WEIGHTS: dict[str, float] = {
    # Corporate filings
    "sedar_material_change": 0.88,
    "sedar_business_acquisition": 0.92,
    "sedar_confidentiality": 0.91,
    "sedar_cease_trade": 0.87,
    "sedar_going_concern": 0.84,
    "sedar_auditor_change": 0.79,
    "sedar_director_resign": 0.76,
    "edgar_conf_treatment": 0.89,
    "edgar_sc13d": 0.85,
    "edgar_merger_confirmed": 0.96,
    "edgar_8k": 0.75,
    # Court / litigation
    "canlii_defendant": 0.88,
    "canlii_plaintiff": 0.72,
    "canlii_class_action": 0.91,
    "canlii_ccaa": 0.94,
    "canlii_injunction": 0.86,
    "canlii_tribunal": 0.83,
    # Regulatory enforcement
    "osc_enforcement": 0.90,
    "osfi_supervisory": 0.88,
    "competition_investigation": 0.91,
    "fintrac_noncompliance": 0.87,
    "health_canada_recall": 0.82,
    "eccc_enforcement": 0.89,
    "competitor_hit_same_industry": 0.71,
    # Job postings
    "job_gc_hire": 0.78,
    "job_cco_urgent": 0.85,
    "job_privacy_counsel": 0.82,
    "job_ma_counsel": 0.80,
    "job_litigation_counsel": 0.83,
    "job_deputy_gc_regulatory": 0.77,
    "job_environmental_counsel": 0.79,
    # Physical / geospatial
    "jet_baystreet_2x": 0.88,
    "satellite_parking_drop": 0.82,
    "permit_environmental": 0.83,
    "permit_construction": 0.76,
    "foot_traffic_competitor": 0.79,
    # News NLP
    "news_lawsuit": 0.75,
    "news_investigation": 0.81,
    "news_layoffs": 0.78,
    "news_data_breach": 0.87,
    "news_merger": 0.82,
    "news_exploring_strategic": 0.86,
    "news_legal_proceedings": 0.74,
    # LinkedIn / people
    "linkedin_gc_spike": 0.77,
    "linkedin_gc_posts_legal": 0.72,
    "linkedin_exec_departure": 0.74,
    "linkedin_mass_exits": 0.80,
    "linkedin_gc_connected_restr": 0.76,
}

# Signals grouped into categories for convergence multiplier
SIGNAL_CATEGORIES: dict[str, str] = {
    **dict.fromkeys(
        [
            "sedar_material_change",
            "sedar_business_acquisition",
            "sedar_confidentiality",
            "sedar_cease_trade",
            "sedar_going_concern",
            "sedar_auditor_change",
            "sedar_director_resign",
            "edgar_conf_treatment",
            "edgar_sc13d",
            "edgar_merger_confirmed",
            "edgar_8k",
        ],
        "filings",
    ),
    **dict.fromkeys(
        [
            "canlii_defendant",
            "canlii_plaintiff",
            "canlii_class_action",
            "canlii_ccaa",
            "canlii_injunction",
            "canlii_tribunal",
        ],
        "litigation",
    ),
    **dict.fromkeys(
        [
            "osc_enforcement",
            "osfi_supervisory",
            "competition_investigation",
            "fintrac_noncompliance",
            "health_canada_recall",
            "eccc_enforcement",
            "competitor_hit_same_industry",
        ],
        "enforcement",
    ),
    **dict.fromkeys(
        [
            "job_gc_hire",
            "job_cco_urgent",
            "job_privacy_counsel",
            "job_ma_counsel",
            "job_litigation_counsel",
            "job_deputy_gc_regulatory",
            "job_environmental_counsel",
        ],
        "jobs",
    ),
    **dict.fromkeys(
        [
            "jet_baystreet_2x",
            "satellite_parking_drop",
            "permit_environmental",
            "permit_construction",
            "foot_traffic_competitor",
        ],
        "geospatial",
    ),
    **dict.fromkeys(
        [
            "news_lawsuit",
            "news_investigation",
            "news_layoffs",
            "news_data_breach",
            "news_merger",
            "news_exploring_strategic",
            "news_legal_proceedings",
        ],
        "news",
    ),
    **dict.fromkeys(
        [
            "linkedin_gc_spike",
            "linkedin_gc_posts_legal",
            "linkedin_exec_departure",
            "linkedin_mass_exits",
            "linkedin_gc_connected_restr",
        ],
        "people",
    ),
}

# Practice area voting weights for each signal
PRACTICE_AREA_VOTES: dict[str, dict[str, float]] = {
    "sedar_material_change": {"Corporate / M&A": 1.0},
    "sedar_business_acquisition": {"Corporate / M&A": 1.0},
    "sedar_confidentiality": {"Corporate / M&A": 1.0},
    "sedar_cease_trade": {"Securities": 1.0},
    "sedar_going_concern": {"Restructuring / Insolvency": 1.0},
    "sedar_auditor_change": {"Corporate / Governance": 0.6, "Fraud": 0.4},
    "sedar_director_resign": {"Corporate / Governance": 1.0},
    "edgar_conf_treatment": {"Corporate / M&A": 1.0},
    "edgar_sc13d": {"Corporate / M&A": 0.8, "Securities": 0.2},
    "edgar_merger_confirmed": {"Corporate / M&A": 1.0},
    "edgar_8k": {"Corporate / M&A": 0.5, "Securities": 0.5},
    "canlii_defendant": {"Litigation": 1.0},
    "canlii_plaintiff": {"Litigation": 1.0},
    "canlii_class_action": {"Litigation": 1.0},
    "canlii_ccaa": {"Restructuring / Insolvency": 1.0},
    "canlii_injunction": {"Litigation": 0.7, "IP": 0.3},
    "canlii_tribunal": {"Regulatory": 1.0},
    "osc_enforcement": {"Securities": 1.0},
    "osfi_supervisory": {"Banking & Finance": 1.0},
    "competition_investigation": {"Competition": 1.0},
    "fintrac_noncompliance": {"Banking & Finance": 0.7, "Regulatory": 0.3},
    "health_canada_recall": {"Regulatory": 0.7, "Litigation": 0.3},
    "eccc_enforcement": {"Environmental": 1.0},
    "competitor_hit_same_industry": {"Regulatory": 1.0},
    "job_gc_hire": {},  # no practice vote
    "job_cco_urgent": {"Regulatory": 0.6, "Banking & Finance": 0.4},
    "job_privacy_counsel": {"Privacy & Cybersecurity": 1.0},
    "job_ma_counsel": {"Corporate / M&A": 1.0},
    "job_litigation_counsel": {"Litigation": 1.0},
    "job_deputy_gc_regulatory": {"Regulatory": 1.0},
    "job_environmental_counsel": {"Environmental": 1.0},
    "jet_baystreet_2x": {"Corporate / M&A": 1.0},
    "satellite_parking_drop": {"Restructuring / Insolvency": 0.6, "Employment & Labour": 0.4},
    "permit_environmental": {"Environmental": 1.0},
    "permit_construction": {"Real Estate & Construction": 1.0},
    "foot_traffic_competitor": {},
    "news_lawsuit": {"Litigation": 1.0},
    "news_investigation": {"Regulatory": 1.0},
    "news_layoffs": {"Employment & Labour": 0.6, "Restructuring / Insolvency": 0.4},
    "news_data_breach": {"Privacy & Cybersecurity": 1.0},
    "news_merger": {"Corporate / M&A": 1.0},
    "news_exploring_strategic": {"Corporate / M&A": 1.0},
    "news_legal_proceedings": {"Litigation": 1.0},
    "linkedin_gc_spike": {},
    "linkedin_gc_posts_legal": {},
    "linkedin_exec_departure": {"Corporate / Governance": 1.0},
    "linkedin_mass_exits": {"Employment & Labour": 0.7, "Restructuring / Insolvency": 0.3},
    "linkedin_gc_connected_restr": {"Restructuring / Insolvency": 1.0},
}


@dataclass
class ScoredSignal:
    signal_type: str
    days_ago: int
    fired_value: float = 1.0  # 1.0 = binary fired; could be continuous
    base_weight: float = field(init=False)
    category: str = field(init=False)

    def __post_init__(self) -> None:
        self.base_weight = SIGNAL_WEIGHTS.get(self.signal_type, 0.50)
        self.category = SIGNAL_CATEGORIES.get(self.signal_type, "other")

    @property
    def decayed_weight(self) -> float:
        """Exponential decay with half-life of 21 days."""
        decay = math.exp(-0.693 * self.days_ago / 21)
        return self.base_weight * decay * self.fired_value


def convergence_score(signals: list[ScoredSignal]) -> float:
    """
    Bayesian complement formula.
    Returns 0-100 probability that a mandate is forming.
    """
    if not signals:
        return 0.0

    prob_no_mandate = 1.0
    for sig in signals:
        prob_no_mandate *= 1.0 - sig.decayed_weight

    raw = (1.0 - prob_no_mandate) * 100

    # Convergence multiplier when signals span multiple categories
    unique_cats = {s.category for s in signals}
    if len(unique_cats) >= 5:
        raw = min(raw * 1.30, 100)
    elif len(unique_cats) >= 3:
        raw = min(raw * 1.18, 100)

    return round(raw, 1)


def classify_practice_area(signals: list[ScoredSignal]) -> tuple[str, float]:
    """
    Weighted vote classifier.
    Returns (practice_area_name, confidence_0_to_1).
    """
    from collections import defaultdict

    votes: dict[str, float] = defaultdict(float)

    for sig in signals:
        pa_votes = PRACTICE_AREA_VOTES.get(sig.signal_type, {})
        for pa, weight in pa_votes.items():
            votes[pa] += sig.decayed_weight * weight

    if not votes:
        return ("General / Unknown", 0.0)

    total = sum(votes.values())
    ranked = sorted(votes.items(), key=lambda x: x[1], reverse=True)
    top_pa, top_score = ranked[0]
    confidence = top_score / total if total > 0 else 0.0

    return (top_pa, round(confidence, 3))


def threshold_label(score: float) -> str | None:
    """Map a convergence score to its alert threshold label."""
    if score >= 95:
        return "CRITICAL"
    elif score >= 80:
        return "HIGH"
    elif score >= 65:
        return "MODERATE"
    elif score >= 50:
        return "WATCH"
    return None


def crossed_threshold(prev: float, curr: float) -> str | None:
    """Return threshold name if the score moved across a boundary, else None."""
    thresholds = [("CRITICAL", 95), ("HIGH", 80), ("MODERATE", 65), ("WATCH", 50)]
    for name, val in thresholds:
        if prev < val <= curr:
            return name
    return None
