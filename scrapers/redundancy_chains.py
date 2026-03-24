"""
app/scrapers/redundancy_chains.py — Redundancy Chain Definitions.

For every critical signal type, we define a primary → fallback → tertiary
source chain. When a primary scraper grades D or F, the chain activates
its fallback automatically.

Architecture:
  - Chains are signal-type based, not scraper based
  - The orchestrator (Agent 003) checks grades before routing tasks
  - If primary is D/F, it runs the fallback instead
  - If primary AND fallback are both D/F, tertiary runs + alert fires

Chain activation logic (in scraper_tasks.py):
  1. Grader runs (weekly via Agent 009)
  2. For each chain: check primary grade
  3. If primary grade ≤ C: log warning, activate fallback
  4. If primary + fallback both ≤ D: activate tertiary + PagerDuty alert

Signal type coverage:
  Every signal type that feeds a scoring engine must have at least 2 sources.
  Signal types with only 1 source are flagged SINGLE_POINT_OF_FAILURE.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import structlog

log = structlog.get_logger(__name__)


@dataclass(frozen=True)
class RedundancyChain:
    signal_type: str
    description: str
    primary: str                    # source_id
    fallback: str | None = None     # source_id — activated when primary ≤ C
    tertiary: str | None = None     # source_id — activated when fallback ≤ D
    is_critical: bool = True        # critical signals have SLA requirements
    activation_grade: str = "D"     # activate fallback when primary reaches this grade


# ── Corporate Filing Chains ────────────────────────────────────────────────────
CORPORATE_CHAINS: list[RedundancyChain] = [
    RedundancyChain(
        signal_type="filing_material_change",
        description="Material change filings — SEDAR+ primary, EDGAR cross-border fallback",
        primary="corporate_sedar_plus",
        fallback="corporate_edgar",
        tertiary=None,
        is_critical=True,
    ),
    RedundancyChain(
        signal_type="filing_insider_trade",
        description="Insider trading — SEDI primary, no direct fallback",
        primary="corporate_sedi",
        fallback=None,
        is_critical=True,
        activation_grade="F",  # Only escalate on full failure — SEDI is authoritative
    ),
    RedundancyChain(
        signal_type="filing_annual_report",
        description="Annual reports / AIF — SEDAR+ primary, EDGAR fallback",
        primary="corporate_sedar_plus",
        fallback="corporate_edgar",
    ),
    RedundancyChain(
        signal_type="regulatory_gazette_notice",
        description="Canada Gazette — single source",
        primary="corporate_canada_gazette",
        fallback=None,
        is_critical=False,
    ),
    RedundancyChain(
        signal_type="insolvency_filing",
        description="OSB insolvency filings — primary source",
        primary="corporate_osb",
        fallback="legal_canlii",   # CanLII will have CCAA filings as backup
        is_critical=True,
    ),
]

# ── Legal / Court Chains ───────────────────────────────────────────────────────
LEGAL_CHAINS: list[RedundancyChain] = [
    RedundancyChain(
        signal_type="caselaw_decision",
        description="Court decisions — CanLII API primary, CanLII scrape fallback",
        primary="legal_canlii",
        fallback="legal_canlii_scrape",
        is_critical=True,
    ),
    RedundancyChain(
        signal_type="scc_decision",
        description="SCC decisions — SCC RSS primary, CanLII fallback",
        primary="legal_scc",
        fallback="legal_canlii",
    ),
    RedundancyChain(
        signal_type="competition_tribunal_decision",
        description="Competition Tribunal — single source",
        primary="legal_competition_tribunal",
        fallback="legal_canlii",
        is_critical=True,
    ),
]

# ── Regulatory Enforcement Chains ─────────────────────────────────────────────
REGULATORY_CHAINS: list[RedundancyChain] = [
    RedundancyChain(
        signal_type="regulatory_osc_enforcement",
        description="OSC enforcement — OSC RSS primary, BCSC fallback (cross-validation)",
        primary="regulatory_osc",
        fallback="regulatory_bcsc",
        is_critical=True,
    ),
    RedundancyChain(
        signal_type="regulatory_fintrac_penalty",
        description="FINTRAC enforcement — single authoritative source",
        primary="regulatory_fintrac",
        fallback=None,
        is_critical=True,
        activation_grade="F",
    ),
    RedundancyChain(
        signal_type="regulatory_competition_enforcement",
        description="Competition Bureau — RSS primary, DOJ fallback",
        primary="regulatory_competition_bureau",
        fallback="regulatory_doj",
        is_critical=True,
    ),
    RedundancyChain(
        signal_type="regulatory_privacy_investigation",
        description="OPC — Privacy Commissioner primary, no direct fallback",
        primary="regulatory_opc",
        fallback=None,
        is_critical=True,
        activation_grade="F",
    ),
    RedundancyChain(
        signal_type="regulatory_osfi_enforcement",
        description="OSFI — OSFI enforcement primary, AMF Quebec fallback",
        primary="regulatory_osfi_enforcement",
        fallback="regulatory_amf_quebec",
        is_critical=True,
    ),
    RedundancyChain(
        signal_type="regulatory_sec_aaer",
        description="SEC AAER cross-border — SEC AAER primary, US DOJ fallback",
        primary="regulatory_sec_aaer",
        fallback="regulatory_us_doj",
        is_critical=False,
    ),
]

# ── Market Signal Chains ───────────────────────────────────────────────────────
MARKET_CHAINS: list[RedundancyChain] = [
    RedundancyChain(
        signal_type="market_price_signal",
        description="Market data — Alpha Vantage primary, Yahoo Finance fallback, TMX tertiary",
        primary="market_alpha_vantage",
        fallback="market_yahoo_finance",
        tertiary="market_tmx_datalinx",
        is_critical=True,
    ),
    RedundancyChain(
        signal_type="market_options_flow",
        description="Options flow — SEDAR BAR primary, Yahoo fallback",
        primary="market_sedar_bar",
        fallback="market_yahoo_finance",
        is_critical=False,
    ),
]

# ── News Signal Chains ─────────────────────────────────────────────────────────
NEWS_CHAINS: list[RedundancyChain] = [
    RedundancyChain(
        signal_type="news_legal_mention",
        description="Legal news — Globe primary, FP fallback, BNN tertiary",
        primary="news_globe_mail",
        fallback="news_financial_post",
        tertiary="news_bnn_bloomberg",
        is_critical=True,
    ),
    RedundancyChain(
        signal_type="news_regulatory_mention",
        description="Regulatory news — Reuters Canada primary, CBC fallback",
        primary="news_reuters",
        fallback="news_cbc_business",
        is_critical=True,
    ),
    RedundancyChain(
        signal_type="news_ma_mention",
        description="M&A news — Google News primary, FP fallback",
        primary="news_google_news",
        fallback="news_financial_post",
        is_critical=False,
    ),
]

# ── Social Signal Chains ───────────────────────────────────────────────────────
SOCIAL_CHAINS: list[RedundancyChain] = [
    RedundancyChain(
        signal_type="social_reddit_legal_mention",
        description="Reddit legal — Reddit OAuth2 primary, no fallback (unique source)",
        primary="social_reddit",
        fallback=None,
        is_critical=False,
        activation_grade="F",
    ),
    RedundancyChain(
        signal_type="social_breach_detected",
        description="Data breach — HIBP primary, CCCS advisory fallback",
        primary="social_breach_monitor",
        fallback="social_breach_monitor",  # CCCS part of same scraper
        is_critical=True,
        activation_grade="F",
    ),
    RedundancyChain(
        signal_type="social_stockhouse_legal_mention",
        description="Stockhouse — single retail investor source",
        primary="social_stockhouse",
        fallback=None,
        is_critical=False,
    ),
]

# ── Geo Signal Chains ──────────────────────────────────────────────────────────
GEO_CHAINS: list[RedundancyChain] = [
    RedundancyChain(
        signal_type="geo_trends_legal_spike",
        description="Google Trends — pytrends primary, no fallback",
        primary="geo_google_trends",
        fallback=None,
        is_critical=False,
        activation_grade="F",
    ),
    RedundancyChain(
        signal_type="geo_statscan_court_volume",
        description="Court volume — StatsCan WDS primary, no fallback",
        primary="geo_statscan",
        fallback=None,
        is_critical=False,
        activation_grade="F",
    ),
]

# ── Law Blog Chains ────────────────────────────────────────────────────────────
BLOG_CHAINS: list[RedundancyChain] = [
    RedundancyChain(
        signal_type="blog_practice_alert",
        description="Law blog — RSS primary, HTML fallback (built into each firm scraper)",
        primary="lawblog_mccarthy",   # representative — all 27 follow same pattern
        fallback=None,               # HTML fallback is inside each scraper, not a chain
        is_critical=False,
        activation_grade="F",
    ),
]

# ── Master chain registry ──────────────────────────────────────────────────────
ALL_CHAINS: list[RedundancyChain] = (
    CORPORATE_CHAINS
    + LEGAL_CHAINS
    + REGULATORY_CHAINS
    + MARKET_CHAINS
    + NEWS_CHAINS
    + SOCIAL_CHAINS
    + GEO_CHAINS
    + BLOG_CHAINS
)

CHAINS_BY_SIGNAL: dict[str, RedundancyChain] = {
    c.signal_type: c for c in ALL_CHAINS
}

# Signal types with no fallback — documented SPOFs
SINGLE_POINTS_OF_FAILURE = [
    c.signal_type for c in ALL_CHAINS
    if c.fallback is None and c.is_critical
]


class RedundancyOrchestrator:
    """
    Determines which scrapers to run given current grade data.
    Called by Agent 003 (Scraper Orchestrator) before each task.
    """

    def __init__(self, grades: dict[str, "ScraperGrade"]) -> None:  # type: ignore[name-defined]
        self._grades = grades

    def get_active_source(self, signal_type: str) -> str | None:
        """
        Returns the source_id that should run for a given signal type.
        Respects chain activation rules.
        """
        chain = CHAINS_BY_SIGNAL.get(signal_type)
        if not chain:
            return None

        primary_grade = self._grades.get(chain.primary)
        primary_letter = primary_grade.grade if primary_grade else "F"

        # Determine if primary is healthy enough
        grade_order = ["A", "B", "C", "D", "F"]
        activation_idx = grade_order.index(chain.activation_grade)
        primary_idx = grade_order.index(primary_letter)

        if primary_idx < activation_idx:
            # Primary is healthy
            return chain.primary

        # Primary degraded — try fallback
        if chain.fallback:
            fallback_grade = self._grades.get(chain.fallback)
            fallback_letter = fallback_grade.grade if fallback_grade else "F"
            fallback_idx = grade_order.index(fallback_letter)

            if fallback_idx < grade_order.index("D"):
                log.warning("chain_activated_fallback",
                            signal_type=signal_type,
                            primary=chain.primary,
                            primary_grade=primary_letter,
                            fallback=chain.fallback)
                return chain.fallback

            # Fallback also degraded — try tertiary
            if chain.tertiary:
                log.error("chain_activated_tertiary",
                          signal_type=signal_type,
                          primary=chain.primary,
                          fallback=chain.fallback,
                          tertiary=chain.tertiary)
                return chain.tertiary

        # All sources failed — log critical alert
        if chain.is_critical:
            log.error("chain_fully_degraded_CRITICAL",
                      signal_type=signal_type,
                      chain=chain,
                      note="Signal gap: all sources for this signal type are degraded.")
        return None

    def get_degraded_signals(self) -> list[dict[str, Any]]:
        """Return all signal types where the chain has activated."""
        degraded = []
        grade_order = ["A", "B", "C", "D", "F"]
        for chain in ALL_CHAINS:
            primary_grade = self._grades.get(chain.primary)
            primary_letter = primary_grade.grade if primary_grade else "F"
            activation_idx = grade_order.index(chain.activation_grade)
            primary_idx = grade_order.index(primary_letter)
            if primary_idx >= activation_idx:
                degraded.append({
                    "signal_type": chain.signal_type,
                    "primary": chain.primary,
                    "primary_grade": primary_letter,
                    "fallback": chain.fallback,
                    "is_critical": chain.is_critical,
                })
        return degraded
