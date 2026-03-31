"""
app/scrapers/regulatory/amf.py — AMF disciplinary proceedings scraper.

Data source: https://lautorite.qc.ca/en/professionals/disciplinary-proceedings
Approach: HTML scraping with BeautifulSoup
Signal value: HIGH — AMF enforcement predicts securities litigation mandates
Note: English section only per CLAUDE.md rules
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_AMF_URL = "https://lautorite.qc.ca/en/professionals/disciplinary-proceedings"
_AMF_BASE = "https://lautorite.qc.ca"


@register
class AMFDisciplinaryScraper(BaseScraper):
    """
    AMF Quebec disciplinary proceedings scraper.

    Scrapes English-language disciplinary proceedings from the
    Autorité des marchés financiers (Quebec securities regulator).
    Rate limit: 0.2 rps (government site).
    """

    source_id = "regulatory_amf"
    source_name = "AMF Quebec Disciplinary Proceedings"
    signal_types = ["regulatory_enforcement"]
    CATEGORY = "regulatory"
    rate_limit_rps = 0.2
    concurrency = 1
    requires_auth = False

    async def scrape(self) -> list[ScraperResult]:
        """Scrape AMF disciplinary proceedings page."""
        results: list[ScraperResult] = []
        cutoff = datetime.now(tz=UTC) - timedelta(days=90)

        try:
            resp = await self.get(_AMF_URL)
            if resp.status_code != 200:
                log.warning("amf_fetch_failed", status=resp.status_code)
                return results

            from bs4 import BeautifulSoup

            soup = BeautifulSoup(resp.text, "html.parser")

            items = (
                soup.select("table tbody tr")
                or soup.select("article")
                or soup.select("div.views-row")
                or soup.select("ul.results li, div.card, li.list-group-item")
            )

            for item in items[:30]:
                result = self._parse_item(item, cutoff)
                if result:
                    results.append(result)

        except Exception as exc:
            log.error("amf_scrape_error", error=str(exc))

        log.info("amf_scrape_complete", count=len(results))
        return results

    def _parse_item(
        self, item: Any, cutoff: datetime
    ) -> ScraperResult | None:
        cells = item.find_all("td")
        if cells and len(cells) >= 2:
            return self._parse_table_row(cells, cutoff)

        title_el = item.find(["h2", "h3", "h4", "a"])
        if not title_el:
            return None
        title = self.safe_text(title_el)
        if not title or len(title) < 5:
            return None

        link_el = item.find("a", href=True)
        source_url = None
        if link_el:
            href = str(link_el.get("href", ""))
            source_url = href if href.startswith("http") else f"{_AMF_BASE}{href}"

        date_el = item.find("time") or item.find(
            class_=lambda c: c and "date" in str(c).lower()
        )
        published_at = None
        if date_el:
            date_str = date_el.get("datetime") or self.safe_text(date_el)
            published_at = self._parse_date(date_str)

        if published_at and published_at < cutoff:
            return None

        respondent = self._extract_respondent(title)

        return ScraperResult(
            source_id=self.source_id,
            signal_type="regulatory_enforcement",
            raw_company_name=respondent,
            source_url=source_url,
            signal_value={"title": title, "regulator": "AMF Quebec"},
            signal_text=f"AMF Disciplinary: {title}",
            published_at=published_at or self._now_utc(),
            practice_area_hints=[
                "securities_capital_markets",
                "financial_regulatory",
                "regulatory_compliance",
            ],
            raw_payload={"title": title, "url": source_url},
            confidence_score=0.85,
        )

    def _parse_table_row(
        self, cells: list[Any], cutoff: datetime
    ) -> ScraperResult | None:
        respondent = self.safe_text(cells[0])
        if not respondent or len(respondent) < 3:
            return None

        action_type = self.safe_text(cells[1]) if len(cells) > 1 else ""
        date_str = self.safe_text(cells[-1])
        published_at = self._parse_date(date_str)

        if published_at and published_at < cutoff:
            return None

        link_el = cells[0].find("a", href=True)
        source_url = None
        if link_el:
            href = str(link_el.get("href", ""))
            source_url = href if href.startswith("http") else f"{_AMF_BASE}{href}"

        return ScraperResult(
            source_id=self.source_id,
            signal_type="regulatory_enforcement",
            raw_company_name=respondent,
            source_url=source_url,
            signal_value={
                "respondent": respondent,
                "action_type": action_type,
                "regulator": "AMF Quebec",
            },
            signal_text=f"AMF Disciplinary: {action_type} — {respondent}",
            published_at=published_at or self._now_utc(),
            practice_area_hints=[
                "securities_capital_markets",
                "financial_regulatory",
                "regulatory_compliance",
            ],
            raw_payload={"respondent": respondent, "action_type": action_type},
            confidence_score=0.85,
        )

    @staticmethod
    def _extract_respondent(title: str) -> str | None:
        lower = title.lower()
        for prefix in ["in the matter of ", "re ", "against "]:
            if prefix in lower:
                idx = lower.index(prefix) + len(prefix)
                name = title[idx:].split(" — ")[0].split(" - ")[0].strip()
                if name:
                    return name
        return None
