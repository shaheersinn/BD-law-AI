"""
app/scrapers/regulatory/amf_quebec.py — AMF Quebec scraper.
"""

from __future__ import annotations

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_SOURCE_URL = "https://lautorite.qc.ca"
_URL = "https://lautorite.qc.ca/professionnels/nouvelles/communiques"


@register
class AmfQuebecScraper(BaseScraper):
    """
    AMF Quebec (Autorité des marchés financiers) scraper.

    Scrapes regulatory enforcement actions and bulletins.
    """

    source_id = "regulatory_amf_quebec"
    source_name = "AMF Quebec (Autorité des marchés financiers)"
    signal_types = ["regulatory_enforcement", "regulatory_bulletin"]
    CATEGORY = "regulatory"
    rate_limit_rps = 0.5
    concurrency = 1
    requires_auth = False

    async def scrape(self) -> list[ScraperResult]:
        """Scrape AMF Quebec enforcement actions."""
        results: list[ScraperResult] = []
        try:
            resp = await self.get(_URL)
            if resp.status_code != 200:
                return results
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(resp.text, "html.parser")
            items = soup.select(
                "article, li.action-item, table tbody tr, div.enforcement-item, ul.results li"
            )
            for item in items[:20]:
                link_tag = item.find("a")
                title_el = link_tag or item.find("h3") or item.find("h4") or item
                title = title_el.get_text(strip=True) if title_el else ""
                link = link_tag.get("href", "") if link_tag else ""
                if link and not str(link).startswith("http"):
                    link = f"{_SOURCE_URL}{link}"
                date_el = (
                    item.find("time") or item.find(class_="date") or item.find(class_="published")
                )
                date_str = date_el.get_text(strip=True) if date_el else ""
                if not title or len(title) < 5:
                    continue
                results.append(
                    ScraperResult(
                        source_id=self.source_id,
                        signal_type="regulatory_enforcement",
                        source_url=str(link) if link else None,
                        signal_value={"title": title, "regulator": "AMF Quebec"},
                        signal_text=f"AMF Quebec: {title}",
                        published_at=self._parse_date(date_str),
                        practice_area_hints=["financial_regulatory", "securities_capital_markets"],
                        raw_payload={"title": title, "link": link},
                        confidence_score=0.9,
                    )
                )
        except Exception as exc:
            log.error("amf_quebec_error", error=str(exc))
        return results
