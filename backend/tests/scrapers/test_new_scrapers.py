"""
Tests for all 28 new scrapers added in Phase S-NEW (1-6).

Covers:
  - Instantiation of each scraper
  - Correct source_id, source_name, signal_types, CATEGORY
  - scrape() returns list[ScraperResult] with mocked HTTP
  - Signal types match SIGNAL_WEIGHTS keys
  - Graceful degradation on HTTP failure
  - Celery task registration
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Convergence engine
from app.ml.convergence.engine import PRACTICE_AREA_VOTES, SIGNAL_CATEGORIES, SIGNAL_WEIGHTS
from app.scrapers.base import ScraperResult

# Bank of Canada enhancement
from app.scrapers.corporate.bank_of_canada import BankOfCanadaScraper
from app.scrapers.courts.bc_cso import BCCSOScraper

# Phase 4: Courts + Energy + IP
from app.scrapers.courts.ontario_commercial_list import OntarioCommercialListScraper
from app.scrapers.courts.soquij import SOQUIJScraper
from app.scrapers.energy.cer_pipeline import CERPipelineScraper

# Phase 6: Environmental + Labour
from app.scrapers.environmental.npri import NPRIScraper

# Phase 3: Financial Stress + Legal Gap
from app.scrapers.financial_stress.ppsa import PPSAScraper
from app.scrapers.financial_stress.private_credit import PrivateCreditScraper
from app.scrapers.financial_stress.sp_ratings import SPRatingsScraper
from app.scrapers.grants.federal_grants import FederalGrantsScraper
from app.scrapers.hnwi.art_auctions import ArtAuctionScraper
from app.scrapers.hnwi.cra_charities import CRACharitiesScraper
from app.scrapers.hnwi.probate_filings import ProbateFilingsScraper

# ── All 28 scraper classes ────────────────────────────────────────────────────
# Phase 1: HNWI
from app.scrapers.hnwi.trust_aging import TrustAgingScraper
from app.scrapers.hnwi.vessel_registry import VesselRegistryScraper
from app.scrapers.immigration.ircc_express_entry import IRCCExpressEntryScraper

# Phase 2: Immigration + PE/VC
from app.scrapers.immigration.lmia import LMIAScraper
from app.scrapers.ip.cipo_trademarks import CIPOTrademarksScraper
from app.scrapers.labour.canada_labour_code_naming import CanadaLabourCodeNamingScraper
from app.scrapers.labour.worksafebc import WorkSafeBCScraper
from app.scrapers.legal.tax_court import TaxCourtScraper
from app.scrapers.macro.cmhc import CMHCScraper

# Phase 5: Ownership + Pension + Startups + Private Credit
from app.scrapers.ownership.beneficial_ownership import BeneficialOwnershipScraper
from app.scrapers.pe.fund_vintage import FundVintageScraper
from app.scrapers.pe.pension_funds import PensionFundsScraper
from app.scrapers.pe.vc_deals import VCDealsScraper
from app.scrapers.restructuring.ccaa_monitors import CCAAMonitorsScraper
from app.scrapers.startups.accelerator_cohorts import AcceleratorCohortsScraper

# ── Scraper metadata specs ────────────────────────────────────────────────────

SCRAPER_SPECS = [
    # (class, source_id, category, signal_types)
    (TrustAgingScraper, "hnwi_trust_aging", "hnwi", ["trust_deemed_disposition_approaching"]),
    (ArtAuctionScraper, "hnwi_art_auctions", "hnwi", ["estate_art_liquidation"]),
    (ProbateFilingsScraper, "hnwi_probate_filings", "hnwi", ["probate_filing_high_value"]),
    (CRACharitiesScraper, "hnwi_cra_charities", "hnwi", ["hnwi_foundation_director_change"]),
    (VesselRegistryScraper, "hnwi_vessel_registry", "hnwi", ["vessel_registry_change"]),
    (LMIAScraper, "immigration_lmia", "immigration", ["immigration_lmia_spike"]),
    (IRCCExpressEntryScraper, "immigration_ircc", "immigration", ["immigration_express_entry_draw"]),
    (FundVintageScraper, "pe_fund_vintage", "pe", ["pe_fund_exit_pressure"]),
    (VCDealsScraper, "pe_vc_deals", "pe", ["vc_series_b_plus"]),
    (PPSAScraper, "financial_stress_ppsa", "financial_stress", ["ppsa_layered_lending"]),
    (SPRatingsScraper, "financial_stress_sp_ratings", "financial_stress", ["credit_rating_downgrade_sp"]),
    (TaxCourtScraper, "legal_tax_court", "legal", ["tax_court_dispute"]),
    (CCAAMonitorsScraper, "restructuring_ccaa_monitors", "restructuring", ["ccaa_monitor_report"]),
    (FederalGrantsScraper, "grants_federal", "grants", ["federal_grant_awarded"]),
    (OntarioCommercialListScraper, "courts_ontario_commercial", "courts", ["ontario_commercial_list_filing"]),
    (BCCSOScraper, "courts_bc_cso", "courts", ["bc_supreme_court_filing"]),
    (SOQUIJScraper, "courts_soquij", "courts", ["quebec_superior_court_filing"]),
    (CERPipelineScraper, "energy_cer_pipeline", "energy", ["cer_pipeline_incident"]),
    (CMHCScraper, "macro_cmhc", "macro", ["cmhc_housing_starts_decline"]),
    (CIPOTrademarksScraper, "ip_cipo_trademarks", "ip", ["trademark_new_class_expansion"]),
    (BeneficialOwnershipScraper, "ownership_beneficial", "ownership", ["beneficial_owner_change"]),
    (PensionFundsScraper, "pe_pension_funds", "pe", ["pension_fund_investment"]),
    (AcceleratorCohortsScraper, "startups_accelerators", "startups", ["accelerator_cohort_member"]),
    (PrivateCreditScraper, "financial_stress_private_credit", "financial_stress", ["private_credit_deterioration"]),
    (NPRIScraper, "environmental_npri", "environmental", ["npri_pollution_spike"]),
    (CanadaLabourCodeNamingScraper, "labour_code_naming", "labour", ["labour_code_payment_order"]),
    (WorkSafeBCScraper, "labour_worksafebc", "labour", ["worksafebc_penalty"]),
]

# All 28 new signal types
NEW_SIGNAL_TYPES = [
    "trust_deemed_disposition_approaching",
    "estate_art_liquidation",
    "probate_filing_high_value",
    "hnwi_foundation_director_change",
    "vessel_registry_change",
    "immigration_lmia_spike",
    "immigration_express_entry_draw",
    "pe_fund_exit_pressure",
    "vc_series_b_plus",
    "ppsa_layered_lending",
    "credit_rating_downgrade_sp",
    "tax_court_dispute",
    "ccaa_monitor_report",
    "federal_grant_awarded",
    "ontario_commercial_list_filing",
    "bc_supreme_court_filing",
    "quebec_superior_court_filing",
    "cer_pipeline_incident",
    "cmhc_housing_starts_decline",
    "trademark_new_class_expansion",
    "beneficial_owner_change",
    "pension_fund_investment",
    "accelerator_cohort_member",
    "private_credit_deterioration",
    "npri_pollution_spike",
    "labour_code_payment_order",
    "worksafebc_penalty",
    "macro_bos_credit_tightening",
]


# ── Instantiation Tests ──────────────────────────────────────────────────────


class TestScraperInstantiation:
    """Each scraper can be instantiated and has correct metadata."""

    @pytest.mark.parametrize(
        "cls,expected_source_id,expected_category,expected_signals",
        SCRAPER_SPECS,
        ids=[s[1] for s in SCRAPER_SPECS],
    )
    def test_instantiation(
        self, cls, expected_source_id, expected_category, expected_signals
    ):
        scraper = cls()
        assert scraper.source_id == expected_source_id
        assert scraper.CATEGORY == expected_category
        assert scraper.signal_types == expected_signals
        assert scraper.source_name  # must have a non-empty name

    def test_total_new_scrapers(self):
        """Verify we have exactly 27 new scraper classes (28 signals, but BankOfCanada is enhanced, not new)."""
        assert len(SCRAPER_SPECS) == 27

    def test_bank_of_canada_enhanced(self):
        """Bank of Canada scraper now includes macro_bos_credit_tightening."""
        scraper = BankOfCanadaScraper()
        assert "macro_bos_credit_tightening" in scraper.signal_types
        assert "monetary_policy_rate_change" in scraper.signal_types
        assert "financial_system_alert" in scraper.signal_types


# ── Convergence Engine Tests ──────────────────────────────────────────────────


class TestConvergenceEngineUpdates:
    """All 28 new signal types are in SIGNAL_WEIGHTS, SIGNAL_CATEGORIES, PRACTICE_AREA_VOTES."""

    @pytest.mark.parametrize("signal_type", NEW_SIGNAL_TYPES)
    def test_signal_in_weights(self, signal_type):
        assert signal_type in SIGNAL_WEIGHTS, f"{signal_type} missing from SIGNAL_WEIGHTS"

    @pytest.mark.parametrize("signal_type", NEW_SIGNAL_TYPES)
    def test_signal_in_categories(self, signal_type):
        assert signal_type in SIGNAL_CATEGORIES, f"{signal_type} missing from SIGNAL_CATEGORIES"

    @pytest.mark.parametrize("signal_type", NEW_SIGNAL_TYPES)
    def test_signal_in_practice_area_votes(self, signal_type):
        assert signal_type in PRACTICE_AREA_VOTES, f"{signal_type} missing from PRACTICE_AREA_VOTES"

    def test_signal_weights_values_valid(self):
        """All signal weights must be between 0 and 1."""
        for signal_type in NEW_SIGNAL_TYPES:
            weight = SIGNAL_WEIGHTS[signal_type]
            assert 0.0 < weight <= 1.0, f"{signal_type} weight {weight} out of range"

    def test_ccaa_monitor_highest_weight(self):
        """ccaa_monitor_report should have the highest weight among new signals."""
        ccaa_weight = SIGNAL_WEIGHTS["ccaa_monitor_report"]
        for st in NEW_SIGNAL_TYPES:
            if st != "ccaa_monitor_report":
                assert SIGNAL_WEIGHTS[st] <= ccaa_weight, (
                    f"{st} ({SIGNAL_WEIGHTS[st]}) > ccaa_monitor_report ({ccaa_weight})"
                )

    def test_total_signal_weights_count(self):
        """SIGNAL_WEIGHTS should have original signals + 28 new ones."""
        # Original had ~130 entries, now we added 28 more
        assert len(SIGNAL_WEIGHTS) >= 130 + 28


# ── Scraper Degradation Tests ────────────────────────────────────────────────


class TestScraperDegradation:
    """Scrapers degrade gracefully on HTTP failures."""

    @pytest.mark.asyncio
    async def test_private_credit_no_api_key(self):
        """Private credit scraper returns [] when no API keys configured."""
        scraper = PrivateCreditScraper()
        with patch("app.scrapers.financial_stress.private_credit.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                dnb_api_key="", equifax_api_key=""
            )
            results = await scraper.scrape()
            assert results == []

    @pytest.mark.asyncio
    async def test_scraper_http_failure_returns_empty(self):
        """A scraper that gets a non-200 response should return []."""
        scraper = LMIAScraper()
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        with patch.object(scraper, "get", new_callable=AsyncMock, return_value=mock_resp):
            results = await scraper.scrape()
            assert isinstance(results, list)
            assert len(results) == 0

    @pytest.mark.asyncio
    async def test_soquij_auth_required(self):
        """SOQUIJ scraper degrades when auth required (401/403)."""
        scraper = SOQUIJScraper()
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        with patch.object(scraper, "get", new_callable=AsyncMock, return_value=mock_resp):
            results = await scraper.scrape()
            assert results == []

    @pytest.mark.asyncio
    async def test_ppsa_auth_required(self):
        """PPSA scraper degrades when auth required."""
        scraper = PPSAScraper()
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        with patch.object(scraper, "get", new_callable=AsyncMock, return_value=mock_resp):
            with patch.object(scraper, "get_soup", new_callable=AsyncMock, return_value=None):
                results = await scraper.scrape()
                assert results == []


# ── Scraper Result Shape Tests ───────────────────────────────────────────────


class TestScraperResultShape:
    """Scrapers return valid ScraperResult objects."""

    @pytest.mark.asyncio
    async def test_lmia_csv_parsing(self):
        """LMIA scraper parses CSV and produces correct signal type."""
        scraper = LMIAScraper()
        csv_data = (
            "Employer,Province/Territory,Year,Positions\n"
            "Test Corp,ON,2024,5\n"
            "Test Corp,ON,2025,20\n"
        )
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = csv_data
        with patch.object(scraper, "get", new_callable=AsyncMock, return_value=mock_resp):
            results = await scraper.scrape()
            assert isinstance(results, list)
            for r in results:
                assert isinstance(r, ScraperResult)
                assert r.source_id == "immigration_lmia"
                assert r.signal_type == "immigration_lmia_spike"

    @pytest.mark.asyncio
    async def test_vc_deals_rss_parsing(self):
        """VC deals scraper parses BetaKit RSS for funding rounds."""
        scraper = VCDealsScraper()
        rss_xml = """<?xml version="1.0"?>
        <rss version="2.0"><channel>
        <item>
            <title>Acme Corp raises $50M Series B</title>
            <link>https://betakit.com/acme</link>
            <pubDate>Mon, 01 Apr 2026 12:00:00 GMT</pubDate>
            <description>Acme Corp announced Series B funding</description>
        </item>
        </channel></rss>"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = rss_xml
        with patch.object(scraper, "get", new_callable=AsyncMock, return_value=mock_resp):
            results = await scraper.scrape()
            assert isinstance(results, list)
            assert len(results) >= 1
            assert results[0].signal_type == "vc_series_b_plus"
            assert results[0].source_id == "pe_vc_deals"

    @pytest.mark.asyncio
    async def test_ircc_express_entry_csv(self):
        """IRCC Express Entry scraper parses draw data."""
        scraper = IRCCExpressEntryScraper()
        csv_data = (
            "Draw Number,Date,Draw Type,Number of Invitations,CRS Cut-Off\n"
            "300,2026-03-15,General,4000,500\n"
        )
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = csv_data
        with patch.object(scraper, "get", new_callable=AsyncMock, return_value=mock_resp):
            results = await scraper.scrape()
            assert isinstance(results, list)
            for r in results:
                assert r.signal_type == "immigration_express_entry_draw"


