"""
High-value probate filing scraper.

Sources: Ontario Courts Public Portal, BC Court Services Online,
Alberta Court of King's Bench estate filings.
Signal: probate_filing_high_value — fires when estate filings > $2M detected.
"""

from __future__ import annotations

import re

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_SOURCES = [
    {
        "name": "Ontario Superior Court — Estate",
        "url": "https://www.ontariocourts.ca/scj/practice/estates/",
        "province": "ON",
    },
    {
        "name": "BC Court Services Online",
        "url": "https://justice.gov.bc.ca/cso/",
        "province": "BC",
    },
    {
        "name": "Alberta Court of King's Bench — Surrogate",
        "url": "https://www.albertacourts.ca/kb/resources/announcements",
        "province": "AB",
    },
]

_HIGH_VALUE_THRESHOLD = 2_000_000  # $2M CAD


@register
class ProbateFilingsScraper(BaseScraper):
    source_id = "hnwi_probate_filings"
    source_name = "Provincial Probate Courts"
    signal_types = ["probate_filing_high_value"]
    CATEGORY = "hnwi"
    rate_limit_rps = 0.2
    concurrency = 1
    ttl_seconds = 7200

    async def scrape(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []

        for source in _SOURCES:
            try:
                page_results = await self._scrape_court(source)
                results.extend(page_results)
            except Exception as exc:
                log.error(
                    "probate_scrape_error",
                    court=source["name"],
                    error=str(exc),
                )

        return results

    async def _scrape_court(self, source: dict[str, str]) -> list[ScraperResult]:
        results: list[ScraperResult] = []

        try:
            soup = await self.get_soup(source["url"])
            if not soup:
                return results
        except Exception as exc:
            log.warning("probate_fetch_error", court=source["name"], error=str(exc))
            return results

        # Look for filing entries in tables or lists
        rows = (
            soup.select("table tbody tr")
            or soup.find_all("div", class_=re.compile(r"filing|case|estate", re.I))
            or soup.find_all("li", class_=re.compile(r"filing|case", re.I))
        )

        for row in rows[:30]:
            try:
                text = self.safe_text(row)
                if not text:
                    continue

                text_lower = text.lower()
                # Filter for estate/probate/surrogate matters
                if not any(
                    kw in text_lower
                    for kw in ["estate", "probate", "surrogate", "certificate of appointment"]
                ):
                    continue

                # Try to extract value
                value = self._extract_value(text)
                if value is not None and value < _HIGH_VALUE_THRESHOLD:
                    continue

                # Extract deceased/applicant name
                name = self._extract_party_name(text)

                link_el = row.find("a", href=True)
                file_url = ""
                if link_el:
                    href = str(link_el.get("href", ""))
                    if href.startswith("http"):
                        file_url = href

                results.append(
                    ScraperResult(
                        source_id=self.source_id,
                        signal_type="probate_filing_high_value",
                        raw_company_name=name,
                        source_url=file_url or source["url"],
                        signal_value={
                            "court": source["name"],
                            "province": source["province"],
                            "estate_value_cad": value,
                            "filing_text": text[:300],
                        },
                        signal_text=f"Probate filing ({source['province']}): {text[:120]}",
                        published_at=self._now_utc(),
                        practice_area_hints=["Wills / Estates"],
                        raw_payload={
                            "court": source["name"],
                            "text": text[:500],
                        },
                        confidence_score=0.80 if value else 0.65,
                    )
                )
            except Exception as exc:
                log.warning("probate_row_parse_error", error=str(exc))

        return results

    @staticmethod
    def _extract_value(text: str) -> int | None:
        """Extract dollar value from filing text."""
        match = re.search(r"\$\s*([\d,]+(?:\.\d{2})?)", text)
        if match:
            try:
                return int(float(match.group(1).replace(",", "")))
            except ValueError:
                return None
        return None

    @staticmethod
    def _extract_party_name(text: str) -> str | None:
        """Extract deceased or applicant name."""
        for prefix in [
            "estate of ",
            "re: ",
            "in the matter of ",
            "deceased: ",
            "applicant: ",
        ]:
            idx = text.lower().find(prefix)
            if idx != -1:
                start = idx + len(prefix)
                remaining = text[start:]
                match = re.match(r"([A-Za-z\s\.\-']+)", remaining)
                if match:
                    name = match.group(1).strip()
                    if len(name) > 3:
                        return name
        return None
