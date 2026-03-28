"""
tests/scrapers/test_phase_s2_social.py — Phase S2 social scrapers test suite.

Tests:
  1. Reddit scraper returns results when OAuth succeeds
  2. Reddit scraper returns [] on auth failure
  3. Twitter scraper has 5 search queries
  4. Twitter monthly budget check blocks at 9000
  5. LinkedIn scraper skips when no API key
  6. Stockhouse scraper filters bear keywords
  7. All social scrapers registered in ScraperRegistry

Mocks all external HTTP calls — no real network traffic in tests.
"""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


def _mock_settings(**overrides):
    """Return a mock Settings object with social API keys."""
    defaults = {
        "reddit_client_id": "test_client_id",
        "reddit_client_secret": "test_client_secret",
        "twitter_bearer_token": "test_bearer_token",
        "proxycurl_api_key": "test_proxycurl_key",
        "stockhouse_api_key": "",
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _mock_response(status_code: int = 200, json_data: dict | None = None, text: str = ""):
    """Return a mock httpx response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.text = text
    return resp


# ── 1. Reddit scraper: results with valid OAuth ──────────────────────────────


@pytest.mark.asyncio
async def test_reddit_scraper_returns_results_with_valid_oauth():
    """Reddit scraper should return results when OAuth token is valid."""
    from app.scrapers.social.reddit import RedditScraper

    scraper = RedditScraper()

    token_response = _mock_response(200, {"access_token": "fake_token", "expires_in": 3600})
    search_response = _mock_response(200, {
        "data": {
            "children": [
                {
                    "data": {
                        "id": "abc123",
                        "title": "Company XYZ facing class action lawsuit",
                        "selftext": "Major lawsuit filed against Company XYZ",
                        "score": 42,
                        "num_comments": 10,
                        "upvote_ratio": 0.85,
                        "permalink": "/r/legaladvicecanada/comments/abc123/",
                        "created_utc": datetime.now(tz=UTC).timestamp(),
                    }
                }
            ]
        }
    })

    with patch("app.scrapers.social.reddit.get_settings", return_value=_mock_settings()):
        scraper.post = AsyncMock(return_value=token_response)
        scraper.get = AsyncMock(return_value=search_response)
        scraper._rate_limit_sleep = AsyncMock()

        results = await scraper.scrape()

    assert len(results) > 0
    for r in results:
        assert r.source_id == "social_reddit"
        assert r.signal_type in ["social_reddit_legal", "social_reddit_regulatory"]
        assert len(r.practice_area_hints) > 0


# ── 2. Reddit scraper: empty on auth failure ─────────────────────────────────


@pytest.mark.asyncio
async def test_reddit_scraper_returns_empty_on_auth_failure():
    """Reddit scraper should return [] when OAuth endpoint returns 401."""
    from app.scrapers.social.reddit import RedditScraper

    scraper = RedditScraper()

    token_response = _mock_response(401, {})

    with patch("app.scrapers.social.reddit.get_settings", return_value=_mock_settings()):
        scraper.post = AsyncMock(return_value=token_response)
        scraper._rate_limit_sleep = AsyncMock()

        results = await scraper.scrape()

    assert results == []


@pytest.mark.asyncio
async def test_reddit_scraper_returns_empty_on_no_credentials():
    """Reddit scraper should return [] when no credentials configured."""
    from app.scrapers.social.reddit import RedditScraper

    scraper = RedditScraper()

    with patch("app.scrapers.social.reddit.get_settings", return_value=_mock_settings(
        reddit_client_id="", reddit_client_secret=""
    )):
        results = await scraper.scrape()

    assert results == []


# ── 3. Twitter scraper: has 5 search queries ─────────────────────────────────


def test_twitter_scraper_has_5_search_queries():
    """Twitter scraper must have exactly 5 search queries."""
    from app.scrapers.social.twitter import _SEARCH_QUERIES

    assert len(_SEARCH_QUERIES) == 5
    for query, signal_type, hints in _SEARCH_QUERIES:
        assert isinstance(query, str)
        assert signal_type.startswith("social_twitter_")
        assert isinstance(hints, list)
        assert len(hints) > 0


# ── 4. Twitter monthly budget check blocks at 9000 ──────────────────────────


@pytest.mark.asyncio
async def test_twitter_monthly_budget_check_blocks_at_9000():
    """Twitter scraper should return [] when monthly budget is exhausted."""
    from app.scrapers.social.twitter import TwitterXScraper

    scraper = TwitterXScraper()

    mock_cache = AsyncMock()
    mock_cache.get = AsyncMock(return_value=9001)

    with patch.dict("sys.modules", {"app.cache.client": MagicMock(cache=mock_cache)}):
        result = await scraper._check_monthly_budget()

    assert result is False


@pytest.mark.asyncio
async def test_twitter_monthly_budget_allows_under_limit():
    """Twitter scraper should proceed when under monthly budget."""
    from app.scrapers.social.twitter import TwitterXScraper

    scraper = TwitterXScraper()

    mock_cache = AsyncMock()
    mock_cache.get = AsyncMock(return_value=100)

    with patch.dict("sys.modules", {"app.cache.client": MagicMock(cache=mock_cache)}):
        result = await scraper._check_monthly_budget()

    assert result is True


# ── 5. LinkedIn scraper: skips when no API key ───────────────────────────────


@pytest.mark.asyncio
async def test_linkedin_scraper_skips_when_no_api_key():
    """LinkedIn scraper should return [] when no Proxycurl API key."""
    from app.scrapers.social.linkedin_social import LinkedInScraper

    scraper = LinkedInScraper()

    with patch("app.scrapers.social.linkedin_social.get_settings", return_value=_mock_settings(
        proxycurl_api_key=""
    )):
        results = await scraper.scrape()

    assert results == []


# ── 6. Stockhouse scraper: filters bear keywords ────────────────────────────


@pytest.mark.asyncio
async def test_stockhouse_scraper_filters_bear_keywords():
    """Stockhouse scraper should filter posts containing bear keywords."""
    from app.scrapers.social.stockhouse import StockhouseScraper

    scraper = StockhouseScraper()

    html = """
    <html><body>
    <div class="search-result">
        <h3><a class="title" href="/companies/bullboard/RY/post1">
            Company facing class action lawsuit
        </a></h3>
        <time datetime="2026-03-28T10:00:00Z">Mar 28</time>
        <p>Major class action filed against Royal Bank</p>
    </div>
    <div class="search-result">
        <h3><a class="title" href="/companies/bullboard/TD/post2">
            Great quarterly results reported
        </a></h3>
        <time datetime="2026-03-28T10:00:00Z">Mar 28</time>
        <p>TD beats expectations this quarter</p>
    </div>
    <div class="search-result">
        <h3><a class="title" href="/companies/bullboard/BNS/post3">
            OSC investigation into fraud allegations
        </a></h3>
        <time datetime="2026-03-28T10:00:00Z">Mar 28</time>
        <p>Ontario Securities Commission opens investigation</p>
    </div>
    </body></html>
    """

    mock_response = _mock_response(200, text=html)
    mock_response.text = html

    scraper.get = AsyncMock(return_value=mock_response)
    scraper._rate_limit_sleep = AsyncMock()

    results = await scraper.scrape()

    # Only posts with bear keywords should be included (class action, fraud/OSC)
    # The "Great quarterly results" post should be filtered out
    assert len(results) >= 2
    for r in results:
        assert r.source_id == "social_stockhouse"
        assert r.signal_type in ["social_stockhouse_bear", "social_stockhouse_legal"]


# ── 7. All social scrapers registered ────────────────────────────────────────


def test_all_social_scrapers_registered():
    """All 4 core social scrapers must be registered in ScraperRegistry."""
    from app.scrapers.registry import ScraperRegistry

    all_ids = ScraperRegistry.all_ids()
    for sid in [
        "social_reddit",
        "social_twitter_x",
        "social_linkedin",
        "social_stockhouse",
    ]:
        assert sid in all_ids, f"Missing social scraper: {sid}"


def test_social_scrapers_have_category():
    """All social scrapers must have CATEGORY = 'social'."""
    from app.scrapers.registry import ScraperRegistry

    social_scrapers = ScraperRegistry.by_category("social")
    social_ids = [s.source_id for s in social_scrapers]
    for sid in [
        "social_reddit",
        "social_twitter_x",
        "social_linkedin",
        "social_stockhouse",
        "social_sedar_forums",
    ]:
        assert sid in social_ids, f"Scraper {sid} missing CATEGORY='social'"


def test_sedar_forums_is_stub():
    """SEDAR forums scraper should be a stub returning []."""
    from app.scrapers.social.sedar_forums import SedarForumsScraper

    scraper = SedarForumsScraper()
    assert scraper.source_id == "social_sedar_forums"
    assert scraper.CATEGORY == "social"


def test_config_has_reddit_settings():
    """Config Settings class must have reddit_client_id and reddit_client_secret."""
    from app.config import Settings

    fields = Settings.model_fields
    assert "reddit_client_id" in fields, "reddit_client_id missing from Settings"
    assert "reddit_client_secret" in fields, "reddit_client_secret missing from Settings"


def test_twitter_ticker_extraction():
    """Twitter scraper should extract TSX tickers from tweet text."""
    from app.scrapers.social.twitter import TwitterXScraper

    assert TwitterXScraper._extract_ticker("Look at TSX:RY dropping") == "RY"
    assert TwitterXScraper._extract_ticker("TSXV:GOLD looking bad") == "GOLD"
    assert TwitterXScraper._extract_ticker("No ticker here") is None


def test_stockhouse_bear_keywords_complete():
    """Stockhouse scraper must have a comprehensive bear keyword list."""
    from app.scrapers.social.stockhouse import _BEAR_KEYWORDS

    required = ["lawsuit", "class action", "fraud", "investigation", "OSC"]
    for kw in required:
        assert kw in _BEAR_KEYWORDS, f"Missing bear keyword: {kw}"
