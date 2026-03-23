"""
app/scrapers/registry.py — Scraper registry.
Maps scraper names to classes. Used by Celery tasks.
"""
from __future__ import annotations
import logging
from typing import TYPE_CHECKING, Optional, Type

if TYPE_CHECKING:
    from app.scrapers.base import BaseScraper

log = logging.getLogger(__name__)
_REGISTRY: dict[str, Type["BaseScraper"]] = {}
_REGISTRY_LOADED = False


def _load_registry() -> None:
    global _REGISTRY_LOADED
    if _REGISTRY_LOADED:
        return
    from app.scrapers.filings.sedar import SedarScraper
    from app.scrapers.filings.edgar import EdgarScraper
    from app.scrapers.filings.sedi import SediScraper
    from app.scrapers.filings.corporations_canada import CorporationsCanadaScraper
    from app.scrapers.filings.osfi_regulated import OsfiRegulatedEntitiesScraper
    from app.scrapers.filings.bank_of_canada import BankOfCanadaScraper
    from app.scrapers.filings.canada_gazette import CanadaGazetteScraper
    from app.scrapers.filings.ciro import CiroScraper
    from app.scrapers.filings.iaac import IaacScraper
    from app.scrapers.filings.tmx_listings import TmxListingsScraper
    from app.scrapers.legal.canlii import CanLIIScraper
    from app.scrapers.legal.scc import SccScraper
    from app.scrapers.legal.competition_tribunal import CompetitionTribunalScraper
    from app.scrapers.legal.refugee_law_lab import RefugeeLawLabScraper
    from app.scrapers.legal.federal_court import FederalCourtScraper
    from app.scrapers.legal.tribunals_ontario import TribunalsOntarioScraper
    from app.scrapers.legal.osb_insolvency import OsbInsolvencyScraper
    from app.scrapers.legal.stanford_scac import StanfordScacScraper
    from app.scrapers.regulatory.osc import OscScraper
    from app.scrapers.regulatory.osfi_enforcement import OsfiEnforcementScraper
    from app.scrapers.regulatory.competition_bureau import CompetitionBureauScraper
    from app.scrapers.regulatory.fintrac import FintracScraper
    from app.scrapers.regulatory.opc import OpcScraper
    from app.scrapers.regulatory.eccc import EcccScraper
    from app.scrapers.regulatory.health_canada import HealthCanadaScraper
    from app.scrapers.regulatory.crtc import CrtcScraper
    from app.scrapers.regulatory.fsra import FsraScraper
    from app.scrapers.regulatory.amf_quebec import AmfQuebecScraper
    from app.scrapers.regulatory.bcsc import BcscScraper
    from app.scrapers.regulatory.asc import AscScraper
    from app.scrapers.regulatory.sec_aaer import SecAaerScraper
    from app.scrapers.regulatory.us_doj import UsDojScraper
    from app.scrapers.jobs.indeed import IndeedScraper
    from app.scrapers.jobs.linkedin_jobs import LinkedInJobsScraper
    from app.scrapers.jobs.job_bank import JobBankScraper
    from app.scrapers.jobs.glassdoor_jobs import GlassdoorJobsScraper
    from app.scrapers.jobs.company_careers import CompanyCareersScraper
    from app.scrapers.market.tmx_datalinx import TmxDatalinxScraper
    from app.scrapers.market.yahoo_finance import YahooFinanceScraper
    from app.scrapers.market.alpha_vantage import AlphaVantageScraper
    from app.scrapers.market.sedar_bar import SedarBarScraper
    from app.scrapers.news.google_news import GoogleNewsScraper
    from app.scrapers.news.reuters import ReutersScraper
    from app.scrapers.news.globe_mail import GlobeMailScraper
    from app.scrapers.news.financial_post import FinancialPostScraper
    from app.scrapers.news.cbc_business import CbcBusinessScraper
    from app.scrapers.news.bnn_bloomberg import BnnBloombergScraper
    from app.scrapers.news.seeking_alpha import SeekingAlphaScraper
    from app.scrapers.social.reddit import RedditScraper
    from app.scrapers.social.linkedin_social import LinkedInSocialScraper
    from app.scrapers.social.stockhouse import StockhouseScraper
    from app.scrapers.social.twitter import TwitterScraper
    from app.scrapers.social.sedar_forums import SedarForumsScraper
    from app.scrapers.geo.opensky import OpenSkyScraper
    from app.scrapers.geo.pytrends import PyTrendsScraper
    from app.scrapers.geo.stats_canada import StatsCanadaScraper
    from app.scrapers.geo.lobbyist_registry import LobbyistRegistryScraper
    from app.scrapers.geo.municipal_permits import MunicipalPermitsScraper
    from app.scrapers.geo.cipo_patents import CipoPatentsScraper
    from app.scrapers.geo.cbsa_trade import CbsaTradeScraper
    from app.scrapers.geo.dark_web import DarkWebBreachScraper
    from app.scrapers.geo.cra_liens import CraTaxLienScraper
    from app.scrapers.geo.labour_relations import LabourRelationsScraper
    from app.scrapers.geo.wsib import WsibScraper
    from app.scrapers.geo.dbrs import DbrsScraper
    from app.scrapers.geo.procurement import ProcurementScraper
    from app.scrapers.geo.commodity_prices import CommodityPricesScraper
    from app.scrapers.lawfirms.tier1 import (
        McCarthyTetraultScraper, OslerScraper, TorysScraper, StikmanScraper,
        BennettJonesScraper, BlakesScraper, FaskenScraper, GoodmansScraper,
        GowlingScraper, NortonRoseScraper, CasselsScraper, DentonsScraper,
        DlaPiperScraper, BlgScraper, McMillanScraper,
    )
    from app.scrapers.lawfirms.tier2 import (
        StikestoneScraper, ConwayBaristowScraper, AdairBarrisScraper,
        BergScraper, CaleyWraysScraper, CazinScraper, DunnMorrisScraper,
        ElkindMechingerScraper, GardinerRobertsScraper, HeenanBlaikeScraper,
        PalliareScraper, TorkinManeScraper,
    )

    all_scrapers = [
        SedarScraper, EdgarScraper, SediScraper, CorporationsCanadaScraper,
        OsfiRegulatedEntitiesScraper, BankOfCanadaScraper, CanadaGazetteScraper,
        CiroScraper, IaacScraper, TmxListingsScraper,
        CanLIIScraper, SccScraper, CompetitionTribunalScraper, RefugeeLawLabScraper,
        FederalCourtScraper, TribunalsOntarioScraper, OsbInsolvencyScraper, StanfordScacScraper,
        OscScraper, OsfiEnforcementScraper, CompetitionBureauScraper, FintracScraper,
        OpcScraper, EcccScraper, HealthCanadaScraper, CrtcScraper, FsraScraper,
        AmfQuebecScraper, BcscScraper, AscScraper, SecAaerScraper, UsDojScraper,
        IndeedScraper, LinkedInJobsScraper, JobBankScraper, GlassdoorJobsScraper,
        CompanyCareersScraper,
        TmxDatalinxScraper, YahooFinanceScraper, AlphaVantageScraper, SedarBarScraper,
        GoogleNewsScraper, ReutersScraper, GlobeMailScraper, FinancialPostScraper,
        CbcBusinessScraper, BnnBloombergScraper, SeekingAlphaScraper,
        RedditScraper, LinkedInSocialScraper, StockhouseScraper, TwitterScraper,
        SedarForumsScraper,
        OpenSkyScraper, PyTrendsScraper, StatsCanadaScraper, LobbyistRegistryScraper,
        MunicipalPermitsScraper, CipoPatentsScraper, CbsaTradeScraper,
        DarkWebBreachScraper, CraTaxLienScraper, LabourRelationsScraper,
        WsibScraper, DbrsScraper, ProcurementScraper, CommodityPricesScraper,
        McCarthyTetraultScraper, OslerScraper, TorysScraper, StikmanScraper,
        BennettJonesScraper, BlakesScraper, FaskenScraper, GoodmansScraper,
        GowlingScraper, NortonRoseScraper, CasselsScraper, DentonsScraper,
        DlaPiperScraper, BlgScraper, McMillanScraper,
        StikestoneScraper, ConwayBaristowScraper, AdairBarrisScraper,
        BergScraper, CaleyWraysScraper, CazinScraper, DunnMorrisScraper,
        ElkindMechingerScraper, GardinerRobertsScraper, HeenanBlaikeScraper,
        PalliareScraper, TorkinManeScraper,
    ]

    for cls in all_scrapers:
        _REGISTRY[cls.NAME] = cls

    _REGISTRY_LOADED = True
    log.info("Scraper registry: %d scrapers loaded", len(_REGISTRY))


def get_registry() -> dict[str, Type["BaseScraper"]]:
    _load_registry()
    return _REGISTRY


def get_scraper(name: str) -> Optional[Type["BaseScraper"]]:
    return get_registry().get(name)


def get_scrapers_by_category(category: str) -> list[Type["BaseScraper"]]:
    return [c for c in get_registry().values() if c.CATEGORY == category]


def list_scraper_names() -> list[str]:
    return sorted(get_registry().keys())
