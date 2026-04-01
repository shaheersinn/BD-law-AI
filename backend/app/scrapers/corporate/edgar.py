"""
app/scrapers/corporate/edgar.py — SEC EDGAR scraper.

Source: https://efts.sec.gov/LATEST/search-index (EDGAR full-text search)
        https://www.sec.gov/cgi-bin/browse-edgar (company search)
        https://data.sec.gov/submissions (company JSON feeds)

What it scrapes:
  - 6-K filings (foreign private issuer interim reports — many Canadian companies)
  - 20-F filings (foreign private issuer annual reports)
  - F-1, F-3 (registration statements — capital markets signal)
  - 13D, 13G (activist shareholder signals — M&A/governance)
  - SC TO-T (tender offers — M&A signal)
  - DEF 14A (proxy — governance/M&A signal)

Rate limit: 0.1 rps (EDGAR rate limit is 10 req/s, we stay at 0.1)
Auth: None required (public API)

EDGAR full-text search: https://efts.sec.gov/LATEST/search-index?q=...&dateRange=custom&startdt=...
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_EDGAR_SEARCH = "https://efts.sec.gov/LATEST/search-index"
_EDGAR_SUBMISSIONS = "https://data.sec.gov/submissions"

# Filing types → signal types
_FILING_MAP = {
    "6-K": "filing_interim",
    "20-F": "filing_annual",
    "F-1": "filing_registration",
    "F-3": "filing_registration",
    "13D": "filing_activist_shareholder",
    "13G": "filing_activist_shareholder",
    "SC TO-T": "filing_tender_offer",
    "DEF 14A": "filing_proxy",
    "8-K": "filing_material_change",
    "10-K": "filing_annual",
}

# Practice area hints by filing type
_PRACTICE_MAP = {
    "13D": ["ma", "governance"],
    "13G": ["ma", "governance"],
    "SC TO-T": ["ma"],
    "6-K": ["securities"],
    "20-F": ["securities", "regulatory"],
    "F-1": ["securities", "capital_markets"],
}


@register
class EDGARScraper(BaseScraper):
    source_id = "corporate_edgar"
    CATEGORY = "corporate"
    source_name = "SEC EDGAR"
    signal_types = [
        "filing_annual",
        "filing_material_change",
        "filing_activist_shareholder",
        "filing_tender_offer",
    ]
    rate_limit_rps = 0.1
    concurrency = 2
    retry_attempts = 4
    timeout_seconds = 30.0
    ttl_seconds = 3600

    async def scrape(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []
        try:
            # Activist shareholder filings (13D/13G) — high M&A signal
            activist = await self._search_edgar(form_types=["13D", "13G"], days_back=14)
            results.extend(activist)
            await self._rate_limit_sleep()

            # Tender offers
            tender = await self._search_edgar(form_types=["SC TO-T"], days_back=14)
            results.extend(tender)
            await self._rate_limit_sleep()

            # Foreign private issuer 6-K (many Canadian companies)
            sixk = await self._search_edgar(form_types=["6-K"], days_back=7)
            results.extend(sixk)
            await self._rate_limit_sleep()

            # Annual 20-F
            twentyf = await self._search_edgar(form_types=["20-F"], days_back=30)
            results.extend(twentyf)

            log.info("edgar_scrape_complete", total=len(results))
            return results

        except Exception as exc:
            log.error("edgar_scrape_error", error=str(exc), exc_info=True)
            return results

    async def _search_edgar(self, form_types: list[str], days_back: int = 7) -> list[ScraperResult]:
        results: list[ScraperResult] = []
        start_dt = (datetime.now(tz=UTC) - timedelta(days=days_back)).strftime("%Y-%m-%d")
        end_dt = datetime.now(tz=UTC).strftime("%Y-%m-%d")

        for form_type in form_types:
            try:
                params = {
                    "q": f'"{form_type}"',
                    "dateRange": "custom",
                    "startdt": start_dt,
                    "enddt": end_dt,
                    "forms": form_type,
                    "_source": "hits.hits._source",
                    "from": "0",
                    "size": "40",
                }
                headers = {
                    "User-Agent": "ORACLE-BD-Research research@halcyon.legal",  # EDGAR requires identifying UA
                    "Accept": "application/json",
                }
                response = await self.get(
                    _EDGAR_SEARCH,
                    params=params,
                    headers=headers,
                )
                if response.status_code != 200:
                    log.warning("edgar_non200", form=form_type, status=response.status_code)
                    continue

                data = response.json()
                hits = data.get("hits", {}).get("hits", [])

                for hit in hits:
                    src = hit.get("_source", {})
                    signal_type = _FILING_MAP.get(form_type, "filing_material_change")
                    hints = _PRACTICE_MAP.get(form_type, ["securities"])

                    results.append(
                        ScraperResult(
                            source_id=self.source_id,
                            signal_type=signal_type,
                            raw_company_name=src.get("entity_name")
                            or src.get("display_names", [None])[0],
                            raw_company_id=src.get("entity_id"),
                            source_url=f"https://www.sec.gov{src.get('file_date', '')}",
                            signal_value={
                                "form_type": form_type,
                                "cik": src.get("entity_id"),
                                "file_date": src.get("file_date"),
                                "period_of_report": src.get("period_of_report"),
                                "accession_no": src.get("accession_no"),
                            },
                            signal_text=f"{src.get('entity_name')} — {form_type} filed {src.get('file_date')}",
                            published_at=self._parse_date(src.get("file_date")),
                            practice_area_hints=hints,
                            raw_payload=src,
                        )
                    )

                await self._rate_limit_sleep()

            except Exception as exc:
                log.error("edgar_form_search_failed", form=form_type, error=str(exc))

        return results

    async def health_check(self) -> bool:
        try:
            response = await self.get(
                _EDGAR_SEARCH,
                params={"q": "test", "forms": "10-K", "size": "1"},
                headers={"User-Agent": "ORACLE-BD-Research research@halcyon.legal"},
            )
            return response.status_code == 200
        except Exception:
            return False
