# ORACLE Scraper Phase S1 — Regulatory Scrapers
# Run AFTER the master cleanup prompt is complete and pushed.

## Pre-conditions (verify before starting)
- Master prompt cleanup is complete and pushed to main
- `grep -r "anthropic" backend/ --include="*.py"` returns zero
- `pytest --tb=short` passes
- `python -c "from app.main import app"` succeeds

## What This Phase Builds
9 regulatory scrapers that are currently empty stubs returning [].
These are your HIGHEST SIGNAL sources for BigLaw BD — regulatory enforcement
actions directly predict mandate probability for litigation, securities,
regulatory, privacy, and competition practice areas.

Priority order (build in this sequence):
1. OSC — Ontario Securities Commission (highest Canadian signal)
2. OSFI — Office of Superintendent of Financial Institutions
3. BCSC — BC Securities Commission
4. ASC — Alberta Securities Commission
5. FSRA — Financial Services Regulatory Authority of Ontario
6. CRTC — Canadian Radio-television and Telecommunications Commission
7. OPC — Office of the Privacy Commissioner
8. US DOJ — United States Department of Justice (cross-border M&A signal)
9. SEC AAER — SEC Accounting and Auditing Enforcement Releases

---

## LOCKED RULES (same as master prompt — no exceptions)
- httpx only — never requests library
- asyncpg for DB — never sync SQLAlchemy in async context
- get_soup(), get_json(), get_rss() helpers from BaseScraper — use them
- rate_limit_rps: government sites max 0.2 rps — be respectful
- All scrapers inherit BaseScraper, use @register decorator
- Return list[ScraperResult] — never raise, return [] on failure
- structlog only — never print() or logging.info()
- English only — skip French-language records entirely
- Store signals to BOTH PostgreSQL (Signal model) and MongoDB (raw_payload)

---

## ARCHITECTURE REFERENCE

### BaseScraper contract
Every scraper must implement:
```python
@register
class MyRegulatoryScraper(BaseScraper):
    source_id = "regulatory_xxx"          # unique snake_case ID
    source_name = "Full Name"             # human-readable
    signal_types = ["regulatory_xxx"]     # list of signal type strings
    CATEGORY = "regulatory"
    rate_limit_rps = 0.2                  # max 0.2 for government sites
    concurrency = 1
    requires_auth = False                 # most regulatory sites are public

    async def scrape(self) -> list[ScraperResult]:
        results = []
        # fetch, parse, build ScraperResult objects
        return results
```

### ScraperResult fields
```python
ScraperResult(
    source_id="regulatory_osc",
    source_name="Ontario Securities Commission",
    signal_type="regulatory_enforcement",    # must match signal_types list
    company_name="Acme Corp",                # extracted company name
    company_identifier=None,                 # ticker/CIK if available
    title="OSC enforcement action against Acme Corp",
    summary="Summary of the enforcement action...",
    source_url="https://www.osc.ca/en/...",
    published_at=datetime(2024, 3, 15, tzinfo=UTC),
    raw_payload={                            # full raw data for MongoDB
        "action_type": "cease_trade",
        "penalty_amount": 50000,
        "practice_area_hints": ["securities", "litigation"],
    },
    practice_area_hints=["securities", "litigation"],  # ML routing hints
    confidence=0.9,
)
```

### Practice area hints to use per regulator
- OSC, BCSC, ASC: ["securities", "litigation", "regulatory"]
- OSFI: ["banking_finance", "regulatory", "insurance"]
- FSRA: ["insurance", "banking_finance", "regulatory"]
- CRTC: ["regulatory", "media_telecom"]
- OPC: ["privacy_data", "regulatory", "litigation"]
- US DOJ: ["litigation", "ma", "competition"]
- SEC AAER: ["securities", "litigation", "regulatory"]

---

## SCRAPER 1 — OSC (Ontario Securities Commission)

### Research first
Before writing code, fetch these URLs and read the response structure:
```
https://www.osc.ca/en/securities-law/orders-rulings-decisions
https://www.osc.ca/en/securities-law/enforcement/enforcement-notices-and-temporary-orders
```
Use: `curl -s "https://www.osc.ca/en/securities-law/enforcement/enforcement-notices-and-temporary-orders" | head -200`

OSC uses a Drupal-based CMS. Pages are HTML. No official API.
Strategy: fetch enforcement page, parse HTML with BeautifulSoup, extract:
- Action title
- Respondent company/person name
- Date
- Action type (cease trade order, settlement, temporary order)
- Link to full document

