"""
app/scrapers/alternative_discovery.py — Alternative Source Discovery.

When a scraper grades D or F, this module identifies candidate replacement
sources and scores them for viability.

Methodology:
  1. Map dead scraper to its signal types
  2. Query a curated catalogue of known alternative sources
  3. Score candidates by: data quality, cost, reliability, overlap with
     existing coverage
  4. Return ranked alternatives with implementation difficulty rating

This module does NOT automatically deploy new scrapers.
It produces a recommendation report for human review.
Agent 009 (Scraper Grader) triggers this when a scraper hits grade D.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import structlog

log = structlog.get_logger(__name__)


@dataclass
class AlternativeSource:
    source_id_candidate: str       # What the new scraper's source_id should be
    display_name: str
    url: str
    data_type: str                 # "api" | "rss" | "html" | "bulk_download"
    cost: str                      # "free" | "freemium" | "paid"
    estimated_cost_cad: str        # e.g. "$0/mo" | "$50/mo"
    signal_types_covered: list[str]
    implementation_difficulty: str  # "easy" | "medium" | "hard"
    estimated_hours: int            # implementation effort
    notes: str
    replaces: str                  # source_id it would replace


# ── Alternative source catalogue ──────────────────────────────────────────────
# This is the curated list of known-viable alternatives per signal type.
# Updated as new sources are discovered.

ALTERNATIVE_CATALOGUE: list[AlternativeSource] = [

    # ── SEDAR+ alternatives ────────────────────────────────────────────────────
    AlternativeSource(
        source_id_candidate="corporate_refinitiv_sedar",
        display_name="Refinitiv Filings API (SEDAR collection)",
        url="https://developers.lseg.com/en/api-catalog/refinitiv-data-platform/filings-API",
        data_type="api",
        cost="paid",
        estimated_cost_cad="$500+/mo",
        signal_types_covered=["filing_material_change", "filing_annual_report", "filing_prospectus"],
        implementation_difficulty="medium",
        estimated_hours=16,
        notes="Refinitiv provides SEDAR+ bulk collection via paid API. "
              "High quality, reliable, but expensive. Justifiable if SEDAR+ scraping breaks.",
        replaces="corporate_sedar_plus",
    ),
    AlternativeSource(
        source_id_candidate="corporate_tsxv_rss",
        display_name="TSX/TSXV News Release RSS",
        url="https://www.tsx.com/news-and-events/news-releases",
        data_type="rss",
        cost="free",
        estimated_cost_cad="$0/mo",
        signal_types_covered=["filing_material_change", "news_ma_mention"],
        implementation_difficulty="easy",
        estimated_hours=4,
        notes="TSX publishes news releases via RSS. Covers listed company announcements "
              "including material changes. Free, no authentication.",
        replaces="corporate_sedar_plus",
    ),

    # ── Market data alternatives ───────────────────────────────────────────────
    AlternativeSource(
        source_id_candidate="market_polygon_io",
        display_name="Polygon.io (Canadian stocks)",
        url="https://polygon.io",
        data_type="api",
        cost="freemium",
        estimated_cost_cad="$0-$29/mo",
        signal_types_covered=["market_price_signal", "market_options_flow"],
        implementation_difficulty="easy",
        estimated_hours=6,
        notes="Polygon.io free tier covers delayed data. Paid tier ($29/mo) gives "
              "real-time data for TSX stocks. Good Alpha Vantage replacement.",
        replaces="market_alpha_vantage",
    ),
    AlternativeSource(
        source_id_candidate="market_bank_of_canada",
        display_name="Bank of Canada Exchange Rates & Stats API",
        url="https://www.bankofcanada.ca/valet/docs",
        data_type="api",
        cost="free",
        estimated_cost_cad="$0/mo",
        signal_types_covered=["market_macro_signal", "geo_statscan_employment_stress"],
        implementation_difficulty="easy",
        estimated_hours=4,
        notes="Bank of Canada Valet API — free, no key, JSON. "
              "Interest rates, exchange rates, key policy rates. "
              "Critical for the interest_rate → insolvency lag signal.",
        replaces="market_alpha_vantage",
    ),

    # ── News alternatives ──────────────────────────────────────────────────────
    AlternativeSource(
        source_id_candidate="news_canadian_press",
        display_name="The Canadian Press RSS",
        url="https://www.thecanadianpress.com",
        data_type="rss",
        cost="free",
        estimated_cost_cad="$0/mo",
        signal_types_covered=["news_legal_mention", "news_regulatory_mention"],
        implementation_difficulty="easy",
        estimated_hours=4,
        notes="Canadian wire service. Good for regulatory and legal news. "
              "Often first to report enforcement actions.",
        replaces="news_globe_mail",
    ),
    AlternativeSource(
        source_id_candidate="news_law360_canada",
        display_name="Law360 Canada (paid)",
        url="https://www.law360.com/canada",
        data_type="html",
        cost="paid",
        estimated_cost_cad="$1,200+/yr",
        signal_types_covered=["news_legal_mention", "blog_practice_alert"],
        implementation_difficulty="hard",
        estimated_hours=20,
        notes="Premium legal news — very high signal quality but expensive. "
              "Consider only if law blog tier becomes insufficient.",
        replaces="news_globe_mail",
    ),

    # ── Social alternatives ────────────────────────────────────────────────────
    AlternativeSource(
        source_id_candidate="social_investing_com",
        display_name="Investing.com Canada news RSS",
        url="https://ca.investing.com/rss/news.rss",
        data_type="rss",
        cost="free",
        estimated_cost_cad="$0/mo",
        signal_types_covered=["social_reddit_distress", "news_ma_mention"],
        implementation_difficulty="easy",
        estimated_hours=3,
        notes="Good retail investor sentiment proxy. Free RSS, no auth.",
        replaces="social_reddit",
    ),
    AlternativeSource(
        source_id_candidate="social_cbc_comments",
        display_name="CBC Corporate News Section",
        url="https://www.cbc.ca/cmlink/rss-business",
        data_type="rss",
        cost="free",
        estimated_cost_cad="$0/mo",
        signal_types_covered=["news_regulatory_mention", "social_reddit_regulatory"],
        implementation_difficulty="easy",
        estimated_hours=2,
        notes="CBC Business RSS — reliable, free, high trust signal for regulatory news.",
        replaces="social_reddit",
    ),

    # ── Geo / macro alternatives ───────────────────────────────────────────────
    AlternativeSource(
        source_id_candidate="geo_bank_of_canada_rates",
        display_name="Bank of Canada Policy Rate History",
        url="https://www.bankofcanada.ca/valet/observations/V39079/json",
        data_type="api",
        cost="free",
        estimated_cost_cad="$0/mo",
        signal_types_covered=["geo_statscan_employment_stress", "market_macro_signal"],
        implementation_difficulty="easy",
        estimated_hours=3,
        notes="BoC overnight rate — feeds the interest_rate → insolvency 12-18mo lag model. "
              "Critical macro signal. Free, no auth, JSON.",
        replaces="geo_statscan",
    ),
    AlternativeSource(
        source_id_candidate="geo_cmhc_housing",
        display_name="CMHC Housing Market Data",
        url="https://www.cmhc-schl.gc.ca/en/data-and-research",
        data_type="bulk_download",
        cost="free",
        estimated_cost_cad="$0/mo",
        signal_types_covered=["geo_property_tax_arrears", "geo_statscan_employment_stress"],
        implementation_difficulty="medium",
        estimated_hours=8,
        notes="CMHC publishes housing stress data — useful as real estate + insolvency signal.",
        replaces="geo_municipal_property",
    ),

    # ── Law blog alternatives ──────────────────────────────────────────────────
    AlternativeSource(
        source_id_candidate="lawblog_thelawyersdaily",
        display_name="The Lawyer's Daily",
        url="https://www.thelawyersdaily.ca/rss",
        data_type="rss",
        cost="free",
        estimated_cost_cad="$0/mo",
        signal_types_covered=["blog_practice_alert", "blog_legal_trend"],
        implementation_difficulty="easy",
        estimated_hours=3,
        notes="Canadian legal news publication — good supplement to firm blogs for "
              "practice area trend detection. Free RSS.",
        replaces="lawblog_mccarthy",
    ),
    AlternativeSource(
        source_id_candidate="lawblog_slaw",
        display_name="Slaw.ca (Canadian law blog aggregator)",
        url="https://www.slaw.ca/feed",
        data_type="rss",
        cost="free",
        estimated_cost_cad="$0/mo",
        signal_types_covered=["blog_practice_alert", "blog_legal_trend"],
        implementation_difficulty="easy",
        estimated_hours=2,
        notes="Slaw aggregates dozens of Canadian law blogs. Single feed covers "
              "broad practice area commentary. High signal-to-noise ratio.",
        replaces="lawblog_lax_oleary",
    ),
]

# Index by source_id they replace
_BY_REPLACES: dict[str, list[AlternativeSource]] = {}
for _alt in ALTERNATIVE_CATALOGUE:
    _BY_REPLACES.setdefault(_alt.replaces, []).append(_alt)


class AlternativeDiscovery:
    """
    Recommends alternative sources for dead/degraded scrapers.
    Called by Agent 009 when a scraper hits grade D.
    """

    def get_alternatives(self, source_id: str) -> list[AlternativeSource]:
        """Return ranked alternatives for a given dead source_id."""
        candidates = _BY_REPLACES.get(source_id, [])
        # Rank: free first, then easy first, then by estimated_hours asc
        difficulty_rank = {"easy": 0, "medium": 1, "hard": 2}
        cost_rank = {"free": 0, "freemium": 1, "paid": 2}
        return sorted(
            candidates,
            key=lambda a: (cost_rank[a.cost], difficulty_rank[a.implementation_difficulty], a.estimated_hours),
        )

    def generate_report(self, degraded_source_ids: list[str]) -> dict[str, Any]:
        """
        Generate a full alternative source report for a list of degraded scrapers.
        This is what Agent 009 writes to the Phase 1C weekly report.
        """
        report: dict[str, Any] = {
            "total_degraded": len(degraded_source_ids),
            "total_with_alternatives": 0,
            "total_spof": 0,     # No alternatives found
            "recommendations": [],
        }

        for source_id in degraded_source_ids:
            alts = self.get_alternatives(source_id)
            if alts:
                report["total_with_alternatives"] += 1
                report["recommendations"].append({
                    "degraded_source": source_id,
                    "top_alternative": {
                        "source_id": alts[0].source_id_candidate,
                        "display_name": alts[0].display_name,
                        "cost": alts[0].cost,
                        "estimated_cost_cad": alts[0].estimated_cost_cad,
                        "implementation_difficulty": alts[0].implementation_difficulty,
                        "estimated_hours": alts[0].estimated_hours,
                        "notes": alts[0].notes,
                    },
                    "all_alternatives_count": len(alts),
                })
            else:
                report["total_spof"] += 1
                report["recommendations"].append({
                    "degraded_source": source_id,
                    "top_alternative": None,
                    "note": "NO ALTERNATIVE IDENTIFIED — manual investigation required.",
                })

        return report

    def get_quick_wins(self) -> list[AlternativeSource]:
        """Return all free + easy alternatives (can implement in <1 day)."""
        return [
            alt for alt in ALTERNATIVE_CATALOGUE
            if alt.cost == "free" and alt.implementation_difficulty == "easy"
        ]
