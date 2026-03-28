# ORACLE Scraper Phase S3 — Geo Intelligence Scrapers
# Run AFTER Phase S2 is complete and pushed.

## Pre-conditions
- Phase S2 complete and pushed
- All social scrapers registered and tested

## What This Phase Builds
9 geo intelligence scrapers — these are the most exotic signals in ORACLE.
They provide leading indicators invisible to competitors who only scrape filings.

Priority order (by signal value and implementation difficulty):
1. Municipal Permits — public open data, easy, high signal for real estate/construction law
2. OpenSky (corporate jets) — free API, high signal for M&A due diligence detection
3. Lobbyist Registry — public data, high signal for regulatory/government relations mandates
4. WSIB — Workers compensation claims, signal for employment law mandates
5. Labour Relations Board — strikes, arbitrations, signal for employment law
6. CRA Liens — tax liens, signal for insolvency and tax law mandates
7. CBSA Trade — cross-border trade data, signal for trade law mandates
8. DBRS Morningstar — credit rating changes, signal for finance/restructuring mandates
9. Dark Web Monitor — data breach detection, signal for privacy/cybersecurity mandates

---

## LOCKED RULES
- httpx only for HTTP
- All sources are public or free-tier APIs — no paid APIs in this phase except DBRS
- rate_limit_rps: 0.2 for government sites, 0.5 for open APIs
- English only — skip French records
- Return [] on failure — never raise
- For open data portals (CKAN): use the CKAN API where available

---

## SCRAPER 1 — Municipal Permits

File: `backend/app/scrapers/geo/municipal_permits.py` (replace stub)

### Data sources
Three Canadian cities with open data portals (CKAN):
- Toronto: https://open.toronto.ca/dataset/building-permits-cleared/ (CKAN API)
- Vancouver: https://opendata.vancouver.ca/explore/dataset/issued-building-permits/ (Socrata API)
- Calgary: https://data.calgary.ca/Business-and-Economic-Activity/Building-Permits/ (CKAN)

### What to extract
- Permit value (high-value permits = construction activity = real estate/construction law signal)
- Permit type (demolition = distress signal, new construction = M&A signal)
- Applicant name (company name)
- Address (jurisdiction signal)
- Issue date

### Signal logic
- Permit value > $10M → signal_type = "geo_permit_major_construction"
- Permit type = "demolition" → signal_type = "geo_permit_demolition"
- Applicant is known company → match to company database

```python
_TORONTO_PERMITS_API = "https://ckan0.cf.opendata.inter.prod-toronto.ca/api/3/action/datastore_search"
_TORONTO_RESOURCE_ID = "7ac3e86d-1b9b-43aa-8c2e-4e72f4d2ca8c"  # verify this ID

@register
class MunicipalPermitsScraper(BaseScraper):
    source_id = "geo_municipal"
    source_name = "Municipal Building Permits (Toronto/Vancouver/Calgary)"
    signal_types = ["geo_permit_major_construction", "geo_permit_demolition", "geo_permit_issued"]
    CATEGORY = "geo"
    rate_limit_rps = 0.3
    concurrency = 1
    requires_auth = False

    async def scrape(self) -> list[ScraperResult]:
        results = []
        results.extend(await self._scrape_toronto())
        results.extend(await self._scrape_vancouver())
        return results

    async def _scrape_toronto(self) -> list[ScraperResult]:
        """Toronto Open Data CKAN API."""
        data = await self.get_json(
            _TORONTO_PERMITS_API,
            params={
                "resource_id": _TORONTO_RESOURCE_ID,
                "limit": 100,
                "filters": json.dumps({"STATUS": "Issued"}),
                # Add date filter for last 30 days
            }
        )
        if not data or not data.get("success"):
            return []
        records = data.get("result", {}).get("records", [])
        return [r for r in [self._parse_toronto_permit(rec) for rec in records] if r]

    def _parse_toronto_permit(self, rec: dict) -> ScraperResult | None:
        value = float(rec.get("ESTIMATED_CONST_COST", 0) or 0)
        if value < 1_000_000:  # Skip small permits
            return None
        company = rec.get("APPLICANT", "") or rec.get("OWNER", "")
        permit_type = rec.get("PERMIT_TYPE", "")
        signal_type = "geo_permit_demolition" if "demolition" in permit_type.lower() else "geo_permit_major_construction"
        return ScraperResult(
            source_id=self.source_id,
            source_name=self.source_name,
            signal_type=signal_type,
            company_name=company,
            title=f"Building permit: {company} — ${value:,.0f}",
            summary=f"{permit_type} permit issued in Toronto for {company}",
            source_url=f"https://open.toronto.ca/dataset/building-permits-cleared/",
            published_at=self._parse_date(rec.get("ISSUED_DATE")),
            raw_payload=rec,
            practice_area_hints=["real_estate", "construction", "environmental"],
            confidence=0.6,
        )
```

