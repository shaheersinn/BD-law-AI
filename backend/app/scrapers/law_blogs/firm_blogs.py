"""
app/scrapers/law_blogs/firm_blogs.py — Law Firm Blog Intelligence.

Category 9: 27 Canadian law firm blogs (15 Bay Street Tier 1 + 12 Tier 2).

Why this category matters:
  - Law firm blogs surface legal/regulatory trends 2-6 weeks before mainstream media
  - When 3+ Bay Street firms publish on the same topic → consensus trend signal
  - Blog content trains our NLP models (practice area classification, keyword weights)
  - Blog activity reveals which practice areas are heating up

Architecture:
  - Single LawFirmBlogScraper base class with per-firm RSS configuration
  - No JS rendering needed (all have RSS feeds or static HTML)
  - Content → MongoDB (NLP training + trend analysis)
  - Signal metadata → PostgreSQL (blog_legal_trend, blog_practice_alert)

Rate limit: 0.016 rps = 1 request per 60 seconds per firm.
           Staggered over a 30-minute window via Celery beat.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET  # nosec B405
from dataclasses import dataclass
from typing import Any

import structlog
from bs4 import BeautifulSoup

from app.scrapers.base import BaseScraper, ScraperResult

log = structlog.get_logger(__name__)


@dataclass(frozen=True)
class FirmConfig:
    """Configuration for a single law firm blog."""

    firm_id: str
    firm_name: str
    tier: int  # 1 = Bay Street Tier 1, 2 = Tier 2 specialty
    rss_url: str
    practice_focus: list[str]  # Primary practice areas this firm covers
    base_url: str = ""


# ── 15 Bay Street Tier 1 Firms ─────────────────────────────────────────────────
_TIER1_FIRMS = [
    FirmConfig(
        "mccarthy",
        "McCarthy Tétrault",
        1,
        "https://www.mccarthy.ca/en/insights/rss",
        ["ma", "securities", "banking", "competition", "regulatory"],
        "https://www.mccarthy.ca",
    ),
    FirmConfig(
        "osler",
        "Osler Hoskin & Harcourt",
        1,
        "https://www.osler.com/en/resources/regulations/rss",
        ["securities", "regulatory", "competition", "employment", "ma"],
        "https://www.osler.com",
    ),
    FirmConfig(
        "torys",
        "Torys LLP",
        1,
        "https://www.torys.com/our-thinking/rss.xml",
        ["ma", "capital_markets", "private_equity", "competition"],
        "https://www.torys.com",
    ),
    FirmConfig(
        "stikeman",
        "Stikeman Elliott",
        1,
        "https://www.stikeman.com/en-ca/kh/rss",
        ["ma", "securities", "banking", "competition", "tax"],
        "https://www.stikeman.com",
    ),
    FirmConfig(
        "bennett_jones",
        "Bennett Jones LLP",
        1,
        "https://www.bennettjones.com/Publications/rss",
        ["energy", "mining", "ma", "regulatory", "arbitration"],
        "https://www.bennettjones.com",
    ),
    FirmConfig(
        "blakes",
        "Blake Cassels & Graydon",
        1,
        "https://www.blakes.com/en/insights/rss",
        ["ma", "capital_markets", "litigation", "competition", "regulatory"],
        "https://www.blakes.com",
    ),
    FirmConfig(
        "fasken",
        "Fasken Martineau DuMoulin",
        1,
        "https://www.fasken.com/en/knowledge/rss",
        ["employment", "ma", "mining", "regulatory", "litigation"],
        "https://www.fasken.com",
    ),
    FirmConfig(
        "goodmans",
        "Goodmans LLP",
        1,
        "https://www.goodmans.ca/news/rss",
        ["insolvency", "ma", "private_equity", "securities", "real_estate"],
        "https://www.goodmans.ca",
    ),
    FirmConfig(
        "gowling",
        "Gowling WLG",
        1,
        "https://gowlingwlg.com/en/insights-resources/rss",
        ["ip", "employment", "litigation", "regulatory", "technology"],
        "https://gowlingwlg.com",
    ),
    FirmConfig(
        "norton_rose",
        "Norton Rose Fulbright",
        1,
        "https://www.nortonrosefulbright.com/en/knowledge/publications/rss",
        ["energy", "financial_regulatory", "litigation", "ma", "insurance"],
        "https://www.nortonrosefulbright.com",
    ),
    FirmConfig(
        "cassels",
        "Cassels Brock & Blackwell",
        1,
        "https://cassels.com/insights/rss/",
        ["mining", "ma", "securities", "insolvency", "ip"],
        "https://cassels.com",
    ),
    FirmConfig(
        "dentons",
        "Dentons Canada",
        1,
        "https://www.dentons.com/en/insights/rss",
        ["regulatory", "employment", "real_estate", "tax", "ma"],
        "https://www.dentons.com",
    ),
    FirmConfig(
        "dla_piper",
        "DLA Piper (Canada)",
        1,
        "https://www.dlapiper.com/en/canada/insights/rss",
        ["technology", "ma", "litigation", "regulatory"],
        "https://www.dlapiper.com",
    ),
    FirmConfig(
        "blg",
        "Borden Ladner Gervais (BLG)",
        1,
        "https://www.blg.com/en/insights/rss",
        ["litigation", "regulatory", "employment", "real_estate", "tax"],
        "https://www.blg.com",
    ),
    FirmConfig(
        "mcmillan",
        "McMillan LLP",
        1,
        "https://mcmillan.ca/insights/rss/",
        ["insolvency", "ma", "financial_regulatory", "securities", "banking"],
        "https://mcmillan.ca",
    ),
]

# ── 12 Tier 2 Specialty Firms ──────────────────────────────────────────────────
_TIER2_FIRMS = [
    FirmConfig(
        "miller_thomson",
        "Miller Thomson LLP",
        2,
        "https://www.millerthomson.com/en/publications/rss/",
        ["litigation", "employment", "health_life_sciences", "insolvency"],
        "https://www.millerthomson.com",
    ),
    FirmConfig(
        "borden_elliot",
        "Borden Elliot",
        2,
        "https://borderelliott.com/feed/",
        ["insolvency", "litigation", "banking"],
        "https://borderelliott.com",
    ),
    FirmConfig(
        "davies",
        "Davies Ward Phillips & Vineberg",
        2,
        "https://www.dwpv.com/en/insights/rss",
        ["securities", "ma", "competition", "tax"],
        "https://www.dwpv.com",
    ),
    FirmConfig(
        "lenczner_slaght",
        "Lenczner Slaght",
        2,
        "https://litigate.com/feed/",
        ["litigation", "arbitration", "class_actions"],
        "https://litigate.com",
    ),
    FirmConfig(
        "thornton_grout",
        "Thornton Grout Finnigan",
        2,
        "https://www.tgf.ca/feed/",
        ["insolvency", "litigation", "banking"],
        "https://www.tgf.ca",
    ),
    FirmConfig(
        "lax_oleary",
        "Lax O'Leary LLP",
        2,
        "https://laxoleary.ca/feed/",
        ["litigation", "securities", "class_actions"],
        "https://laxoleary.ca",
    ),
    FirmConfig(
        "borden_elliot2",
        "Borden Elliot (Insolvency)",
        2,
        "https://borderelliott.com/feed/",
        ["insolvency"],
        "https://borderelliott.com",
    ),
    FirmConfig(
        "ogilvy",
        "Ogilvy Renault (merged to Norton Rose)",
        2,
        "https://www.nortonrosefulbright.com/en-ca/insights/rss",
        ["regulatory", "financial_regulatory"],
        "https://www.nortonrosefulbright.com",
    ),
    FirmConfig(
        "fraser_milner",
        "Dentons (formerly Fraser Milner Casgrain)",
        2,
        "https://www.dentons.com/en/ca/insights/rss",
        ["energy", "mining", "regulatory"],
        "https://www.dentons.com",
    ),
    FirmConfig(
        "langford",
        "Langford Law",
        2,
        "https://langfordlaw.ca/feed/",
        ["employment", "litigation"],
        "https://langfordlaw.ca",
    ),
    FirmConfig(
        "goldman_sloan",
        "Goldman Sloan Nash & Haber",
        2,
        "https://gsnh.com/feed/",
        ["competition", "regulatory"],
        "https://gsnh.com",
    ),
    FirmConfig(
        "lerners",
        "Lerners LLP",
        2,
        "https://www.lerners.ca/news/rss",
        ["litigation", "class_actions", "personal_injury"],
        "https://www.lerners.ca",
    ),
]

ALL_FIRMS = _TIER1_FIRMS + _TIER2_FIRMS

# ── Trend signal: 3+ firms publish on same topic in 7 days ────────────────────
_TREND_THRESHOLD = 3  # Minimum firm count to generate consensus signal


def _build_source_id(firm: FirmConfig) -> str:
    return f"lawblog_{firm.firm_id}"


class LawFirmBlogScraper(BaseScraper):
    """
    Base scraper for a single law firm blog.
    Instantiated per-firm via the factory function below.
    """

    rate_limit_rps = 0.016  # 1 req/60s per firm
    concurrency = 1
    retry_attempts = 2
    timeout_seconds = 20.0
    ttl_seconds = 3600

    def __init__(self, firm: FirmConfig) -> None:
        self.source_id = _build_source_id(firm)
        self.source_name = f"{firm.firm_name} Blog"
        self.signal_types = ["blog_legal_trend", "blog_practice_alert"]
        self._firm = firm
        super().__init__()

    async def scrape(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []
        try:
            response = await self.get(self._firm.rss_url)
            if response.status_code != 200:
                # Many firm blogs return 404 for RSS — try HTML fallback
                results.extend(await self._scrape_html_fallback())
                return results

            content_type = response.headers.get("content-type", "")
            if "xml" in content_type or response.text.strip().startswith("<"):
                results.extend(self._parse_rss(response.text))
            else:
                results.extend(self._parse_html(response.text))

        except Exception as exc:
            log.error("lawblog_scrape_error", firm=self._firm.firm_id, error=str(exc))

        return results

    def _parse_rss(self, xml_text: str) -> list[ScraperResult]:
        results = []
        try:
            root = ET.fromstring(xml_text)  # nosec B314 — trusted government/news RSS source
            for item in root.iter("item"):
                title = (item.findtext("title") or "").strip()
                link = (item.findtext("link") or "").strip()
                pub_date = (item.findtext("pubDate") or "").strip()
                description = (item.findtext("description") or "").strip()

                if not title:
                    continue

                # Identify practice area from title/description
                hints = self._classify_content(title + " " + description)
                if not hints:
                    hints = self._firm.practice_focus[:2]

                results.append(
                    ScraperResult(
                        source_id=self.source_id,
                        signal_type="blog_practice_alert",
                        source_url=str(link) if link else None,
                        signal_value={
                            "firm": self._firm.firm_name,
                            "firm_id": self._firm.firm_id,
                            "tier": self._firm.tier,
                            "title": title,
                            "pub_date": pub_date,
                        },
                        signal_text=f"[{self._firm.firm_name}] {title}",
                        published_at=self._parse_date(pub_date),
                        practice_area_hints=hints,
                        raw_payload={
                            "firm_id": self._firm.firm_id,
                            "title": title,
                            "description": description[:1000],
                            "link": link,
                        },
                        confidence_score=0.85 if self._firm.tier == 1 else 0.75,
                    )
                )
        except ET.ParseError as e:
            log.warning("lawblog_rss_parse_error", firm=self._firm.firm_id, error=str(e))
        return results

    def _parse_html(self, html: str) -> list[ScraperResult]:
        results = []
        try:
            soup = BeautifulSoup(html, "html.parser")
            # Common blog article patterns
            selectors = [
                "article h2 a",
                "article h3 a",
                ".blog-post h2 a",
                ".insight h2 a",
                ".publication-title a",
                ".news-item a",
                "h2.entry-title a",
                "h3.entry-title a",
            ]
            seen = set()
            for sel in selectors:
                for link_el in soup.select(sel)[:20]:
                    title = link_el.get_text(strip=True)
                    href = str(link_el.get("href", "") or "")
                    if not title or title in seen:
                        continue
                    seen.add(title)
                    url = href if href.startswith("http") else f"{self._firm.base_url}{href}"
                    hints = self._classify_content(title)
                    if not hints:
                        hints = self._firm.practice_focus[:2]
                    results.append(
                        ScraperResult(
                            source_id=self.source_id,
                            signal_type="blog_practice_alert",
                            source_url=url,
                            signal_value={
                                "firm": self._firm.firm_name,
                                "firm_id": self._firm.firm_id,
                                "tier": self._firm.tier,
                                "title": title,
                            },
                            signal_text=f"[{self._firm.firm_name}] {title}",
                            practice_area_hints=hints,
                            raw_payload={"firm_id": self._firm.firm_id, "title": title, "url": url},
                            confidence_score=0.8 if self._firm.tier == 1 else 0.7,
                        )
                    )
        except Exception as e:
            log.warning("lawblog_html_parse_error", firm=self._firm.firm_id, error=str(e))
        return results

    async def _scrape_html_fallback(self) -> list[ScraperResult]:
        """Try the base URL insights page if RSS fails."""
        try:
            insights_url = f"{self._firm.base_url}/insights"
            response = await self.get(insights_url)
            if response.status_code == 200:
                return self._parse_html(response.text)
        except Exception:  # nosec B110
            pass
        return []

    def _classify_content(self, text: str) -> list[str]:
        text = text.lower()
        area_keywords = {
            "ma": ["merger", "acquisition", "takeover", "m&a", "transaction", "deal"],
            "securities": ["securities", "prospectus", "ipo", "capital market", "disclosure"],
            "employment": ["employment", "labour", "dismissal", "termination", "human rights"],
            "competition": [
                "competition",
                "antitrust",
                "cartel",
                "abuse of dominance",
                "merger review",
            ],
            "insolvency": ["insolvency", "restructuring", "ccaa", "receivership", "bankruptcy"],
            "regulatory": ["regulatory", "compliance", "enforcement", "osfi", "osf", "fintrac"],
            "privacy": ["privacy", "data", "pipeda", "cybersecurity", "breach"],
            "tax": ["tax", "cra", "gst", "transfer pricing", "income tax"],
            "environmental": ["environmental", "climate", "carbon", "esg", "indigenous"],
            "litigation": ["litigation", "lawsuit", "arbitration", "dispute", "judgment"],
            "ip": ["intellectual property", "patent", "trademark", "copyright"],
            "banking": ["banking", "fintech", "financial services", "lending", "credit"],
            "real_estate": ["real estate", "property", "condo", "zoning", "development"],
            "health_life_sciences": ["health", "pharmaceutical", "drug", "fda", "health canada"],
            "class_actions": ["class action", "class proceeding", "certification"],
        }
        hints = []
        for area, keywords in area_keywords.items():
            if any(kw in text for kw in keywords):
                hints.append(area)
        return hints


# ── Register all 27 firms via the registry ─────────────────────────────────────
def _make_firm_scraper_class(firm: FirmConfig) -> type:
    """
    Dynamically create a registered scraper class for each firm.
    We need actual classes (not instances) because the registry maps source_id → class.
    """
    class_name = f"LawBlog{firm.firm_id.replace('-', '').replace('_', '').title()}Scraper"

    def init(self: Any) -> None:
        LawFirmBlogScraper.__init__(self, firm)

    scraper_cls = type(
        class_name,
        (LawFirmBlogScraper,),
        {
            "source_id": _build_source_id(firm),
            "source_name": f"{firm.firm_name} Blog",
            "signal_types": ["blog_legal_trend", "blog_practice_alert"],
            "CATEGORY": "lawblog",
            "__init__": init,
        },
    )
    # Register
    from app.scrapers.registry import _REGISTRY

    _REGISTRY[_build_source_id(firm)] = scraper_cls
    return scraper_cls


# Auto-register all firms when module is imported
_firm_scraper_classes: list[type] = []
for _firm in ALL_FIRMS:
    _cls = _make_firm_scraper_class(_firm)
    _firm_scraper_classes.append(_cls)
    # Also expose at module level for direct import
    globals()[_cls.__name__] = _cls


def get_all_firm_scrapers() -> list[LawFirmBlogScraper]:
    """Return fresh instances of all 27 firm blog scrapers."""
    return [cls() for cls in _firm_scraper_classes]
