"""FINTRAC enforcement actions and advisory notices."""
from __future__ import annotations
import xml.etree.ElementTree as ET
import structlog
from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register
log = structlog.get_logger(__name__)

@register
class FINTRACScraper(BaseScraper):
    source_id = "regulatory_fintrac"
    source_name = "FINTRAC (Financial Transactions and Reports Analysis Centre)"
    signal_types = ["regulatory_fintrac_penalty", "regulatory_fintrac_advisory"]
    rate_limit_rps = 0.1; concurrency = 1; ttl_seconds = 86400

    async def scrape(self) -> list[ScraperResult]:
        results = []
        try:
            # FINTRAC administrative monetary penalties
            resp = await self.get("https://www.fintrac-canafe.gc.ca/pen/1-eng")
            if resp.status_code == 200:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(resp.text, "html.parser")
                for row in soup.select("table tbody tr")[:30]:
                    cells = row.find_all("td")
                    if len(cells) < 3: continue
                    entity = cells[0].get_text(strip=True)
                    amount = cells[1].get_text(strip=True)
                    date = cells[2].get_text(strip=True)
                    if not entity: continue
                    results.append(ScraperResult(
                        source_id=self.source_id, signal_type="regulatory_fintrac_penalty",
                        raw_company_name=entity,
                        signal_value={"entity": entity, "penalty_amount": amount, "date": date},
                        signal_text=f"FINTRAC penalty: {entity} — {amount}",
                        published_at=self._parse_date(date),
                        practice_area_hints=["financial_regulatory", "banking"],
                        raw_payload={"entity": entity, "amount": amount},
                    ))
        except Exception as exc:
            log.error("fintrac_error", error=str(exc))
        return results
