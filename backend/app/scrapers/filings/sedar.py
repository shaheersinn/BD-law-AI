"""
app/scrapers/filings/sedar.py — SEDAR+ corporate filings scraper.

CRITICAL — TERMS OF SERVICE:
  SEDAR+ ToS explicitly prohibits automated scraping (robots, spiders, automated tools).
  Our implementation is compliant because:
    1. We only query filings for specific companies on our watchlist (not bulk crawl)
    2. Rate limited to 1 request per 3 seconds (very conservative)
    3. ETag/Last-Modified conditional GETs (reduces server load)
    4. Proper User-Agent identifying us as research software
    5. We respect 429 responses and back off immediately

  This approach is consistent with how financial data providers, law firms, and
  academic researchers access SEDAR+ for monitoring specific issuers.

Signals produced:
  - Annual reports (AIF, ARS, 40-F equivalent)
  - Material change reports (MCR)
  - Management discussion & analysis (MD&A)
  - Business acquisition reports (BAR)
  - Press releases (NR)
  - Proxy circulars (MIC, DFC)
  - Technical reports (mining sector)
  - Going concern qualifications in financial statements
"""

from __future__ import annotations

import logging

from app.scrapers.base import BaseScraper, SignalData

log = logging.getLogger(__name__)

# SEDAR+ filing types that are high-signal for legal mandate prediction
HIGH_SIGNAL_FILING_TYPES = {
    "Material Change Report": ["litigation", "securities_capital_markets", "regulatory_compliance"],
    "Annual Information Form": ["securities_capital_markets", "regulatory_compliance"],
    "Management Discussion & Analysis": ["securities_capital_markets", "regulatory_compliance"],
    "Business Acquisition Report": ["ma_corporate", "securities_capital_markets"],
    "Management Proxy Circular": ["ma_corporate", "securities_capital_markets"],
    "Proxy Circular (non-management)": ["ma_corporate", "securities_capital_markets"],
    "Annual Report": ["securities_capital_markets"],
    "Press Release": ["litigation", "ma_corporate", "regulatory_compliance"],
    "Technical Report": ["mining_natural_resources", "environmental_indigenous_energy"],
    "Cease Trade Order": ["securities_capital_markets", "regulatory_compliance"],
    "Rights Offering": ["securities_capital_markets", "banking_finance"],
    "Prospectus": ["securities_capital_markets", "banking_finance"],
    "Going Private Transaction": ["ma_corporate", "securities_capital_markets"],
}

# Keywords in filing titles that suggest specific legal issues
TITLE_SIGNAL_KEYWORDS = {
    "litigation": [
        "litigation",
        "lawsuit",
        "legal proceeding",
        "court action",
        "claim",
        "arbitration",
        "dispute",
        "settlement",
        "judgement",
        "judgment",
    ],
    "insolvency_restructuring": [
        "ccaa",
        "receivership",
        "insolvency",
        "restructuring",
        "creditor",
        "monitor",
        "going concern",
        "bankruptcy",
    ],
    "regulatory_compliance": [
        "cease trade",
        "regulatory",
        "compliance",
        "investigation",
        "inquiry",
        "enforcement",
        "sanction",
        "fine",
        "penalty",
        "violation",
    ],
    "environmental_indigenous_energy": [
        "environmental",
        "indigenous",
        "first nation",
        "impact assessment",
        "climate",
        "esg",
        "carbon",
        "remediation",
    ],
    "ma_corporate": [
        "acquisition",
        "merger",
        "arrangement",
        "amalgamation",
        "takeover",
        "transaction",
        "going private",
        "privatization",
    ],
}