### Implementation
File: `backend/app/scrapers/regulatory/osc.py`

```python
"""
app/scrapers/regulatory/osc.py — Ontario Securities Commission scraper.

Data source: https://www.osc.ca/en/securities-law/enforcement/
Approach: HTML scraping with BeautifulSoup (no official API)
Update frequency: Daily (enforcement actions published irregularly)
Signal value: CRITICAL — OSC enforcement is direct mandate signal for
  securities litigation, regulatory defence, cease trade order work
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_OSC_ENFORCEMENT_URL = "https://www.osc.ca/en/securities-law/enforcement/enforcement-notices-and-temporary-orders"
_OSC_ORDERS_URL = "https://www.osc.ca/en/securities-law/orders-rulings-decisions"
_OSC_SETTLEMENTS_URL = "https://www.osc.ca/en/securities-law/enforcement/settlements"


@register
class OSCScraper(BaseScraper):
    source_id = "regulatory_osc"
    source_name = "Ontario Securities Commission"
    signal_types = [
        "regulatory_enforcement",
        "regulatory_cease_trade",
        "regulatory_settlement",
        "regulatory_temporary_order",
    ]
    CATEGORY = "regulatory"
    rate_limit_rps = 0.2
    concurrency = 1
    requires_auth = False

    async def scrape(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []
        cutoff = datetime.now(tz=UTC) - timedelta(days=90)

        for url, signal_type in [
            (_OSC_ENFORCEMENT_URL, "regulatory_enforcement"),
            (_OSC_SETTLEMENTS_URL, "regulatory_settlement"),
        ]:
            page_results = await self._scrape_osc_page(url, signal_type, cutoff)
            results.extend(page_results)

        log.info("osc_scrape_complete", count=len(results))
        return results

    async def _scrape_osc_page(
        self, url: str, signal_type: str, cutoff: datetime
    ) -> list[ScraperResult]:
        soup = await self.get_soup(url)
        if soup is None:
            log.warning("osc_fetch_failed", url=url)
            return []

        results = []
        # OSC lists enforcement actions in <article> or <div class="views-row"> blocks
        # Adapt selector based on actual HTML structure found during research
        items = (
            soup.find_all("article")
            or soup.find_all("div", class_="views-row")
            or soup.find_all("li", class_="views-row")
        )

        for item in items:
            try:
                result = self._parse_osc_item(item, url, signal_type, cutoff)
                if result:
                    results.append(result)
            except Exception as exc:
                log.warning("osc_parse_item_failed", error=str(exc))
                continue

        return results

    def _parse_osc_item(
        self, item: Any, base_url: str, signal_type: str, cutoff: datetime
    ) -> ScraperResult | None:
        # Extract title
        title_el = item.find(["h2", "h3", "a"])
        if not title_el:
            return None
        title = self.safe_text(title_el)
        if not title:
            return None

        # Skip French records
        if any(fr in title.lower() for fr in [" et ", " de ", " du ", " les ", " des "]):
            if not any(en in title.lower() for en in ["the", "and", "or", "of"]):
                return None

        # Extract link
        link_el = item.find("a", href=True)
        source_url = ""
        if link_el:
            href = link_el.get("href", "")
            source_url = href if href.startswith("http") else f"https://www.osc.ca{href}"

        # Extract date
        date_el = item.find(["time", "span"], class_=lambda c: c and "date" in c.lower())
        published_at: datetime | None = None
        if date_el:
            date_str = date_el.get("datetime") or self.safe_text(date_el)
            published_at = self._parse_date(date_str)

        if published_at and published_at < cutoff:
            return None

        # Extract company name from title
        company_name = self._extract_company_from_title(title)

        return ScraperResult(
            source_id=self.source_id,
            source_name=self.source_name,
            signal_type=signal_type,
            company_name=company_name,
            title=title,
            summary=f"OSC action: {title}",
            source_url=source_url,
            published_at=published_at or datetime.now(tz=UTC),
            raw_payload={
                "action_type": signal_type,
                "regulator": "OSC",
                "url": source_url,
            },
            practice_area_hints=["securities", "litigation", "regulatory"],
            confidence=0.85,
        )

    def _extract_company_from_title(self, title: str) -> str:
        """
        Extract company/respondent name from OSC enforcement action title.
        Common patterns:
          "In the Matter of Acme Corp" → "Acme Corp"
          "Temporary Order — XYZ Inc." → "XYZ Inc."
          "Settlement with John Smith" → "John Smith"
        """
        for prefix in ["In the Matter of ", "Re ", "Settlement with ", "Temporary Order — "]:
            if prefix.lower() in title.lower():
                idx = title.lower().index(prefix.lower()) + len(prefix)
                return title[idx:].split(" — ")[0].split(" and ")[0].strip()
        return title[:80]  # fallback: truncated title
```

