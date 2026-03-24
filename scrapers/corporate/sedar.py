"""
app/scrapers/corporate/sedar.py — SEDAR+ scraper.

Source: https://efts.sedar.com (SEDAR full-text search system)
        https://www.sedarplus.ca (SEDAR+ public search)

What it scrapes:
  - Annual reports (AIF, Annual Information Form)
  - Material change reports (MCR)
  - Management Discussion & Analysis (MD&A)
  - Press releases with legal/regulatory content
  - Cease trade orders
  - Technical reports

Signal types:
  - filing_annual: Annual Information Form, MD&A
  - filing_material_change: Material Change Report
  - filing_cease_trade: Cease Trade Order
  - filing_quarterly: Quarterly reports

Rate limit: 0.5 rps (no official limit, respectful)
Auth: None required (public filings)

SEDAR+ has no official API. We scrape the EFTS full-text search endpoint
which has been used by researchers for years.
"""
from __future__ import annotations
import json
import re
from datetime import datetime, timezone, timedelta
from typing import Any

import structlog
from bs4 import BeautifulSoup

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

# SEDAR EFTS search endpoint (legacy SEDAR full-text search, still active)
_EFTS_BASE = "https://efts.sedar.com/EFTSPublicSearchServlet"

# Filing types we care about for legal signal detection
_TARGET_FILING_TYPES = {
    "40F": "filing_annual",
    "AIF": "filing_annual",
    "ARS": "filing_annual",
    "MCR": "filing_material_change",
    "MD&A": "filing_annual",
    "PRE14A": "filing_proxy",
    "CTN": "filing_cease_trade",
    "Cease Trade Order": "filing_cease_trade",
    "Material Change": "filing_material_change",
    "Annual Information Form": "filing_annual",
    "Annual Report": "filing_annual",
}

# Practice area keywords in filing titles/content
_PRACTICE_HINTS: dict[str, list[str]] = {
    "litigation": ["lawsuit", "litigation", "claim", "action", "judgment", "court"],
    "regulatory": ["regulatory", "investigation", "enforcement", "compliance"],
    "insolvency": ["restructuring", "ccaa", "insolvency", "creditor", "receivership", "bankruptcy"],
    "securities": ["securities", "disclosure", "material change", "insider", "cease trade"],
    "employment": ["termination", "wrongful dismissal", "human rights", "labour"],
    "environmental": ["environmental", "contamination", "remediation", "spill", "climate"],
    "competition": ["competition bureau", "merger", "acquisition", "antitrust", "cartel"],
    "privacy": ["privacy", "data breach", "personal information", "opc"],
    "tax": ["tax", "cra", "assessment", "reassessment", "transfer pricing"],
    "real_estate": ["real estate", "property", "lease", "zoning", "expropriation"],
}


