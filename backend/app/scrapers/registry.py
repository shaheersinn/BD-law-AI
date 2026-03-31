"""
app/scrapers/registry.py — Scraper registry.

Two registration mechanisms:
  1. @register decorator — used by modern scrapers (legal, geo, lawblog, social)
  2. _load_registry() — explicit imports for scrapers that don't use @register

ScraperRegistry is a static class providing the public API used by tasks and tests.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.scrapers.base import BaseScraper

log = logging.getLogger(__name__)

# ── Registry storage ───────────────────────────────────────────────────────────
_REGISTRY: dict[str, type[BaseScraper]] = {}
_REGISTRY_LOADED = False


# ── @register decorator ───────────────────────────────────────────────────────
def register(cls: type[BaseScraper]) -> type[BaseScraper]:
    """
    Class decorator that adds a scraper to the global registry.

    Usage:
        @register
        class MyCustomScraper(BaseScraper):
            source_id = "custom_source"
            ...
    """
    if not cls.source_id:
        log.warning("Scraper %s has no source_id — skipping registration", cls.__name__)
        return cls
    if cls.source_id in _REGISTRY:
        log.debug("Scraper %s already registered as %s", cls.__name__, cls.source_id)
    else:
        _REGISTRY[cls.source_id] = cls
    return cls


# ── Registry loader ───────────────────────────────────────────────────────────
def _load_registry() -> None:
    """
    Import all scraper modules to trigger @register decorators.
    Also handles old-style scrapers that don't use @register.
    """
    global _REGISTRY_LOADED
    if _REGISTRY_LOADED:
        return

    # ── Modern scrapers (use @register) ───────────────────────────────────────
    # Just importing the modules triggers registration.
    _safe_import("app.scrapers.legal.canlii")
    _safe_import("app.scrapers.legal.scc")
    _safe_import("app.scrapers.legal.competition_tribunal")
    _safe_import("app.scrapers.legal.refugee_law_lab")
    _safe_import("app.scrapers.legal.federal_court")
    _safe_import("app.scrapers.legal.tribunals_ontario")
    _safe_import("app.scrapers.legal.osb_insolvency")
    _safe_import("app.scrapers.legal.scac")
    _safe_import("app.scrapers.legal.osb")

    _safe_import("app.scrapers.geo.geo_scrapers")
    _safe_import("app.scrapers.geo.google_trends")
    _safe_import("app.scrapers.geo.statscan")
    _safe_import("app.scrapers.geo.opensky")
    _safe_import("app.scrapers.geo.pytrends")
    _safe_import("app.scrapers.geo.stats_canada")
    _safe_import("app.scrapers.geo.lobbyist_registry")
    _safe_import("app.scrapers.geo.municipal_permits")
    _safe_import("app.scrapers.geo.cipo_patents")
    _safe_import("app.scrapers.geo.cbsa_trade")
    _safe_import("app.scrapers.geo.dark_web")
    _safe_import("app.scrapers.geo.cra_liens")
    _safe_import("app.scrapers.geo.labour_relations")
    _safe_import("app.scrapers.geo.wsib")
    _safe_import("app.scrapers.geo.dbrs")
    _safe_import("app.scrapers.geo.procurement")
    _safe_import("app.scrapers.geo.commodity_prices")

    _safe_import("app.scrapers.law_blogs.firm_blogs")
    _safe_import("app.scrapers.law_blogs.trend_detector")

    _safe_import("app.scrapers.social.reddit")
    _safe_import("app.scrapers.social.linkedin_social")
    _safe_import("app.scrapers.social.stockhouse")
    _safe_import("app.scrapers.social.twitter")
    _safe_import("app.scrapers.social.sedar_forums")
    _safe_import("app.scrapers.social.breach_monitor")

    # ── Old-style scrapers (use NAME/CATEGORY attributes, no @register) ────────
    # These are registered explicitly since they predate the @register pattern.
    _register_old_style(
        [
            "app.scrapers.filings.sedar",
            "app.scrapers.filings.edgar",
            "app.scrapers.filings.sedi",
            "app.scrapers.filings.corporations_canada",
            "app.scrapers.filings.osfi_regulated",
            "app.scrapers.filings.bank_of_canada",
            "app.scrapers.filings.canada_gazette",
            "app.scrapers.filings.ciro",
            "app.scrapers.filings.iaac",
            "app.scrapers.filings.tmx_listings",
        ]
    )
    _register_old_style(
        [
            "app.scrapers.jobs.indeed",
            "app.scrapers.jobs.linkedin_jobs",
            "app.scrapers.jobs.job_bank",
            "app.scrapers.jobs.glassdoor_jobs",
            "app.scrapers.jobs.company_careers",
        ]
    )
    _register_old_style(
        [
            "app.scrapers.market.tmx_datalinx",
            "app.scrapers.market.yahoo_finance",
            "app.scrapers.market.alpha_vantage",
            "app.scrapers.market.sedar_bar",
        ]
    )
    _register_old_style(
        [
            "app.scrapers.news.google_news",
            "app.scrapers.news.reuters",
            "app.scrapers.news.globe_mail",
            "app.scrapers.news.financial_post",
            "app.scrapers.news.cbc_business",
            "app.scrapers.news.bnn_bloomberg",
            "app.scrapers.news.seeking_alpha",
        ]
    )
    _register_old_style(
        [
            "app.scrapers.regulatory.osc",
            "app.scrapers.regulatory.osfi_enforcement",
            "app.scrapers.regulatory.competition_bureau",
            "app.scrapers.regulatory.fintrac",
            "app.scrapers.regulatory.opc",
            "app.scrapers.regulatory.eccc",
            "app.scrapers.regulatory.health_canada",
            "app.scrapers.regulatory.crtc",
            "app.scrapers.regulatory.fsra",
            "app.scrapers.regulatory.amf_quebec",
            "app.scrapers.regulatory.bcsc",
            "app.scrapers.regulatory.asc",
            "app.scrapers.regulatory.sec_aaer",
            "app.scrapers.regulatory.us_doj",
            "app.scrapers.regulatory.amf",
            "app.scrapers.regulatory.doj",
        ]
    )

    _REGISTRY_LOADED = True
    log.info("Scraper registry loaded: %d scrapers", len(_REGISTRY))


def _safe_import(module_path: str) -> None:
    """Import a module, logging (not raising) on failure."""
    try:
        import importlib

        importlib.import_module(module_path)
    except Exception as exc:
        log.warning("Failed to import scraper module %s: %s", module_path, exc)


def _register_old_style(module_paths: list[str]) -> None:
    """
    Register old-style scrapers that define NAME/source_id but don't use @register.
    Finds the first BaseScraper subclass in each module and registers it.
    """
    import importlib
    import inspect

    from app.scrapers.base import BaseScraper  # noqa: PLC0415 (local import to avoid circular)

    for module_path in module_paths:
        try:
            mod = importlib.import_module(module_path)
        except Exception as exc:
            log.warning("Failed to import old-style scraper %s: %s", module_path, exc)
            continue

        for _name, obj in inspect.getmembers(mod, inspect.isclass):
            if (
                obj is not BaseScraper
                and issubclass(obj, BaseScraper)
                and obj.__module__ == module_path
            ):
                # Support both source_id and NAME (old scrapers)
                sid = getattr(obj, "source_id", None) or getattr(obj, "NAME", None)
                if sid and sid not in _REGISTRY:
                    # Ensure source_id is set (old scrapers use NAME)
                    if not getattr(obj, "source_id", None):
                        obj.source_id = sid
                    _REGISTRY[sid] = obj
                    log.debug("Registered old-style scraper: %s → %s", obj.__name__, sid)


# ── Public API ────────────────────────────────────────────────────────────────


def get_registry() -> dict[str, type[BaseScraper]]:
    _load_registry()
    return _REGISTRY


def get_scraper(name: str) -> type[BaseScraper] | None:
    return get_registry().get(name)


def get_scrapers_by_category(category: str) -> list[type[BaseScraper]]:
    return [c for c in get_registry().values() if getattr(c, "CATEGORY", "") == category]


def list_scraper_names() -> list[str]:
    return sorted(get_registry().keys())


# ── ScraperRegistry class (used by tasks and tests) ───────────────────────────


class ScraperRegistry:
    """
    Static class providing a typed API over the global _REGISTRY dict.
    Used by:
      - app/tasks/scraper_tasks.py  (by_category, all_scrapers, get)
      - tests/scrapers/test_phase1_scrapers.py  (count, all_scrapers, get, by_category, all_ids)
    """

    @staticmethod
    def count() -> int:
        """Total number of registered scrapers."""
        return len(get_registry())

    @staticmethod
    def all_scrapers() -> list[BaseScraper]:
        """Return one instantiated instance of every registered scraper."""
        instances: list[BaseScraper] = []
        for cls in get_registry().values():
            try:
                instances.append(cls())
            except Exception as exc:
                log.warning("Could not instantiate scraper %s: %s", cls.__name__, exc)
        return instances

    @staticmethod
    def get(source_id: str) -> BaseScraper:
        """Instantiate and return a single scraper by source_id. Raises KeyError if missing."""
        reg = get_registry()
        if source_id not in reg:
            raise KeyError(f"Scraper not found: {source_id!r}")
        return reg[source_id]()

    @staticmethod
    def by_category(category: str) -> list[BaseScraper]:
        """Return instantiated scrapers in a given category."""
        instances = []
        for cls in get_registry().values():
            if getattr(cls, "CATEGORY", "") == category:
                try:
                    instances.append(cls())
                except Exception as exc:
                    log.warning("Could not instantiate %s: %s", cls.__name__, exc)
        return instances

    @staticmethod
    def all_ids() -> list[str]:
        """Return all registered source_ids, sorted alphabetically."""
        return sorted(get_registry().keys())
