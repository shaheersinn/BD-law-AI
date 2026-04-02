"""
BC Court Services Online scraper.

Source: BC Supreme Court civil filings via CSO.
Signal: bc_supreme_court_filing — fires when watchlist companies appear
as parties in BC Supreme Court civil filings.
"""

from __future__ import annotations

import re

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_BC_CSO_URL = "https://justice.gov.bc.ca/cso/"
_BC_CSO_SEARCH_URL = "https://justice.gov.bc.ca/cso/esearch/civil/searchPartyForm.do"


@register
class BCCSOScraper(BaseScraper):
    source_id = "courts_bc_cso"
    source_name = "BC Court Services Online"
    signal_types = ["bc_supreme_court_filing"]
    CATEGORY = "courts"
    rate_limit_rps = 0.2
    concurrency = 1
    ttl_seconds = 7200

    async def scrape(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []

        try:
            soup = await self.get_soup(_BC_CSO_URL)
            if not soup:
                return results
        except Exception as exc:
            log.error("bc_cso_fetch_error", error=str(exc))
            return results

        entries = (
            soup.select("table tbody tr")
            or soup.find_all("div", class_=re.compile(r"result|case|filing", re.I))
            or soup.find_all("li", class_=re.compile(r"result|case", re.I))
        )

        for entry in entries[:40]:
            try:
                text = self.safe_text(entry)
                if not text or len(text) < 10:
                    continue

                title_el = entry.find(["h2", "h3", "h4", "a", "strong"])
                title = self.safe_text(title_el) if title_el else text[:100]

                party = self._extract_party(title, text)

                link_el = entry.find("a", href=True)
                source_url = ""
                if link_el:
                    href = str(link_el.get("href", ""))
                    if href.startswith("http"):
                        source_url = href

                # Extract file number
                file_no = self._extract_file_number(text)

                results.append(
                    ScraperResult(
                        source_id=self.source_id,
                        signal_type="bc_supreme_court_filing",
                        raw_company_name=party,
                        source_url=source_url or _BC_CSO_URL,
                        signal_value={
                            "title": title,
                            "court": "BC Supreme Court",
                            "file_number": file_no,
                        },
                        signal_text=f"BC Supreme Court: {title}",
                        published_at=self._now_utc(),
                        practice_area_hints=["Litigation"],
                        raw_payload={"title": title, "text": text[:500]},
                        confidence_score=0.85,
                    )
                )
            except Exception as exc:
                log.warning("bc_cso_entry_error", error=str(exc))

        return results

    @staticmethod
    def _extract_party(title: str, text: str) -> str | None:
        """Extract party name from case listing."""
        combined = f"{title}\n{text}"
        match = re.search(r"(.+?)\s+v\.\s+", combined)
        if match:
            return match.group(1).strip()
        for label in ["plaintiff", "petitioner", "applicant"]:
            pattern = rf"{label}\s*[:]\s*(.+?)(?:\n|$)"
            match = re.search(pattern, combined, re.I)
            if match:
                return match.group(1).strip()
        return None

    @staticmethod
    def _extract_file_number(text: str) -> str | None:
        """Extract court file number."""
        match = re.search(r"(?:file|no\.?|#)\s*[:.]?\s*(\d{2,}[-/]\d+)", text, re.I)
        return match.group(1) if match else None