# ── Celery Task Registration Tests ───────────────────────────────────────────


class TestCeleryTaskRegistration:
    """All 14 new Celery tasks are registered."""

    def test_new_tasks_importable(self):
        """All new task functions can be imported."""
        from app.tasks.scraper_tasks import (
            run_courts_scrapers,
            run_energy_scrapers,
            run_environmental_scrapers,
            run_financial_stress_scrapers,
            run_grants_scrapers,
            run_hnwi_scrapers,
            run_immigration_scrapers,
            run_ip_scrapers,
            run_labour_scrapers,
            run_macro_scrapers,
            run_ownership_scrapers,
            run_pe_scrapers,
            run_restructuring_scrapers,
            run_startups_scrapers,
        )

        tasks = [
            run_hnwi_scrapers,
            run_immigration_scrapers,
            run_pe_scrapers,
            run_financial_stress_scrapers,
            run_restructuring_scrapers,
            run_grants_scrapers,
            run_courts_scrapers,
            run_energy_scrapers,
            run_macro_scrapers,
            run_ip_scrapers,
            run_ownership_scrapers,
            run_startups_scrapers,
            run_environmental_scrapers,
            run_labour_scrapers,
        ]
        assert len(tasks) == 14

    def test_beat_schedule_has_new_entries(self):
        """Beat schedule includes all 14 new scraper entries."""
        from app.tasks.celery_app import celery_app

        schedule = celery_app.conf.beat_schedule
        new_task_names = [
            "scrapers.run_hnwi",
            "scrapers.run_immigration",
            "scrapers.run_pe",
            "scrapers.run_financial_stress",
            "scrapers.run_restructuring",
            "scrapers.run_grants",
            "scrapers.run_courts",
            "scrapers.run_energy",
            "scrapers.run_macro",
            "scrapers.run_ip",
            "scrapers.run_ownership",
            "scrapers.run_startups",
            "scrapers.run_environmental",
            "scrapers.run_labour",
        ]
        scheduled_tasks = {v["task"] for v in schedule.values()}
        for task_name in new_task_names:
            assert task_name in scheduled_tasks, f"{task_name} missing from beat schedule"

    def test_task_routing_has_new_entries(self):
        """Task routing maps all 14 new tasks to scrapers queue."""
        from app.tasks.celery_app import celery_app

        routes = celery_app.conf.task_routes
        new_routes = [
            "scrapers.run_hnwi",
            "scrapers.run_immigration",
            "scrapers.run_pe",
            "scrapers.run_financial_stress",
            "scrapers.run_restructuring",
            "scrapers.run_grants",
            "scrapers.run_courts",
            "scrapers.run_energy",
            "scrapers.run_macro",
            "scrapers.run_ip",
            "scrapers.run_ownership",
            "scrapers.run_startups",
            "scrapers.run_environmental",
            "scrapers.run_labour",
        ]
        for route in new_routes:
            assert route in routes, f"{route} missing from task_routes"
            assert routes[route] == {"queue": "scrapers"}


# ── Bank of Canada Enhancement Tests ─────────────────────────────────────────


class TestBankOfCanadaEnhancement:
    """BOS/SLOS enhancement doesn't break existing functionality."""

    def test_existing_signal_types_preserved(self):
        scraper = BankOfCanadaScraper()
        assert "monetary_policy_rate_change" in scraper.signal_types
        assert "financial_system_alert" in scraper.signal_types

    def test_new_signal_type_added(self):
        scraper = BankOfCanadaScraper()
        assert "macro_bos_credit_tightening" in scraper.signal_types

    def test_category_unchanged(self):
        scraper = BankOfCanadaScraper()
        assert scraper.CATEGORY == "corporate"
        assert scraper.source_id == "corporate_bank_of_canada"
