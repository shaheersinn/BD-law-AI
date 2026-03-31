"""
tests/scrapers/test_class_action_scrapers.py — Phase CA-1 class action scraper tests.

Tests all 12 class action scrapers with mocked HTTP responses.
Validates ScraperResult fields, practice_area_hints, confidence_score, etc.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.scrapers.base import ScraperResult

# ── Realistic HTML fixtures ──────────────────────────────────────────────────

_COURT_TABLE_HTML = """
<html><body>
<table><tbody>
<tr>
  <td><a href="/case/cv-12345">Smith v. Acme Corp</a></td>
  <td>CV-12345-00</td>
  <td>Filed</td>
  <td>March 15, 2026</td>
</tr>
<tr>
  <td><a href="/case/cv-67890">Jones v. MegaBank Inc. — Securities Fraud</a></td>
  <td>CV-67890-00</td>
  <td>Certified</td>
  <td>February 20, 2026</td>
</tr>
<tr>
  <td><a href="/case/cv-11111">Doe v. DataCorp — Privacy Breach</a></td>
  <td>CV-11111-00</td>
  <td>Settlement Approved</td>
  <td>January 10, 2026</td>
</tr>
</tbody></table>
</body></html>
"""

_ARTICLE_LIST_HTML = """
<html><body>
<article>
  <h3><a href="/cases/acme-securities">Investigation: Acme Securities Class Action</a></h3>
  <time datetime="2026-03-10">March 10, 2026</time>
  <p>Investigating potential securities fraud by Acme Corp.</p>
</article>
<article>
  <h3><a href="/cases/bigco-product">BigCo Product Liability Class Action Filed</a></h3>
  <time datetime="2026-02-28">February 28, 2026</time>
  <p>Class action filed against BigCo for defective products.</p>
