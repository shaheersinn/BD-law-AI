"""
app/scrapers/regulatory/competition_bureau.py — Competition Bureau scraper.
"""

from __future__ import annotations

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_SOURCE_URL = "https://www.canada.ca/en/competition-bureau"
_URL = "https://www.canada.ca/en/competition-bureau/news/recent-actions.html"


@register
class CompetitionBureauScraper(BaseScraper):
    """
    Competition Bureau of Canada scraper.

    Scrapes regulatory enforcement actions and bulletins.
    """

    source_id = "regulatory_competition_bureau"
    source_name = "Competition Bureau of Canada"
    signal_types = ["regulatory_enforcement", "regulatory_bulletin"]
    CATEGORY = "regulatory"
    rate_limit_rps = 0.5
    concurrency = 1
    requires_auth = False

    async def scrape(self) -> list[ScraperResult]:
        """Scrape Competition Bureau enforcement actions."""
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
                        signal_value={"title": title, "regulator": "Competition Bureau"},
                        signal_text=f"Competition Bureau: {title}",
                        published_at=self._parse_date(date_str),
                        practice_area_hints=["competition_antitrust", "regulatory_compliance"],
                        raw_payload={"title": title, "link": link},
                        confidence_score=0.95,
                    )
                )
        except Exception as exc:
            log.error("competition_bureau_error", error=str(exc))
        return results
