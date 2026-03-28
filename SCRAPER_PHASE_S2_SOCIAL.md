# ORACLE Scraper Phase S2 — Social Scrapers
# Run AFTER Phase S1 is complete and pushed.

## Pre-conditions
- Phase S1 complete and pushed
- All 9 regulatory scrapers registered and tested
- API keys confirmed available in environment:
  - REDDIT_CLIENT_ID + REDDIT_CLIENT_SECRET (OAuth2)
  - TWITTER_BEARER_TOKEN (API v2 Basic tier)
  - PROXYCURL_API_KEY (LinkedIn — 10 free credits/month)
  - STOCKHOUSE_API_KEY (if required — check if public)

## What This Phase Builds
5 social scrapers currently returning []:
1. Reddit — r/legaladvicecanada, r/PersonalFinanceCanada, r/canada, r/investing, r/CanadianInvestor
2. Twitter/X — replace existing stub with full implementation from root twitter_x.py
3. LinkedIn Social — executive departures via Proxycurl
4. Stockhouse — Canadian retail investor forum (bearish signals)
5. SEDAR Forums — if applicable

Important note on priority: Reddit > Stockhouse > Twitter > LinkedIn (by data access ease and cost)

---

## LOCKED RULES
- httpx only — never requests library
- API keys from settings (get_settings()) — never hardcoded
- Rate limits: strict — Twitter is 10k tweets/month on Basic tier
- Return [] on any auth failure — do NOT raise, do NOT log the key
- store raw_payload in MongoDB (NLP features read from here)
- English only — skip non-English posts

---

## SCRAPER 1 — Reddit

File: `backend/app/scrapers/social/reddit.py` (replace stub)

### API Reference
Reddit OAuth2 — no official Python SDK needed, httpx works fine.
Auth endpoint: https://www.reddit.com/api/v1/access_token
Search endpoint: https://oauth.reddit.com/r/{subreddit}/search.json

### Pre-implementation research
1. Read Reddit API rate limits: https://www.reddit.com/dev/api/
2. Free tier: 60 requests/minute with OAuth2
3. Search params: q=query, sort=new, time=week, limit=25, restrict_sr=true

### Target subreddits and queries
```python
_SUBREDDITS_QUERIES = [
    # (subreddit, query, signal_type, practice_area_hints)
    ("legaladvicecanada", "lawsuit OR litigation OR fired OR wrongful", "social_reddit_legal", ["litigation", "employment"]),
    ("legaladvicecanada", "CCAA OR receivership OR bankruptcy OR insolvency", "social_reddit_legal", ["insolvency"]),
    ("PersonalFinanceCanada", "lawsuit OR class action OR settlement", "social_reddit_legal", ["litigation"]),
    ("canada", "regulatory fine OR enforcement OR securities fraud", "social_reddit_regulatory", ["regulatory", "securities"]),
    ("investing", "SEC OR OSC OR enforcement OR fraud TSX", "social_reddit_regulatory", ["securities"]),
    ("CanadianInvestor", "lawsuit OR investigation OR class action TSX", "social_reddit_legal", ["litigation", "securities"]),
]
```

### Implementation skeleton
```python
@register
class RedditScraper(BaseScraper):
    source_id = "social_reddit"
    source_name = "Reddit"
    signal_types = ["social_reddit_legal", "social_reddit_regulatory"]
    CATEGORY = "social"
    rate_limit_rps = 0.5
    concurrency = 2
    requires_auth = True

    async def scrape(self) -> list[ScraperResult]:
        token = await self._get_oauth_token()
        if not token:
            log.warning("reddit_auth_failed")
            return []

        results = []
        for subreddit, query, signal_type, hints in _SUBREDDITS_QUERIES:
            posts = await self._search_subreddit(token, subreddit, query)
            for post in posts:
                result = self._build_result(post, signal_type, hints)
                if result:
                    results.append(result)
        return results

    async def _get_oauth_token(self) -> str | None:
        settings = get_settings()
        if not settings.reddit_client_id or not settings.reddit_client_secret:
            return None
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://www.reddit.com/api/v1/access_token",
                data={"grant_type": "client_credentials"},
                auth=(settings.reddit_client_id, settings.reddit_client_secret),
                headers={"User-Agent": "ORACLE-BD-Intelligence/1.0"},
            )
            if resp.status_code == 200:
                return resp.json().get("access_token")
        return None
```