---

## SCRAPER 2 — OpenSky (Corporate Jets)

File: `backend/app/scrapers/geo/opensky.py` (replace stub)

### API reference
OpenSky REST API (free, no auth required for basic queries):
https://opensky-network.org/api/states/all

For corporate jet tracking, filter by:
- aircraft_type: large business jets (Gulfstream, Bombardier, Dassault)
- origin_airport / destination_airport: major Canadian business hubs
  - CYYZ (Toronto Pearson), CYVR (Vancouver), CYYC (Calgary)

### What it signals
Corporate jet travel patterns are M&A due diligence proxies:
- Unusual flight from city A (known company HQ) to city B (target company location)
- Cluster of corporate jets at same destination
- Repeated flights between same city pair within 1 week

```python
_OPENSKY_API = "https://opensky-network.org/api/states/all"
_CANADIAN_HUB_AIRPORTS = ["CYYZ", "CYVR", "CYYC", "CYUL", "CYWG"]

# Business jet ICAO type codes (partial list)
_BIZJET_TYPES = ["GL5T", "GL6T", "GLEX", "G650", "F2TH", "C56X", "C680", "C750"]

@register
class OpenSkyScraper(BaseScraper):
    source_id = "geo_opensky"
    source_name = "OpenSky Network (Corporate Flight Tracking)"
    signal_types = ["geo_flight_corporate_jet", "geo_executive_travel"]
    CATEGORY = "geo"
    rate_limit_rps = 0.1  # OpenSky rate limit: 400 calls/day anonymous
    concurrency = 1
    requires_auth = False

    async def scrape(self) -> list[ScraperResult]:
        # Query flights arriving at/departing Canadian hub airports
        # Filter for business jet aircraft types
        # Group by origin/destination pair
        # Flag unusual patterns (same pair 3+ times in 7 days)
        ...
```

Signal value: MEDIUM-HIGH. OpenSky is free, publicly available, and provides early M&A signals that are completely invisible to competitors scraping public filings.

---

## SCRAPER 3 — Lobbyist Registry

File: `backend/app/scrapers/geo/lobbyist_registry.py` (replace stub)

### Data sources
- Federal: https://lobbycanada.gc.ca/app/secure/ocl/lrs/do/cmmns (has data download)
- Ontario: https://www.ontario.ca/page/lobbyist-registry (search)
- BC: https://www.lobbyistregistrar.bc.ca/

### What to extract
- Registrant organization (company name)
- Subject matter of lobbying (=practice area signal)
- Government institution being lobbied
- Registration/renewal date

Signal value: HIGH for regulatory and government relations mandates.
A company registering lobbyists in Ottawa for "financial regulations" → predict banking/regulatory mandate.

---

## SCRAPER 4 — WSIB

File: `backend/app/scrapers/geo/wsib.py` (replace stub)

Data source: https://www.wsib.ca/en/businesses/rates-and-premiums/experience-rating
WSIB does not publish claims data publicly. Implementation options:
a) Scrape WSIB's published "schedule of penalties" for violations
b) If no public data: implement as documented stub with clear comment explaining why

Check: https://www.wsib.ca/en/about-wsib/news-and-events/news-releases
Parse news releases for company names and enforcement actions.

---

## SCRAPER 5 — Labour Relations Board

File: `backend/app/scrapers/geo/labour_relations.py` (replace stub)

### Data sources
- Ontario LRB: https://www.olrb.gov.on.ca/decisions (decisions database)
- Federal CIRB: https://cirb-ccri.gc.ca/en/decisions/

### What to extract
- Company name (respondent)
- Decision type (certification, unfair labour practice, strike vote)
- Decision date
- Practice area: employment_labour

Signal value: HIGH for employment/labour law mandates.
A union certification application against a company = predict employment law mandate within 60-90 days.

---

## SCRAPER 6 — CRA Liens

File: `backend/app/scrapers/geo/cra_liens.py` (replace stub)

CRA does not publish a public lien registry. 
Research: Is there any public mechanism to find CRA liens?
- Provincial land registries (Ontario Parcel Register) record CRA liens
- PPSA (Personal Property Security Act) registries

If no accessible public source: implement as documented stub.
Comment must explain: "CRA lien data requires provincial PPSA registry access — not publicly queryable via web. Future implementation requires Teranet or equivalent API partnership."

---

## SCRAPER 7 — CBSA Trade

File: `backend/app/scrapers/geo/cbsa_trade.py` (replace stub)

Data source: https://www.cbsa-asfc.gc.ca/trade-commerce/menu-eng.html
CBSA's Advance Ruling program publishes some decisions publicly.
Also: Statistics Canada publishes aggregate trade data by commodity.