### Quality gate for OSC scraper
```bash
python -c "
import asyncio
from app.scrapers.regulatory.osc import OSCScraper
scraper = OSCScraper()
results = asyncio.run(scraper.scrape())
print(f'OSC results: {len(results)}')
assert len(results) > 0, 'OSC returned empty — scraper is broken'
assert all(r.source_id == 'regulatory_osc' for r in results)
assert all(r.practice_area_hints for r in results)
print('PASS')
"
```

---

## SCRAPER 2 — OSFI

File: `backend/app/scrapers/regulatory/osfi_enforcement.py` (already exists — implement it)

Data source:
- https://www.osfi-bsif.gc.ca/en/guidance-guidance/regulatory-requirements-guidance/enforcement-actions
- RSS feed if available: check https://www.osfi-bsif.gc.ca/en/rss

Approach: RSS feed preferred, HTML fallback
Signal types: `["regulatory_enforcement", "regulatory_osfi_action"]`
Practice area hints: `["banking_finance", "regulatory", "insurance"]`
Rate: 0.2 rps

Key data to extract: institution name, action type, effective date, action description

---

## SCRAPER 3 — BCSC

File: `backend/app/scrapers/regulatory/bcsc.py`

Data source: https://www.bcsc.bc.ca/enforcement/enforcement-actions
Approach: HTML scraping (same pattern as OSC)
Signal types: `["regulatory_enforcement", "regulatory_cease_trade"]`
Practice area hints: `["securities", "litigation", "regulatory"]`

---

## SCRAPER 4 — ASC

File: `backend/app/scrapers/regulatory/asc.py`

Data source: https://www.albertasecurities.com/enforcement/enforcement-proceedings
Approach: HTML scraping
Signal types: `["regulatory_enforcement"]`
Practice area hints: `["securities", "litigation", "regulatory"]`

---

## SCRAPER 5 — FSRA

File: `backend/app/scrapers/regulatory/fsra.py`

Data source: https://www.fsrao.ca/enforcement/enforcement-actions
Approach: HTML scraping
Signal types: `["regulatory_enforcement", "regulatory_fsra_action"]`
Practice area hints: `["insurance", "banking_finance", "regulatory"]`

---

## SCRAPER 6 — CRTC

File: `backend/app/scrapers/regulatory/crtc.py`

Data source:
- Decisions: https://crtc.gc.ca/eng/deci.htm
- RSS: https://crtc.gc.ca/eng/rss.htm (check for enforcement-specific feed)
Approach: RSS preferred → HTML fallback
Signal types: `["regulatory_enforcement", "regulatory_crtc_decision"]`
Practice area hints: `["regulatory", "media_telecom"]`
Note: Skip French-language decisions. CRTC publishes bilingual — filter by
  checking if English version exists before parsing.

---

## SCRAPER 7 — OPC

File: `backend/app/scrapers/regulatory/opc.py`

Data source:
- Investigations: https://www.priv.gc.ca/en/opc-actions-and-decisions/investigations/
- Findings: https://www.priv.gc.ca/en/opc-actions-and-decisions/investigations/findings/
Approach: HTML scraping
Signal types: `["regulatory_enforcement", "regulatory_privacy_finding"]`
Practice area hints: `["privacy_data", "regulatory", "litigation"]`
Signal value: HIGH — OPC findings directly predict privacy law mandates

---

## SCRAPER 8 — US DOJ

File: `backend/app/scrapers/regulatory/us_doj.py`

Data source:
- Press releases: https://www.justice.gov/news (filter for Canadian companies)
- RSS: https://www.justice.gov/feeds/opa/justice-news.xml
Approach: RSS feed (DOJ publishes good RSS)
Filter criteria: Only include if Canadian company name detected in title/summary
Signal types: `["regulatory_enforcement", "regulatory_doj_action"]`
Practice area hints: `["litigation", "ma", "competition"]`
Note: DOJ RSS is well-structured — parse <title>, <description>, <pubDate>

---