### Config additions needed
Add to `backend/app/config.py` Settings class:
```python
reddit_client_id: str = ""
reddit_client_secret: str = ""
twitter_bearer_token: str = ""
proxycurl_api_key: str = ""
stockhouse_api_key: str = ""
```

Add to `.env.example`:
```
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret
TWITTER_BEARER_TOKEN=your_twitter_bearer_token
PROXYCURL_API_KEY=your_proxycurl_api_key
```

---

## SCRAPER 2 — Twitter/X

File: `backend/app/scrapers/social/twitter.py` (already migrated from root in master prompt — verify and expand)

### Verify migration was done
The master prompt migrated `scrapers/social/twitter_x.py` → `backend/app/scrapers/social/twitter.py`
Check: does `backend/app/scrapers/social/twitter.py` have the 5 search queries and real API URL?

If NOT migrated (master prompt may have left a stub):
Copy the implementation from root `scrapers/social/twitter_x.py` — it has:
- `_TWITTER_SEARCH = "https://api.twitter.com/2/tweets/search/recent"`
- 5 `_SEARCH_QUERIES` tuples for Canadian legal signals
- Real API call with Bearer token auth

### Expand the existing implementation
Add pagination support (next_token from Twitter response).
Add company name extraction from tweet text.
Add SEDAR ticker detection (TSX: XXXX pattern).

```python
_SEARCH_QUERIES = [
    ("lawsuit OR litigation OR \"class action\" OR \"cease trade\" lang:en -is:retweet", "social_twitter_legal", ["litigation"]),
    ("CCAA OR receivership OR insolvency OR bankruptcy lang:en -is:retweet", "social_twitter_distress", ["insolvency"]),
    ("TSX OR TSXV SEC enforcement penalty investigation fraud lang:en", "social_twitter_regulatory", ["securities"]),
    ("\"data breach\" OR \"privacy violation\" Canada lang:en", "social_twitter_legal", ["privacy_data"]),
    ("merger acquisition \"hostile bid\" \"going private\" TSX lang:en", "social_twitter_ma", ["ma"]),
]
```

Rate limit awareness: 10,000 tweets/month on Basic tier.
Implement a monthly counter in Redis. When counter > 9,000: stop scraping and log warning.
```python
async def _check_monthly_budget(self) -> bool:
    """Return False if monthly tweet budget is exhausted."""
    from app.cache.client import cache
    key = f"twitter_monthly_count:{datetime.now(tz=UTC).strftime('%Y-%m')}"
    count = await cache.get(key) or 0
    if int(count) >= 9000:
        log.warning("twitter_monthly_budget_exhausted", count=count)
        return False
    return True
```

---

## SCRAPER 3 — LinkedIn (Proxycurl)

File: `backend/app/scrapers/social/linkedin_social.py` (replace stub with root implementation)

### Verify migration
Master prompt migrated root `scrapers/social/linkedin.py` → `backend/app/scrapers/social/linkedin_social.py`
Verify the file has the Proxycurl API URL and exec departure detection logic.

### Key constraints
- 10 free Proxycurl credits/month — EXTREMELY conservative usage
- Only query for target companies in watchlist (not all companies)
- Cache Proxycurl responses in Redis for 30 days

```python
_PROXYCURL_EMPLOYEES = "https://nubela.co/proxycurl/api/v2/linkedin/company/employees/"

@register
class LinkedInSocialScraper(BaseScraper):
    source_id = "social_linkedin"
    source_name = "LinkedIn (Proxycurl)"
    signal_types = ["social_linkedin_exec_departure", "social_linkedin_legal_hire"]
    CATEGORY = "social"
    rate_limit_rps = 0.05  # 10 credits/month = ~0.0003 rps sustained
    concurrency = 1
    requires_auth = True

    async def scrape(self) -> list[ScraperResult]:
        settings = get_settings()
        if not settings.proxycurl_api_key:
            log.info("linkedin_skipped_no_api_key")
            return []
        # Only scrape top watchlist companies
        # Fetch from PostgreSQL: SELECT linkedin_url FROM companies
        #   WHERE priority_tier = 1 AND linkedin_url IS NOT NULL LIMIT 5
        ...
```