@register
class SEDARScraper(BaseScraper):
    source_id = "corporate_sedar"
    source_name = "SEDAR+ Filing System"
    signal_types = ["filing_annual", "filing_material_change", "filing_cease_trade"]
    rate_limit_rps = 0.5
    concurrency = 2
    retry_attempts = 3
    timeout_seconds = 45.0
    ttl_seconds = 3600  # 1 hour

    async def scrape(self) -> list[ScraperResult]:
        """
        Scrape recent SEDAR+ filings.

        Strategy:
          1. Search EFTS for filings in last 7 days
          2. Filter to signal-relevant filing types
          3. Extract company name, filing type, date, URL
          4. Return ScraperResult for each filing
        """
        results: list[ScraperResult] = []
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=7)

        try:
            # Search for material change reports (highest legal signal value)
            mcr_results = await self._search_efts(
                query="material change",
                filing_type="Material Change Report",
                days_back=7,
            )
            results.extend(mcr_results)
            await self._rate_limit_sleep()

            # Search for cease trade orders
            cto_results = await self._search_efts(
                query="cease trade order",
                filing_type="Cease Trade Order",
                days_back=7,
            )
            results.extend(cto_results)
            await self._rate_limit_sleep()

            # Search for recent AIF/Annual Reports
            aif_results = await self._search_efts(
                query="annual information form",
                filing_type="Annual Information Form",
                days_back=30,  # Annual reports — wider window
            )
            results.extend(aif_results)

            log.info("sedar_scrape_complete", total=len(results))
            return results

        except Exception as exc:
            log.error("sedar_scrape_error", error=str(exc), exc_info=True)
            return results  # Return partial results

    async def _search_efts(
        self,
        query: str,
        filing_type: str,
        days_back: int = 7,
    ) -> list[ScraperResult]:
        """Search EFTS for filings matching query + type in recent days."""
        results: list[ScraperResult] = []
        start_date = (datetime.now(tz=timezone.utc) - timedelta(days=days_back)).strftime("%Y-%m-%d")
        end_date = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")

        params = {
            "target": "EFTSPublicSearchServlet",
            "keyword": query,
            "filetype": filing_type,
            "fdateBegin": start_date,
            "fdateEnd": end_date,
            "dateType": "filing",
            "lang": "EN",
            "page": "1",
            "ipp": "50",
        }

        try:
            response = await self.get(_EFTS_BASE, params=params)
            if response.status_code != 200:
                log.warning("sedar_efts_non200", status=response.status_code, query=query)
                return results

            soup = BeautifulSoup(response.text, "html.parser")
            filings = self._parse_efts_results(soup)

            for filing in filings:
                signal_type = _TARGET_FILING_TYPES.get(filing_type, "filing_material_change")
                hints = self._extract_practice_hints(filing.get("title", "") + " " + filing.get("description", ""))

                results.append(ScraperResult(
                    source_id=self.source_id,
                    signal_type=signal_type,
                    raw_company_name=filing.get("company_name"),
                    raw_company_id=filing.get("sedar_id"),
                    source_url=filing.get("url"),
                    signal_value={
                        "filing_type": filing_type,
                        "filing_date": filing.get("filing_date"),
                        "sedar_id": filing.get("sedar_id"),
                        "document_id": filing.get("doc_id"),
                    },
                    signal_text=f"{filing.get('company_name')} — {filing_type}: {filing.get('title', '')}",
                    published_at=self._parse_date(filing.get("filing_date")),
                    practice_area_hints=hints,
                    raw_payload=filing,
                ))

        except Exception as exc:
            log.error("sedar_efts_search_failed", query=query, error=str(exc))

        return results

    def _parse_efts_results(self, soup: BeautifulSoup) -> list[dict[str, Any]]:
        """Parse EFTS HTML search results page."""
        filings: list[dict[str, Any]] = []
        try:
            # EFTS returns a table of results
            rows = soup.find_all("tr", class_=re.compile(r"result|filing"))
            for row in rows:
                cells = row.find_all("td")
                if len(cells) < 4:
                    continue
                filing: dict[str, Any] = {}
                # Column order: Company | Filing Type | Date | Document
                filing["company_name"] = cells[0].get_text(strip=True)
                filing["filing_type"] = cells[1].get_text(strip=True)
                filing["filing_date"] = cells[2].get_text(strip=True)
                link = cells[3].find("a")
                if link:
                    filing["url"] = link.get("href", "")
                    filing["title"] = link.get_text(strip=True)
                filings.append(filing)
        except Exception as parse_exc:
            log.warning("sedar_parse_failed", error=str(parse_exc))
        return filings

    def _extract_practice_hints(self, text: str) -> list[str]:
        """Extract practice area hints from filing text."""
        text_lower = text.lower()
        hints = []
        for practice, keywords in _PRACTICE_HINTS.items():
            if any(kw in text_lower for kw in keywords):
                hints.append(practice)
        return hints

    async def health_check(self) -> bool:
        try:
            response = await self.get(_EFTS_BASE, params={"target": "EFTSPublicSearchServlet", "lang": "EN"})
            return response.status_code in (200, 302)
        except Exception:
            return False
