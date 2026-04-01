"""Stanford Class Action Clearinghouse (SCAC) — US/Canadian class action signals."""

from __future__ import annotations

import structlog
from bs4 import BeautifulSoup

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_SCAC_URL = "https://securities.stanford.edu/class-action-filings/index-recently-filed.html"


@register
class StanfordScacScraper(BaseScraper):
    source_id = "legal_scac"
    source_name = "Stanford Class Action Clearinghouse"
    CATEGORY = "legal"
    signal_types = ["litigation_class_action"]
    rate_limit_rps = 0.1
    concurrency = 1
    ttl_seconds = 43200

    async def scrape(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []
        try:
            resp = await self.get(_SCAC_URL)
            if resp.status_code != 200:
                return results
            soup = BeautifulSoup(resp.text, "html.parser")
            rows = soup.select("table.table tbody tr")
            for row in rows[:50]:
                cells = row.find_all("td")
                if len(cells) < 4:
                    continue
                company = cells[0].get_text(strip=True)
                date = cells[1].get_text(strip=True)
                link = row.find("a")
                url = (
                    f"https://securities.stanford.edu{link['href']}"
                    if link and link.get("href")
                    else None
                )
                results.append(
                    ScraperResult(
                        source_id=self.source_id,
                        signal_type="litigation_class_action",
                        raw_company_name=company,
                        source_url=url,
                        signal_value={"company": company, "filing_date": date},
                        signal_text=f"Class action filed: {company}",
                        published_at=self._parse_date(date),
                        practice_area_hints=["class_actions", "securities"],
                        raw_payload={"company": company, "date": date},
                    )
                )
        except Exception as exc:
            log.error("scac_error", error=str(exc))
        return results