---

## SCRAPER 4 — Stockhouse

File: `backend/app/scrapers/social/stockhouse.py` (replace stub)

Data source: https://stockhouse.com/bullboards
Approach: HTML scraping (Stockhouse has no official API)
Target: Canadian public companies with bearish sentiment or legal mentions

```python
_STOCKHOUSE_SEARCH = "https://stockhouse.com/search?q={ticker}&type=bullboard"
# Search for legal keywords in recent posts

@register
class StockhouseScraper(BaseScraper):
    source_id = "social_stockhouse"
    source_name = "Stockhouse Bullboards"
    signal_types = ["social_stockhouse_bear", "social_stockhouse_legal"]
    CATEGORY = "social"
    rate_limit_rps = 0.1
    concurrency = 1
    requires_auth = False

    _BEAR_KEYWORDS = [
        "lawsuit", "class action", "fraud", "investigation",
        "cease trade", "receivership", "insolvency", "regulatory",
        "SEC", "OSC", "BCSC", "going concern"
    ]
```

Approach: Fetch top TSX companies' Stockhouse bullboard pages. Search post text for bear keywords. Extract company name from ticker. Build ScraperResult for each matching post.

---

## SCRAPER 5 — SEDAR Forums (if applicable)

File: `backend/app/scrapers/social/sedar_forums.py`

Check if SEDAR+ has any public discussion/forum component.
If not: implement as a stub that logs "SEDAR forums not available" and returns [].
Do not waste implementation time on a source that doesn't exist.

---

## TESTS FOR PHASE S2

File: `tests/scrapers/test_phase_s2_social.py`

```python
async def test_reddit_scraper_returns_results_with_valid_oauth():
    # Mock: OAuth token endpoint returns valid token
    # Mock: Reddit search endpoint returns posts with legal keywords
    # Assert: results have correct signal_type and practice_area_hints

async def test_reddit_scraper_returns_empty_on_auth_failure():
    # Mock: OAuth endpoint returns 401
    # Assert: returns [] without raising

async def test_twitter_scraper_has_5_search_queries():
    from app.scrapers.social.twitter import _SEARCH_QUERIES
    assert len(_SEARCH_QUERIES) == 5

async def test_twitter_monthly_budget_check_blocks_at_9000():
    # Mock Redis count = 9001
    # Assert: scraper returns [] without calling Twitter API

async def test_linkedin_scraper_skips_when_no_api_key():
    # Settings with no proxycurl_api_key
    # Assert: returns [] without making HTTP call

async def test_stockhouse_scraper_filters_bear_keywords():
    # Mock HTML with posts containing "lawsuit" and "class action"
    # Assert: both posts in results with correct signal type

async def test_all_social_scrapers_registered():
    from app.scrapers.registry import ScraperRegistry
    registry = ScraperRegistry.all_by_category("social")
    source_ids = [s.source_id for s in registry]
    for sid in ["social_reddit", "social_twitter", "social_linkedin", "social_stockhouse"]:
        assert sid in source_ids, f"Missing: {sid}"
```

SUCCESS CRITERIA for Phase S2:
- Reddit scraper: returns results when mocked OAuth succeeds, [] when it fails
- Twitter scraper: has real search queries (not stub), monthly budget check works
- LinkedIn scraper: skips gracefully when no API key
- Stockhouse scraper: bear keyword filtering works
- All 4 registered in ScraperRegistry
- `pytest tests/scrapers/test_phase_s2_social.py` → 0 failures
- Config additions (reddit/twitter/proxycurl env vars) documented in .env.example

---

## PHASE S2 COMPLETION CHECKLIST
- [ ] Config env vars added to Settings class and .env.example
- [ ] Reddit: full OAuth2 + search implementation
- [ ] Twitter: full implementation (verify migration from root, expand)
- [ ] LinkedIn: Proxycurl implementation with credit budget guard
- [ ] Stockhouse: HTML scraping with bear keyword filter
- [ ] SEDAR forums: assess and stub or implement
- [ ] Unit tests written and passing
- [ ] No API keys hardcoded anywhere
- [ ] Monthly Twitter budget counter implemented in Redis
- [ ] git commit -m "feat(scrapers): implement social scrapers — Reddit, Twitter, LinkedIn, Stockhouse"
- [ ] git push origin main
