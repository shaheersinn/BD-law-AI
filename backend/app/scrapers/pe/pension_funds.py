"""
Maple 8 pension fund investment scraper.

Sources: CPP Investments, CDPQ, OTPP, OMERS, AIMCo, HOOPP, PensionPulse blog
press releases.
Signal: pension_fund_investment — fires when Maple 8 pension funds announce
investments correlating with watchlist companies.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET  # nosec B405

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_PENSION_SOURCES = [
    {
        "name": "CPP Investments",
        "url": "https://www.cppinvestments.com/feed/",
        "type": "rss",
    },
    {
        "name": "CDPQ",
        "url": "https://www.cdpq.com/en/news/rss.xml",
        "type": "rss",
    },
    {
        "name": "OTPP",
        "url": "https://www.otpp.com/en-ca/news/",
        "type": "html",
    },
    {
        "name": "OMERS",
        "url": "https://www.omers.com/news",
        "type": "html",
    },
    {
        "name": "PensionPulse",
        "url": "https://pensionpulse.blogspot.com/feeds/posts/default?alt=rss",
        "type": "rss",
    },
]

_INVESTMENT_KEYWORDS = [
    "invest",
    "acquisition",
    "acquired",
    "partner",
    "committed",
    "allocated",
    "stake",
    "portfolio",
    "co-invest",
    "fund",
    "private equity",
    "infrastructure",
    "real estate",
]


@register
class PensionFundsScraper(BaseScraper):
    source_id = "pe_pension_funds"
    source_name = "Maple 8 Pension Funds"
    signal_types = ["pension_fund_investment"]
    CATEGORY = "pe"
    rate_limit_rps = 0.2
    concurrency = 1
    ttl_seconds = 7200

    async def scrape(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []

        for source in _PENSION_SOURCES:
            try:
                if source["type"] == "rss":
                    page_results = await self._scrape_rss(source)
                else:
                    page_results = await self._scrape_html(source)
                results.extend(page_results)
                await self._rate_limit_sleep()
            except Exception as exc:
                log.error("pension_fund_error", source=source["name"], error=str(exc))

        return results

    async def _scrape_rss(self, source: dict[str, str]) -> list[ScraperResult]:
        results: list[ScraperResult] = []

        try:
            resp = await self.get(source["url"])
            if resp.status_code != 200:
                return results

            root = ET.fromstring(resp.text)  # nosec B314 — trusted pension fund RSS
        except Exception as exc:
            log.warning("pension_rss_error", source=source["name"], error=str(exc))
            return results

        for item in root.iter("item"):
            try:
                title = (item.findtext("title") or "").strip()
                link = (item.findtext("link") or "").strip()
                pub_date = (item.findtext("pubDate") or "").strip()
                description = (item.findtext("description") or "").strip()

                combined_lower = f"{title} {description}".lower()

                is_investment = any(kw in combined_lower for kw in _INVESTMENT_KEYWORDS)
                if not is_investment:
                    continue

                company = self._extract_investee(title, description)

                results.append(
                    ScraperResult(
                        source_id=self.source_id,
                        signal_type="pension_fund_investment",
                        raw_company_name=company,
                        source_url=link,
                        signal_value={
                            "pension_fund": source["name"],
                            "title": title,
                            "investee": company,
                        },
                        signal_text=f"{source['name']}: {title}",
                        published_at=self._parse_date(pub_date),
                        practice_area_hints=["Corporate / M&A", "Securities"],
                        raw_payload={"title": title, "description": description[:500]},
                        confidence_score=0.82,
                    )
                )
            except Exception as exc:
                log.warning("pension_rss_item_error", error=str(exc))

        return results

    async def _scrape_html(self, source: dict[str, str]) -> list[ScraperResult]:
        results: list[ScraperResult] = []

        try:
            soup = await self.get_soup(source["url"])
            if not soup:
                return results
        except Exception as exc:
            log.warning("pension_html_error", source=source["name"], error=str(exc))
            return results

        articles = (
            soup.find_all("article")
            or soup.find_all("div", class_=re.compile(r"news|press|post", re.I))
        )

        for article in articles[:20]:
            try:
                title_el = article.find(["h2", "h3", "h4", "a"])
                title = self.safe_text(title_el) if title_el else ""
                if not title:
                    continue

                title_lower = title.lower()
                is_investment = any(kw in title_lower for kw in _INVESTMENT_KEYWORDS)
                if not is_investment:
                    continue

                link_el = article.find("a", href=True)
                source_url = ""
                if link_el:
                    href = str(link_el.get("href", ""))
                    if href.startswith("http"):
                        source_url = href

                company = self._extract_investee(title, "")

                results.append(
                    ScraperResult(
                        source_id=self.source_id,
                        signal_type="pension_fund_investment",
                        raw_company_name=company,
                        source_url=source_url or source["url"],
                        signal_value={
                            "pension_fund": source["name"],
                            "title": title,
                            "investee": company,
                        },
                        signal_text=f"{source['name']}: {title}",
                        published_at=self._now_utc(),
                        practice_area_hints=["Corporate / M&A", "Securities"],
                        raw_payload={"title": title},
                        confidence_score=0.80,
                    )
                )
            except Exception as exc:
                log.warning("pension_html_article_error", error=str(exc))

        return results

    @staticmethod
    def _extract_investee(title: str, description: str) -> str | None:
        """Extract investee company name from press release."""
        combined = f"{title}\n{description}"
        patterns = [
            r"(?:acquires?|invests? in|partners? with|stake in)\s+(.+?)(?:\s*[-–,;(]|$)",
            r"(.+?)\s+(?:acquisition|investment|partnership|deal)\b",
        ]
        for pattern in patterns:
            match = re.search(pattern, combined, re.I)
            if match:
                name = match.group(1).strip()
                if len(name) > 3:
                    return name
        return None
