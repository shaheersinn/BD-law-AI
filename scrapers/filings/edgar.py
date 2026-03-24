"""
app/scrapers/filings/edgar.py — SEC EDGAR REST API scraper.

Free API at data.sec.gov — no authentication required.
Rate limit: 10 requests/second (SEC documented limit).
We self-limit to 5 req/sec to be conservative.

Key endpoints used:
  data.sec.gov/submissions/{CIK}.json — filing history for a company
  efts.sec.gov/LATEST/search-index    — full text search
  www.sec.gov/Archives/edgar/daily-index/bulkdata/submissions.zip — bulk bootstrap

Bootstrap strategy (first run):
  Download submissions.zip → extract all Canadian company CIKs
  (Companies with country_of_incorporation = "CA")

Ongoing scraping:
  For each company in our watchlist with a CIK, check recent filings.
  High-signal form types: 8-K, 6-K, 20-F, 40-F, SC 13D, SC 13G, DEF 14A

Signals produced:
  - 8-K material events (item 1.01 agreements, 8.01 other events)
  - 6-K press releases (foreign private issuers = many Canadian companies)
  - 20-F/40-F annual reports with legal contingency disclosures
  - SC 13D/G activist shareholder accumulation
  - DEF 14A proxy circulars (M&A votes)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from app.scrapers.base import BaseScraper, SignalData

log = logging.getLogger(__name__)

# EDGAR form types and their practice area mappings
EDGAR_SIGNAL_FORMS = {
    "8-K": {
        "practice_areas": ["securities_capital_markets", "litigation", "regulatory_compliance"],
        "strength": 0.75,
        "signal_type": "corporate_filing",
    },
    "6-K": {
        "practice_areas": ["securities_capital_markets", "regulatory_compliance"],
        "strength": 0.65,
        "signal_type": "corporate_filing",
    },
    "SC 13D": {
        "practice_areas": ["ma_corporate", "securities_capital_markets"],
        "strength": 0.85,
        "signal_type": "activist_shareholder",
    },
    "SC 13G": {
        "practice_areas": ["ma_corporate", "securities_capital_markets"],
        "strength": 0.70,
        "signal_type": "activist_shareholder",
    },
    "DEF 14A": {
        "practice_areas": ["ma_corporate", "securities_capital_markets"],
        "strength": 0.75,
        "signal_type": "proxy_circular",
    },
    "40-F": {
        "practice_areas": ["securities_capital_markets"],
        "strength": 0.55,
        "signal_type": "annual_report",
    },
    "20-F": {
        "practice_areas": ["securities_capital_markets"],
        "strength": 0.55,
        "signal_type": "annual_report",
    },
    "NT 20-F": {
        "practice_areas": ["securities_capital_markets", "regulatory_compliance"],
        "strength": 0.80,
        "signal_type": "late_filing",
    },
    "NT 40-F": {
        "practice_areas": ["securities_capital_markets", "regulatory_compliance"],
        "strength": 0.80,
        "signal_type": "late_filing",
    },
}

# 8-K item codes that indicate legal/regulatory issues
HIGH_SIGNAL_8K_ITEMS = {
    "1.01": ("ma_corporate", 0.80),          # Entry into material agreement
    "1.02": ("ma_corporate", 0.75),          # Termination of material agreement
    "1.03": ("insolvency_restructuring", 0.95),  # Bankruptcy/receivership
    "2.01": ("ma_corporate", 0.90),          # Completion of acquisition
    "2.03": ("banking_finance", 0.70),       # Creation of direct financial obligation
    "2.06": ("securities_capital_markets", 0.75),  # Material impairments
    "3.01": ("securities_capital_markets", 0.90),  # Notice of delisting
    "4.01": ("regulatory_compliance", 0.85),     # Auditor changes
    "4.02": ("securities_capital_markets", 0.90),  # Non-reliance on financials
    "5.01": ("ma_corporate", 0.85),          # Changes in control
    "5.02": ("securities_capital_markets", 0.65),  # Director/officer changes
    "7.01": ("securities_capital_markets", 0.65),  # Regulation FD disclosures
    "8.01": ("litigation", 0.70),            # Other events
}

# EDGAR base URLs
EDGAR_BASE = "https://data.sec.gov"
EDGAR_ARCHIVES = "https://www.sec.gov/Archives/edgar"
EFTS_BASE = "https://efts.sec.gov"


class EdgarScraper(BaseScraper):
    """
    Scrapes SEC EDGAR for filings by Canadian companies dual-listed on US exchanges.

    Uses the free data.sec.gov REST API — no API key required.
    Rate limited to 5 req/sec (half of documented 10 req/sec limit — polite margin).

    On first run: bootstraps company list from submissions.zip (companies with CIK).
    On subsequent runs: checks recent filings for known CIKs.
    """

    NAME = "edgar_filings"
    CATEGORY = "filings"
    SOURCE_URL = "https://data.sec.gov"
    RATE_LIMIT_RPS = 5.0
    MAX_CONCURRENT = 5
    SOURCE_RELIABILITY = 1.0
    MAX_RETRIES = 3

    # SEC requires user agent with contact info
    BASE_HEADERS = {
        "User-Agent": "ORACLE-Research oracle@halcyon.legal",
        "Accept": "application/json",
        "Accept-Encoding": "gzip, deflate",
    }

    async def run(self) -> list[SignalData]:
        """Scrape recent EDGAR filings for watchlist companies with CIKs."""
        signals: list[SignalData] = []

        companies = await self._load_companies_with_cik(max_companies=100)

        if not companies:
            self.log.info("EDGAR: no CIK-linked companies found — run bootstrap first")
            return signals

        self.log.info("EDGAR: checking %d companies", len(companies))

        for company in companies:
            try:
                company_signals = await self._scrape_company(company)
                signals.extend(company_signals)
            except Exception as exc:
                self.log.error("EDGAR: error on %s: %s", company.get("name"), exc)

        self.log.info("EDGAR: %d signals found", len(signals))
        return signals

    async def _scrape_company(self, company: dict) -> list[SignalData]:
        """Fetch recent filings for a company by CIK."""
        cik = company.get("cik", "").lstrip("0")
        if not cik:
            return []

        # CIK must be zero-padded to 10 digits for the API
        cik_padded = cik.zfill(10)

        url = f"{EDGAR_BASE}/submissions/CIK{cik_padded}.json"
        data = await self.get_json(url)

        if not data:
            return []

        # Recent filings are in data["filings"]["recent"]
        recent = data.get("filings", {}).get("recent", {})
        if not recent:
            return []

        return self._parse_recent_filings(recent, company, data.get("name", company.get("name")))

    def _parse_recent_filings(
        self,
        recent: dict,
        company: dict,
        entity_name: str,
    ) -> list[SignalData]:
        """Parse the recent filings dict from EDGAR submissions API."""
        signals: list[SignalData] = []

        form_types = recent.get("form", [])
        dates = recent.get("filingDate", [])
        accession_nums = recent.get("accessionNumber", [])
        descriptions = recent.get("primaryDocument", [])

        for i, form_type in enumerate(form_types[:50]):  # Last 50 filings
            config = EDGAR_SIGNAL_FORMS.get(form_type)
            if config is None:
                continue

            date_str = dates[i] if i < len(dates) else None
            accession = accession_nums[i] if i < len(accession_nums) else ""
            primary_doc = descriptions[i] if i < len(descriptions) else ""

            published_at = self.parse_date(date_str)

            # Build filing URL
            cik = company.get("cik", "").zfill(10)
            acc_no_dashes = accession.replace("-", "")
            filing_url = (
                f"https://www.sec.gov/Archives/edgar/data/{cik}/"
                f"{acc_no_dashes}/{primary_doc}"
            ) if accession else ""

            # Determine practice areas
            practice_areas = list(config["practice_areas"])
            strength = config["strength"]
            signal_type = config["signal_type"]

            # For 8-K, try to detect item codes in description to refine practice areas
            if form_type == "8-K" and primary_doc:
                for item_code, (area, item_strength) in HIGH_SIGNAL_8K_ITEMS.items():
                    if item_code in primary_doc:
                        if area not in practice_areas:
                            practice_areas.insert(0, area)
                        strength = max(strength, item_strength)

            title = f"{form_type} — {entity_name}"
            if date_str:
                title += f" ({date_str})"

            signals.append(SignalData(
                scraper_name=self.NAME,
                signal_type=signal_type,
                raw_entity_name=entity_name,
                title=title,
                summary=(
                    f"EDGAR {form_type} filing by {entity_name}. "
                    f"Accession: {accession}"
                ),
                source_url=filing_url,
                published_at=published_at,
                practice_areas=practice_areas,
                signal_strength=strength,
                metadata={
                    "form_type": form_type,
                    "accession_number": accession,
                    "cik": company.get("cik"),
                    "primary_document": primary_doc,
                },
            ))

        return signals

    async def bootstrap_from_submissions_zip(self) -> int:
        """
        One-time bootstrap: download submissions.zip and extract Canadian company CIKs.
        Returns count of companies added to DB.

        Call this manually on first deployment:
          python -c "
          import asyncio
          from app.scrapers.filings.edgar import EdgarScraper
          async def main():
              s = EdgarScraper()
              count = await s.bootstrap_from_submissions_zip()
              print(f'Added {count} companies')
          asyncio.run(main())
          "
        """
        import io
        import json
        import zipfile

        self.log.info("EDGAR: downloading submissions.zip (~500MB) — this is a one-time operation")

        response = await self.get(
            "https://www.sec.gov/Archives/edgar/daily-index/bulkdata/submissions.zip"
        )
        if response is None:
            self.log.error("EDGAR: failed to download submissions.zip")
            return 0

        count = 0
        try:
            with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
                for filename in zf.namelist():
                    if not filename.endswith(".json"):
                        continue
                    try:
                        with zf.open(filename) as f:
                            data = json.load(f)

                        # Only process Canadian or dual-listed companies
                        country = data.get("addresses", {}).get("business", {}).get("country", "")
                        if country not in ("CA", "Canada", "CANADA"):
                            continue

                        cik = data.get("cik", "")
                        name = data.get("name", "")
                        tickers = data.get("tickers", [])

                        if cik and name:
                            await self._upsert_company(cik, name, tickers)
                            count += 1

                    except Exception as exc:
                        self.log.debug("EDGAR bootstrap: skip %s: %s", filename, exc)

        except Exception as exc:
            self.log.error("EDGAR bootstrap: zip parse error: %s", exc)

        self.log.info("EDGAR bootstrap: %d Canadian companies added/updated", count)
        return count

    async def _upsert_company(
        self, cik: str, name: str, tickers: list[str]
    ) -> None:
        """Add or update a company record from EDGAR data."""
        try:
            from app.database import AsyncSessionLocal
            from app.models.company import Company
            from sqlalchemy import select
            import re

            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(Company).where(Company.cik == cik.lstrip("0"))
                )
                company = result.scalar_one_or_none()

                if company is None:
                    company = Company(
                        name=name,
                        name_normalized=re.sub(r"[^\w\s]", "", name).lower().strip(),
                        cik=cik.lstrip("0"),
                        ticker=tickers[0] if tickers else None,
                        jurisdiction="US",  # EDGAR = SEC-registered
                        watchlist_priority=3,
                    )
                    db.add(company)
                else:
                    company.name = name
                    if tickers and not company.ticker:
                        company.ticker = tickers[0]

                await db.commit()
        except Exception as exc:
            self.log.debug("EDGAR: upsert error for %s: %s", name, exc)

    async def _load_companies_with_cik(self, max_companies: int = 100) -> list[dict]:
        """Load companies that have EDGAR CIKs."""
        try:
            from app.database import AsyncSessionLocal
            from app.models.company import Company
            from sqlalchemy import select

            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(Company.id, Company.name, Company.cik, Company.ticker)
                    .where(Company.is_active == True)
                    .where(Company.cik.isnot(None))
                    .order_by(Company.watchlist_priority.asc())
                    .limit(max_companies)
                )
                return [
                    {"id": r.id, "name": r.name, "cik": r.cik, "ticker": r.ticker}
                    for r in result.all()
                ]
        except Exception as exc:
            self.log.error("EDGAR: load companies error: %s", exc)
            return []