Signal value: MEDIUM for trade law mandates (anti-dumping, customs disputes).

---

## SCRAPER 8 — DBRS Morningstar

File: `backend/app/scrapers/geo/dbrs.py` (replace stub)

### Data source
DBRS Morningstar rating actions: https://dbrs.morningstar.com/research
Note: Full data requires paid subscription. Check if rating actions are publicly listed.

If public rating action page exists: scrape company name, rating change, date.
If paywalled: implement documented stub with note: "DBRS full data requires paid subscription. Free tier shows only recent highlights."

Signal value: HIGH for banking/finance and restructuring mandates.
A credit rating downgrade → predict restructuring, refinancing, or insolvency mandate within 90 days.

---

## SCRAPER 9 — Dark Web Monitor

File: `backend/app/scrapers/geo/dark_web.py` (replace stub)

### Important caveat
Dark web monitoring requires either:
a) A paid breach intelligence service (HaveIBeenPwned API, SpyCloud, etc.)
b) Monitoring specific dark web forums (legally and technically complex)

### Recommended implementation
Use the free HaveIBeenPwned API (HIBP) which monitors breach dumps:
- API: https://haveibeenpwned.com/API/v3
- Free tier: can query domains for breaches
- API key: required ($3.50/month)

```python
_HIBP_BREACHES = "https://haveibeenpwned.com/api/v3/breaches"

@register
class DarkWebMonitorScraper(BaseScraper):
    source_id = "geo_dark_web"
    source_name = "HaveIBeenPwned (Breach Monitor)"
    signal_types = ["geo_data_breach_detected"]
    CATEGORY = "geo"
    rate_limit_rps = 0.05
    concurrency = 1
    requires_auth = True  # HIBP API key required

    async def scrape(self) -> list[ScraperResult]:
        settings = get_settings()
        if not settings.hibp_api_key:
            log.info("dark_web_skipped_no_api_key")
            return []
        # Fetch all known breaches
        # Cross-reference against companies in our database by domain name
        # Return matches
```

Signal value: HIGH for privacy/cybersecurity mandates.
A data breach → predict privacy law mandate within 30 days (mandatory breach notification).

---

## TESTS FOR PHASE S3

File: `tests/scrapers/test_phase_s3_geo.py`

```python
async def test_municipal_permits_toronto_returns_results():
    # Mock CKAN API response with permits > $1M
    # Assert: results have correct signal_type
    # Assert: small permits (< $1M) filtered out

async def test_municipal_permits_returns_empty_on_api_failure():
    # Mock get_json returns None
    # Assert: returns []

async def test_opensky_scraper_instantiates():
    from app.scrapers.geo.opensky import OpenSkyScraper
    scraper = OpenSkyScraper()
    assert scraper.source_id == "geo_opensky"

async def test_dark_web_scraper_skips_without_api_key():
    # Settings with no hibp_api_key
    # Assert: returns [] without making HTTP call

async def test_all_geo_scrapers_registered():
    from app.scrapers.registry import ScraperRegistry
    registry = ScraperRegistry.all_by_category("geo")
    source_ids = [s.source_id for s in registry]
    required = [
        "geo_municipal", "geo_opensky", "geo_lobbyist",
        "geo_wsib", "geo_labour_relations", "geo_dark_web",
        "geo_cbsa_trade", "geo_dbrs",
    ]
    for sid in required:
        assert sid in source_ids, f"Missing geo scraper: {sid}"
```

SUCCESS CRITERIA for Phase S3:
- Municipal permits: parses Toronto CKAN API, filters < $1M permits
- OpenSky: instantiates, hits API (real or mocked), parses aircraft data
- Lobbyist registry: extracts company + subject matter
- WSIB, CRA, CBSA: real implementation OR clearly documented stub (no silent empty stubs)
- Dark web: HIBP integration with API key guard
- All registered in ScraperRegistry
- `pytest tests/scrapers/test_phase_s3_geo.py` → 0 failures
- git commit and push

---

## PHASE S3 COMPLETION CHECKLIST
- [ ] Research done for each source before implementing (curl + read response)
- [ ] Municipal permits: Toronto + Vancouver CKAN APIs working
- [ ] OpenSky: aircraft filtering and corporate jet detection logic
- [ ] Lobbyist registry: at least federal registry parsed
- [ ] WSIB/CRA: real implementation or properly documented stub (not silent [])
- [ ] DBRS: real implementation or properly documented stub
- [ ] Dark web: HIBP integration with key guard
- [ ] hibp_api_key added to Settings + .env.example
- [ ] Tests written and passing
- [ ] git commit -m "feat(scrapers): implement geo intelligence scrapers — permits, opensky, lobbyist, wsib, labour, dark web, cbsa, dbrs"
- [ ] git push origin main