## SCRAPER 9 — SEC AAER

File: `backend/app/scrapers/regulatory/sec_aaer.py`

Data source:
- AAER list: https://www.sec.gov/litigation/admin.shtml
- RSS: https://www.sec.gov/rss/litigation/admin.xml (check if exists)
Approach: HTML or RSS
Filter: only Canadian companies (look for "Canada", "TSX", "Ontario", etc. in text)
Signal types: `["regulatory_enforcement", "regulatory_sec_aaer"]`
Practice area hints: `["securities", "litigation", "regulatory"]`

---

## IMPLEMENTATION RULES FOR ALL 9 SCRAPERS

### Pre-implementation research (mandatory for each scraper)
Before writing ANY scraper code:
1. Fetch the target URL with `curl -s [URL] | head -500`
2. Identify the actual HTML structure (class names, element types)
3. Check if RSS feed exists — always prefer RSS over HTML scraping
4. Identify the date format used
5. Then write the scraper

### Error handling pattern (same for all)
```python
async def scrape(self) -> list[ScraperResult]:
    results = []
    try:
        # scraping logic
    except Exception as exc:
        log.error("scraper_failed", source=self.source_id, error=str(exc))
        return []  # never raise — return empty list
    return results
```

### Rate limiting (already handled by BaseScraper)
Do not add manual sleep() calls — rate_limit_rps handles this.
Do not override the circuit breaker logic.

### Content deduplication
The storage layer handles SHA256 dedup. Do not implement your own dedup.
Just return all results — duplicates will be filtered at storage time.

---

## TESTS FOR PHASE S1

File: `tests/scrapers/test_phase_s1_regulatory.py`

Write these tests:
```python
# All tests mock HTTP — never make real requests
import pytest
from unittest.mock import AsyncMock, patch

# For each scraper:
async def test_osc_scraper_returns_results_on_valid_html():
    # Mock get_soup to return parsed HTML with enforcement items
    # Assert: returns list[ScraperResult]
    # Assert: source_id == "regulatory_osc"
    # Assert: practice_area_hints is non-empty
    # Assert: no result has empty title

async def test_osc_scraper_returns_empty_on_fetch_failure():
    # Mock get_soup to return None
    # Assert: returns [] without raising

async def test_osc_scraper_skips_french_records():
    # Mock HTML with French-only title
    # Assert: that record is not in results

async def test_osfi_scraper_parses_rss_correctly():
    # Mock get_rss to return sample OSFI RSS data
    # Assert: results have correct signal_types

# Repeat pattern for each of the 9 scrapers

async def test_all_regulatory_scrapers_registered():
    from app.scrapers.registry import ScraperRegistry
    registry = ScraperRegistry.all_by_category("regulatory")
    source_ids = [s.source_id for s in registry]
    required = [
        "regulatory_osc", "regulatory_osfi", "regulatory_bcsc",
        "regulatory_asc", "regulatory_fsra", "regulatory_crtc",
        "regulatory_opc", "regulatory_us_doj", "regulatory_sec_aaer"
    ]
    for sid in required:
        assert sid in source_ids, f"Missing scraper: {sid}"
```

SUCCESS CRITERIA for Phase S1:
- All 9 scrapers return list[ScraperResult] (not []) when given valid mocked HTML/RSS
- All 9 scrapers return [] (not raise) when fetch fails
- All 9 scrapers are registered in ScraperRegistry
- `pytest tests/scrapers/test_phase_s1_regulatory.py` → 0 failures
- Manual smoke test on OSC (real request, no mock): returns > 0 results
- French content filter working: French-only records excluded

---

## PHASE S1 COMPLETION CHECKLIST
- [ ] Pre-implementation research done for each scraper (curl + read HTML)
- [ ] All 9 scrapers implemented with real parsing logic (no return [])
- [ ] All 9 scrapers use @register decorator
- [ ] All 9 scrapers handle fetch failure gracefully (return [], not raise)
- [ ] French content filtering in place for bilingual regulators (CRTC, OPC, OSC)
- [ ] Unit tests written and passing
- [ ] Manual smoke test on at least OSC and OPC (highest priority)
- [ ] Update HANDOFF.md: "Phase S1 complete — 9 regulatory scrapers implemented"
- [ ] git commit -m "feat(scrapers): implement 9 regulatory scrapers — OSC, OSFI, BCSC, ASC, FSRA, CRTC, OPC, DOJ, SEC AAER"
- [ ] git push origin main