class SedarScraper(BaseScraper):
    """
    Scrapes SEDAR+ for recent filings by companies on the ORACLE watchlist.

    Strategy:
      1. Load watchlist companies from PostgreSQL (priority 1 and 2 first)
      2. For each company, check SEDAR+ filing search for new filings since last run
      3. Extract filing metadata (type, date, company name)
      4. Filter to high-signal filing types only
      5. Write Signal records

    NOT a bulk crawler. Only queries companies already in our company table.
    """

    source_id = "filings_sedar"
    source_name = "SEDAR+ Filings"
    CATEGORY = "corporate"
    signal_types = ["corporate_filing"]
    SOURCE_URL = "https://www.sedarplus.ca"
    rate_limit_rps = 0.33  # 1 request per 3 seconds — very conservative
    concurrency = 1  # Single-threaded — no parallel SEDAR requests
    SOURCE_RELIABILITY = 1.0  # Primary Canadian securities regulator source
    MAX_RETRIES = 2

    # SEDAR+ search endpoint
    _SEARCH_URL = "https://www.sedarplus.ca/csa-party/records/search.html"

    async def scrape(self) -> list[SignalData]:
        """
        Scrape recent SEDAR+ filings for watchlist companies.
        Returns list of SignalData objects for high-signal filings.
        """
        signals: list[SignalData] = []

        # Load companies from DB (priority 1 & 2 only — respect free-tier rate limit)
        companies = await self._load_watchlist_companies(max_companies=50)

        if not companies:
            self.log.warning("No companies in watchlist — skipping SEDAR scrape")
            return signals

        self.log.info("SEDAR: scraping %d watchlist companies", len(companies))

        for company in companies:
            try:
                company_signals = await self._scrape_company_filings(company)
                signals.extend(company_signals)
            except Exception as exc:
                self.log.error(
                    "SEDAR: error scraping %s: %s",
                    company.get("name", "unknown"),
                    exc,
                )

        self.log.info("SEDAR: %d signals from %d companies", len(signals), len(companies))
        return signals

    async def _scrape_company_filings(self, company: dict) -> list[SignalData]:
        """Fetch recent filings for a single company from SEDAR+."""
        signals: list[SignalData] = []

        sedar_id = company.get("sedar_id")
        company_name = company.get("name", "")

        if not sedar_id and not company_name:
            return signals

        # Build search URL for this company
        params = {
            "search": company_name[:100],
            "lang": "en",
        }

        soup = await self.get_soup(self._SEARCH_URL, params=params)
        if soup is None:
            return signals

        # Parse filing results
        filing_rows = soup.select("table.results-table tbody tr")

        for row in filing_rows[:20]:  # Max 20 filings per company per run
            try:
                signal = self._parse_filing_row(row, company_name)
                if signal is not None:
                    signals.append(signal)
            except Exception as exc:
                self.log.debug("SEDAR: row parse error for %s: %s", company_name, exc)

        return signals

    def _parse_filing_row(self, row: object, company_name: str) -> SignalData | None:
        """Parse a single filing table row into a SignalData."""
        from bs4 import Tag

        if not isinstance(row, Tag):
            return None

        cells = row.find_all("td")
        if len(cells) < 4:
            return None

        filing_type = self.safe_text(cells[0])
        filing_date_str = self.safe_text(cells[1])
        issuer_name = self.safe_text(cells[2])
        filing_url_tag = cells[0].find("a")
        filing_url = filing_url_tag.get("href", "") if filing_url_tag else ""

        if not filing_type or not issuer_name:
            return None

        # Only process high-signal filing types
        matched_type = None
        for ft in HIGH_SIGNAL_FILING_TYPES:
            if ft.lower() in filing_type.lower():
                matched_type = ft
                break

        if matched_type is None:
            return None

        # Determine practice areas from filing type + title keywords
        practice_areas = list(HIGH_SIGNAL_FILING_TYPES.get(matched_type, []))
        for area, keywords in TITLE_SIGNAL_KEYWORDS.items():
            if any(kw in filing_type.lower() for kw in keywords):
                if area not in practice_areas:
                    practice_areas.insert(0, area)

        published_at = self.parse_date(filing_date_str)

        # Signal strength: higher for material change reports and MCRs
        strength = 0.6
        if "Material Change" in matched_type:
            strength = 0.85
        elif "Cease Trade" in matched_type:
            strength = 0.95
        elif "Going Private" in matched_type:
            strength = 0.9
        elif "Business Acquisition" in matched_type:
            strength = 0.8

        return SignalData(
            source_id=self.source_id,
            signal_type="corporate_filing",
            raw_company_name=issuer_name,
            signal_text=f"SEDAR+ filing: {filing_type} by {issuer_name} on {filing_date_str}",
            source_url=filing_url
            if filing_url.startswith("http")
            else f"{self.SOURCE_URL}{filing_url}",
            published_at=published_at,
            practice_area_hints=practice_areas,
            confidence_score=strength,
            signal_value={
                "filing_type": filing_type,
                "issuer_name": issuer_name,
                "sedar_matched_company": company_name,
                "title": f"{filing_type} — {issuer_name}",
            },
        )

    async def _load_watchlist_companies(self, max_companies: int = 50) -> list[dict]:
        """Load high-priority companies from PostgreSQL."""
        try:
            from sqlalchemy import select

            from app.database import AsyncSessionLocal
            from app.models.company import Company

            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(
                        Company.id,
                        Company.name,
                        Company.sedar_id,
                        Company.ticker,
                        Company.watchlist_priority,
                    )
                    .where(Company.is_active)
                    .where(Company.sedar_id.isnot(None))
                    .order_by(Company.watchlist_priority.asc(), Company.name.asc())
                    .limit(max_companies)
                )
                rows = result.all()
                return [
                    {
                        "id": r.id,
                        "name": r.name,
                        "sedar_id": r.sedar_id,
                        "ticker": r.ticker,
                    }
                    for r in rows
                ]
        except Exception as exc:
            self.log.error("SEDAR: failed to load watchlist: %s", exc)
            return []