</article>
</body></html>
"""

_COURTLISTENER_JSON = {
    "results": [
        {
            "caseName": "In re Canadian Mining Corp Securities Litigation",
            "case_name": "In re Canadian Mining Corp Securities Litigation",
            "dateFiled": "2026-03-01",
            "date_filed": "2026-03-01",
            "snippet": "Class action against TSX-listed Canadian Mining Corp for securities fraud",
            "absolute_url": "/opinion/12345/",
            "court": "S.D.N.Y.",
            "docketNumber": "1:26-cv-01234",
            "docket_number": "1:26-cv-01234",
        },
        {
            "caseName": "Doe v. Random US Corp",
            "case_name": "Doe v. Random US Corp",
            "dateFiled": "2026-03-05",
            "date_filed": "2026-03-05",
            "snippet": "A purely domestic US matter with no foreign nexus whatsoever.",
            "absolute_url": "/opinion/67890/",
            "court": "N.D. Ill.",
            "docketNumber": "1:26-cv-05678",
            "docket_number": "1:26-cv-05678",
        },
    ]
}


# ── Valid PRACTICE_AREA_BITS keys ─────────────────────────────────────────────

VALID_PRACTICE_AREAS = {
    "ma_corporate",
    "litigation",
    "regulatory_compliance",
    "employment_labour",
    "insolvency_restructuring",
    "securities_capital_markets",
    "competition_antitrust",
    "privacy_cybersecurity",
    "environmental_indigenous_energy",
    "tax",
    "real_estate_construction",
    "banking_finance",
    "intellectual_property",
    "immigration_corporate",
    "infrastructure_project_finance",
    "wills_estates",
    "administrative_public_law",
    "arbitration",
    "class_actions",
    "construction_disputes",
    "defamation_media",
    "financial_regulatory",
    "franchise_distribution",
    "health_life_sciences",
    "insurance_reinsurance",
    "international_trade_customs",
    "mining_natural_resources",
    "municipal_land_use",
    "nfp_charity",
    "pension_benefits",
    "product_liability",
    "sports_entertainment",
    "technology_fintech_regulatory",
    "data_privacy_technology",
}


def _mock_response(text: str = "", status_code: int = 200) -> httpx.Response:
    """Create a mock httpx Response."""
    return httpx.Response(
        status_code=status_code,
        text=text,
        request=httpx.Request("GET", "https://example.com"),
    )


def _mock_json_response(data: dict, status_code: int = 200) -> httpx.Response:
    """Create a mock httpx Response with JSON."""
    import json

    return httpx.Response(
        status_code=status_code,
        text=json.dumps(data),
        headers={"content-type": "application/json"},
        request=httpx.Request("GET", "https://example.com"),
    )


def _validate_results(results: list[ScraperResult], expected_source_id: str) -> None:
    """Common validation for all scraper results."""
    assert isinstance(results, list)
    for r in results:
        assert isinstance(r, ScraperResult)
        assert r.source_id == expected_source_id
        assert r.signal_type, "signal_type must not be empty"
        assert 0.0 <= r.confidence_score <= 1.0
        assert "class_actions" in r.practice_area_hints
        for hint in r.practice_area_hints:
            assert hint in VALID_PRACTICE_AREAS, f"Invalid practice area: {hint}"


# ── Ontario Class Proceedings Tests ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_ontario_scraper_parses_table():
    from app.scrapers.class_actions.ontario_class_proceedings import (
        OntarioClassProceedingsScraper,
    )

    scraper = OntarioClassProceedingsScraper()
    with patch.object(scraper, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = _mock_response(_COURT_TABLE_HTML)
        results = await scraper.scrape()

    assert len(results) == 3
    _validate_results(results, "class_action_ontario")

    # Check first result
    assert results[0].raw_company_name == "Acme Corp"
    assert results[0].signal_value["jurisdiction"] == "ON"
    assert results[0].signal_value["court"] == "Ontario Superior Court of Justice"

    # Check certified case
    assert results[1].signal_type == "class_action_certified"
    assert "securities_capital_markets" in results[1].practice_area_hints

    # Check settled case
    assert results[2].signal_type == "class_action_settled"


@pytest.mark.asyncio
async def test_ontario_scraper_handles_failure():
    from app.scrapers.class_actions.ontario_class_proceedings import (
        OntarioClassProceedingsScraper,
    )

    scraper = OntarioClassProceedingsScraper()
    with patch.object(scraper, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = _mock_response("", status_code=503)
        results = await scraper.scrape()

    assert results == []


@pytest.mark.asyncio
async def test_ontario_scraper_contract():
    from app.scrapers.class_actions.ontario_class_proceedings import (
        OntarioClassProceedingsScraper,
    )

    scraper = OntarioClassProceedingsScraper()
    assert scraper.source_id == "class_action_ontario"
    assert scraper.source_name
    assert scraper.signal_types
    assert scraper.rate_limit_rps == 0.2
    assert scraper.concurrency == 1
    assert scraper.CATEGORY == "class_actions"
    assert hasattr(scraper, "scrape")
    assert hasattr(scraper, "health_check")


# ── BC Class Proceedings Tests ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_bc_scraper_parses_table():
    from app.scrapers.class_actions.bc_class_proceedings import (
        BCClassProceedingsScraper,
    )

    scraper = BCClassProceedingsScraper()
    with patch.object(scraper, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = _mock_response(_COURT_TABLE_HTML)
        results = await scraper.scrape()

    assert len(results) >= 1
    _validate_results(results, "class_action_bc")
    assert results[0].signal_value["jurisdiction"] == "BC"


@pytest.mark.asyncio
async def test_bc_scraper_contract():
    from app.scrapers.class_actions.bc_class_proceedings import (
        BCClassProceedingsScraper,
    )

    scraper = BCClassProceedingsScraper()
    assert scraper.source_id == "class_action_bc"
    assert scraper.CATEGORY == "class_actions"
    assert scraper.rate_limit_rps == 0.2


# ── Quebec Class Proceedings Tests ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_quebec_scraper_parses_table():
    from app.scrapers.class_actions.quebec_class_proceedings import (
        QuebecClassProceedingsScraper,
    )

    scraper = QuebecClassProceedingsScraper()
    with patch.object(scraper, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = _mock_response(_COURT_TABLE_HTML)
        results = await scraper.scrape()

    assert len(results) >= 1
    _validate_results(results, "class_action_quebec")
    assert results[0].signal_value["jurisdiction"] == "QC"


# ── Federal Court Tests ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_federal_scraper_parses_table():
    from app.scrapers.class_actions.federal_court_class_proceedings import (
        FederalCourtClassProceedingsScraper,
    )

    scraper = FederalCourtClassProceedingsScraper()
    with patch.object(scraper, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = _mock_response(_COURT_TABLE_HTML)
        results = await scraper.scrape()

    assert len(results) >= 1
    _validate_results(results, "class_action_federal")
    assert results[0].signal_value["jurisdiction"] == "FED"


# ── Alberta Tests ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_alberta_scraper_parses_table():
    from app.scrapers.class_actions.alberta_class_proceedings import (
        AlbertaClassProceedingsScraper,
    )

    scraper = AlbertaClassProceedingsScraper()
    with patch.object(scraper, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = _mock_response(_COURT_TABLE_HTML)
        results = await scraper.scrape()

    assert len(results) >= 1
    _validate_results(results, "class_action_alberta")
    assert results[0].signal_value["jurisdiction"] == "AB"


# ── ClassAction.org Tests ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_classaction_org_parses_articles():
    from app.scrapers.class_actions.classaction_ca import ClassActionOrgScraper

    scraper = ClassActionOrgScraper()
    with patch.object(scraper, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = _mock_response(_ARTICLE_LIST_HTML)
        results = await scraper.scrape()

    assert len(results) == 2
    _validate_results(results, "class_action_org")
    assert results[0].signal_type == "class_action_investigation"
    assert results[1].signal_type == "class_action_news"


@pytest.mark.asyncio
async def test_classaction_org_infers_practice_areas():
    from app.scrapers.class_actions.classaction_ca import ClassActionOrgScraper

    scraper = ClassActionOrgScraper()
    with patch.object(scraper, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = _mock_response(_ARTICLE_LIST_HTML)
        results = await scraper.scrape()

    # First article mentions "securities"
    assert "securities_capital_markets" in results[0].practice_area_hints
    # Second article mentions "product"
    assert "product_liability" in results[1].practice_area_hints


# ── Siskinds Tests ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_siskinds_scraper_parses_articles():
    from app.scrapers.class_actions.siskinds_class_actions import (
        SiskindsClassActionsScraper,
    )

    scraper = SiskindsClassActionsScraper()
    with patch.object(scraper, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = _mock_response(_ARTICLE_LIST_HTML)
        results = await scraper.scrape()

    assert len(results) >= 1
    _validate_results(results, "class_action_siskinds")
    assert results[0].signal_value["firm"] == "Siskinds LLP"


# ── Branch MacMaster Tests ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_branch_macmaster_scraper():
    from app.scrapers.class_actions.branch_macmaster_class_actions import (
        BranchMacMasterClassActionsScraper,
    )

    scraper = BranchMacMasterClassActionsScraper()
    with patch.object(scraper, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = _mock_response(_ARTICLE_LIST_HTML)
        results = await scraper.scrape()

    assert len(results) >= 1
    _validate_results(results, "class_action_branch_macmaster")
    assert results[0].signal_value["firm"] == "Branch MacMaster LLP"


# ── Merchant Law Tests ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_merchant_law_scraper():
    from app.scrapers.class_actions.merchant_law_class_actions import (
        MerchantLawClassActionsScraper,
    )

    scraper = MerchantLawClassActionsScraper()
    with patch.object(scraper, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = _mock_response(_ARTICLE_LIST_HTML)
        results = await scraper.scrape()

    assert len(results) >= 1
    _validate_results(results, "class_action_merchant_law")


# ── Koskie Minsky Tests ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_koskie_minsky_scraper():
    from app.scrapers.class_actions.koskie_minsky_class_actions import (
        KoskieMinskyClassActionsScraper,
    )

    scraper = KoskieMinskyClassActionsScraper()
    with patch.object(scraper, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = _mock_response(_ARTICLE_LIST_HTML)
        results = await scraper.scrape()

    assert len(results) >= 1
    _validate_results(results, "class_action_koskie_minsky")


# ── CBA Tests ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cba_scraper_parses_articles():
    from app.scrapers.class_actions.cba_class_actions import CBAClassActionsScraper

    scraper = CBAClassActionsScraper()
    with patch.object(scraper, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = _mock_response(_ARTICLE_LIST_HTML)
        results = await scraper.scrape()

    assert len(results) >= 1
    _validate_results(results, "class_action_cba")
    assert results[0].signal_type == "class_action_analysis"
    assert results[0].confidence_score == 0.60


# ── PACER / CourtListener Tests ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_pacer_scraper_filters_canadian():
    from app.scrapers.class_actions.pacer_class_actions import (
        PACERClassActionsScraper,
    )

    scraper = PACERClassActionsScraper()
    with patch.object(scraper, "get_json", new_callable=AsyncMock) as mock_json:
        mock_json.return_value = _COURTLISTENER_JSON
        results = await scraper.scrape()

    # Only the Canadian-connected case should be returned
    assert len(results) == 1
    _validate_results(results, "class_action_pacer")
    assert results[0].signal_value["jurisdiction"] == "US"
    assert "securities_capital_markets" in results[0].practice_area_hints
    assert "Canadian Mining Corp" in results[0].signal_value["case_name"]


@pytest.mark.asyncio
async def test_pacer_scraper_empty_api():
    from app.scrapers.class_actions.pacer_class_actions import (
        PACERClassActionsScraper,
    )

    scraper = PACERClassActionsScraper()
    with patch.object(scraper, "get_json", new_callable=AsyncMock) as mock_json:
        mock_json.return_value = None
        results = await scraper.scrape()

    assert results == []


# ── Contract Tests for All 12 Scrapers ────────────────────────────────────────

_ALL_CLASS_ACTION_SCRAPERS = [
    ("app.scrapers.class_actions.ontario_class_proceedings", "OntarioClassProceedingsScraper"),
    ("app.scrapers.class_actions.bc_class_proceedings", "BCClassProceedingsScraper"),
    ("app.scrapers.class_actions.quebec_class_proceedings", "QuebecClassProceedingsScraper"),
    ("app.scrapers.class_actions.federal_court_class_proceedings", "FederalCourtClassProceedingsScraper"),
    ("app.scrapers.class_actions.alberta_class_proceedings", "AlbertaClassProceedingsScraper"),
    ("app.scrapers.class_actions.classaction_ca", "ClassActionOrgScraper"),
    ("app.scrapers.class_actions.siskinds_class_actions", "SiskindsClassActionsScraper"),
    ("app.scrapers.class_actions.branch_macmaster_class_actions", "BranchMacMasterClassActionsScraper"),
    ("app.scrapers.class_actions.merchant_law_class_actions", "MerchantLawClassActionsScraper"),
    ("app.scrapers.class_actions.koskie_minsky_class_actions", "KoskieMinskyClassActionsScraper"),
    ("app.scrapers.class_actions.cba_class_actions", "CBAClassActionsScraper"),
    ("app.scrapers.class_actions.pacer_class_actions", "PACERClassActionsScraper"),
]


@pytest.mark.parametrize("module_path,class_name", _ALL_CLASS_ACTION_SCRAPERS)
def test_scraper_contract(module_path: str, class_name: str):
    """Every class action scraper must satisfy the BaseScraper contract."""
    import importlib

    mod = importlib.import_module(module_path)
    cls = getattr(mod, class_name)
    scraper = cls()

    assert scraper.source_id, f"{class_name}: Missing source_id"
    assert scraper.source_id.startswith("class_action_"), f"{class_name}: source_id must start with 'class_action_'"
    assert scraper.source_name, f"{class_name}: Missing source_name"
    assert scraper.signal_types, f"{class_name}: Missing signal_types"
    assert scraper.CATEGORY == "class_actions", f"{class_name}: CATEGORY must be 'class_actions'"
    assert scraper.rate_limit_rps > 0, f"{class_name}: rate_limit_rps must be > 0"
    assert scraper.concurrency >= 1, f"{class_name}: concurrency must be >= 1"
    assert hasattr(scraper, "scrape"), f"{class_name}: Missing scrape()"
    assert hasattr(scraper, "health_check"), f"{class_name}: Missing health_check()"


@pytest.mark.parametrize("module_path,class_name", _ALL_CLASS_ACTION_SCRAPERS)
@pytest.mark.asyncio
async def test_scraper_returns_empty_on_500(module_path: str, class_name: str):
    """All scrapers must return [] on HTTP errors, not raise."""
    import importlib

    mod = importlib.import_module(module_path)
    cls = getattr(mod, class_name)
    scraper = cls()

    with patch.object(scraper, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = _mock_response("Server Error", status_code=500)
        # Also mock get_json for PACER
        if hasattr(scraper, "get_json"):
            with patch.object(scraper, "get_json", new_callable=AsyncMock) as mock_json:
                mock_json.return_value = None
                results = await scraper.scrape()
        else:
            results = await scraper.scrape()

    assert isinstance(results, list)


# ── Registry Integration Tests ────────────────────────────────────────────────


def test_all_class_action_scrapers_registered():
    """All 12 class action scrapers must appear in the registry."""
    from app.scrapers.registry import ScraperRegistry

    all_ids = ScraperRegistry.all_ids()
    expected = [
        "class_action_ontario",
        "class_action_bc",
        "class_action_quebec",
        "class_action_federal",
        "class_action_alberta",
        "class_action_org",
        "class_action_siskinds",
        "class_action_branch_macmaster",
        "class_action_merchant_law",
        "class_action_koskie_minsky",
        "class_action_cba",
        "class_action_pacer",
    ]
    for sid in expected:
        assert sid in all_ids, f"Scraper {sid} not registered"


def test_class_action_category_count():
    """There should be exactly 12 class action scrapers by category."""
    from app.scrapers.registry import ScraperRegistry

    scrapers = ScraperRegistry.by_category("class_actions")
    assert len(scrapers) == 12


# ── Migration File Test ──────────────────────────────────────────────────────


def test_migration_file_exists():
    """The Phase CA-1 migration file must exist and contain upgrade/downgrade."""
    import ast
    import os

    path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "alembic",
        "versions",
        "0009_class_action_tables.py",
    )
    assert os.path.exists(path), f"Migration file not found: {path}"

    with open(path) as f:
        source = f.read()

    # Valid Python syntax
    tree = ast.parse(source)
    func_names = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
    assert "upgrade" in func_names, "Migration missing upgrade()"
    assert "downgrade" in func_names, "Migration missing downgrade()"
    assert "class_action_cases" in source, "Migration missing class_action_cases table"


# ── Celery Task Registration Test ────────────────────────────────────────────


def test_celery_task_registered():
    """The class action Celery task must be registered."""
    try:
        from app.tasks.celery_app import celery_app
    except ImportError:
        pytest.skip("celery not installed")

    # Force task discovery
    celery_app.loader.import_default_modules()
    task_names = list(celery_app.tasks.keys())

    assert "scrapers.run_class_actions" in task_names, (
        f"scrapers.run_class_actions not in tasks: {[t for t in task_names if 'class' in t.lower()]}"
    )


# ── Status Inference Tests ────────────────────────────────────────────────────


def test_ontario_status_inference():
    from app.scrapers.class_actions.ontario_class_proceedings import (
        OntarioClassProceedingsScraper,
    )

    assert OntarioClassProceedingsScraper._infer_status("Settlement Approved") == "settled"
    assert OntarioClassProceedingsScraper._infer_status("Certification granted") == "certified"
    assert OntarioClassProceedingsScraper._infer_status("Case dismissed") == "dismissed"
    assert OntarioClassProceedingsScraper._infer_status("Appeal filed") == "appealed"
    assert OntarioClassProceedingsScraper._infer_status("New case") == "filed"


def test_party_extraction():
    from app.scrapers.class_actions.ontario_class_proceedings import (
        OntarioClassProceedingsScraper,
    )

    assert OntarioClassProceedingsScraper._extract_parties("Smith v. Acme Corp") == "Acme Corp"
    assert OntarioClassProceedingsScraper._extract_parties("Jones vs. MegaBank Inc.") == "MegaBank Inc."
    assert OntarioClassProceedingsScraper._extract_parties("No parties here") is None


def test_practice_area_inference():
    from app.scrapers.class_actions.ontario_class_proceedings import (
        OntarioClassProceedingsScraper,
    )

    areas = OntarioClassProceedingsScraper._infer_practice_areas("Securities fraud class action")
    assert "class_actions" in areas
    assert "securities_capital_markets" in areas

    areas = OntarioClassProceedingsScraper._infer_practice_areas("Employment wage theft")
    assert "employment_labour" in areas


def test_pacer_canadian_filter():
    from app.scrapers.class_actions.pacer_class_actions import (
        PACERClassActionsScraper,
    )

    assert PACERClassActionsScraper._has_canadian_connection("case involving toronto company")
    assert PACERClassActionsScraper._has_canadian_connection("tsx listed entity")
    assert not PACERClassActionsScraper._has_canadian_connection("purely domestic us matter")
