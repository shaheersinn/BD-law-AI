"""
app/scrapers/social/twitter.py — Twitter/X scraper.

Source: Twitter/X API v2 (Bearer Token — free Basic tier)
        https://api.twitter.com/2/tweets/search/recent

Queries financial distress + legal signals on Canadian public companies.
Free Basic tier: 10,000 tweets/month read access.

Data: MongoDB ONLY.

Signal types:
  social_twitter_legal      — company named in legal/enforcement context
  social_twitter_distress   — financial distress signals (CCAA, insolvency)
  social_twitter_regulatory — regulatory enforcement (SEC/OSC)
  social_twitter_ma         — M&A activity (merger, acquisition, hostile bid)
"""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta

import structlog

from app.config import get_settings
from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_TWITTER_SEARCH = "https://api.twitter.com/2/tweets/search/recent"

_SEARCH_QUERIES = [
    (
        'lawsuit OR litigation OR "class action" OR "cease trade" lang:en -is:retweet',
        "social_twitter_legal",
        ["litigation"],
    ),
    (
        "CCAA OR receivership OR insolvency OR bankruptcy lang:en -is:retweet",
        "social_twitter_distress",
        ["insolvency"],
    ),
    (
        "TSX OR TSXV SEC enforcement penalty investigation fraud lang:en",
        "social_twitter_regulatory",
        ["securities"],
    ),
    (
        '"data breach" OR "privacy violation" Canada lang:en',
        "social_twitter_legal",
        ["privacy_data"],
    ),
    ('merger acquisition "hostile bid" "going private" TSX lang:en', "social_twitter_ma", ["ma"]),
]

_TICKER_PATTERN = re.compile(r"\b(?:TSX|TSXV|TSE)\s*[:]\s*([A-Z]{1,5})\b")
_MONTHLY_BUDGET = 9000


@register
class TwitterXScraper(BaseScraper):
    source_id = "social_twitter_x"
    source_name = "Twitter/X Financial Signals"
    signal_types = [
        "social_twitter_legal",
        "social_twitter_distress",
        "social_twitter_regulatory",
        "social_twitter_ma",
    ]
    CATEGORY = "social"
    rate_limit_rps = 0.1
    concurrency = 1
    retry_attempts = 3
    timeout_seconds = 20.0
    ttl_seconds = 1800
    requires_auth = True

    async def scrape(self) -> list[ScraperResult]:
        settings = get_settings()
        bearer_token = settings.twitter_bearer_token
        if not bearer_token:
            log.warning("twitter_no_bearer_token")
            return []

        if not await self._check_monthly_budget():
            return []

        results: list[ScraperResult] = []
        headers = {
            "Authorization": f"Bearer {bearer_token}",
            "User-Agent": "ORACLE-BD/1.0",
        }

        for query, signal_type, hints in _SEARCH_QUERIES:
            try:
                tweets = await self._search_with_pagination(query, headers)
                await self._increment_monthly_counter(len(tweets))

                for tweet in tweets:
                    metrics = tweet.get("public_metrics", {})
                    text = tweet.get("text", "")
                    ticker = self._extract_ticker(text)
                    company = self._extract_company_name(text)

                    results.append(
                        ScraperResult(
                            source_id=self.source_id,
                            signal_type=signal_type,
                            raw_company_name=company,
                            source_url=f"https://twitter.com/i/web/status/{tweet.get('id')}",
                            signal_value={
                                "tweet_id": tweet.get("id"),
                                "retweet_count": metrics.get("retweet_count", 0),
                                "like_count": metrics.get("like_count", 0),
                                "reply_count": metrics.get("reply_count", 0),
                                "ticker": ticker,
                            },
                            signal_text=text[:500],
                            published_at=self._parse_date(tweet.get("created_at")),
                            practice_area_hints=hints,
                            raw_payload={
                                "id": tweet.get("id"),
                                "text": text,
                                "metrics": metrics,
                                "author_id": tweet.get("author_id"),
                            },
                            confidence_score=0.5,
                        )
                    )
                await self._rate_limit_sleep()
            except Exception as exc:
                log.error("twitter_query_error", query=query[:50], error=str(exc))

        log.info("twitter_scrape_complete", total=len(results))
        return results

    async def _search_with_pagination(
        self, query: str, headers: dict[str, str], max_pages: int = 2
    ) -> list[dict]:
        all_tweets: list[dict] = []
        next_token: str | None = None

        for _ in range(max_pages):
            params: dict[str, str | int] = {
                "query": query,
                "max_results": 10,
                "tweet.fields": "created_at,author_id,public_metrics,entities",
                "start_time": (datetime.now(tz=UTC) - timedelta(hours=6)).isoformat(),
            }
            if next_token:
                params["next_token"] = next_token

            response = await self.get(_TWITTER_SEARCH, params=params, headers=headers)

            if response.status_code == 429:
                log.warning("twitter_rate_limited")
                break
            if response.status_code != 200:
                break

            data = response.json()
            all_tweets.extend(data.get("data", []))

            meta = data.get("meta", {})
            next_token = meta.get("next_token")
            if not next_token:
                break

        return all_tweets

    async def _check_monthly_budget(self) -> bool:
        """Return False if monthly tweet budget is exhausted."""
        try:
            from app.cache.client import cache

            key = f"twitter_monthly_count:{datetime.now(tz=UTC).strftime('%Y-%m')}"
            count = await cache.get(key)
            if count is not None and int(count) >= _MONTHLY_BUDGET:
                log.warning("twitter_monthly_budget_exhausted", count=count)
                return False
        except Exception as exc:
            log.warning("twitter_budget_check_failed", error=str(exc))
        return True

    async def _increment_monthly_counter(self, count: int) -> None:
        """Increment the monthly tweet counter in Redis."""
        try:
            from app.cache.client import cache

            key = f"twitter_monthly_count:{datetime.now(tz=UTC).strftime('%Y-%m')}"
            current = await cache.get(key) or 0
            await cache.set(key, int(current) + count, ttl=60 * 60 * 24 * 32)
        except Exception as exc:
            log.warning("twitter_counter_increment_failed", error=str(exc))

    @staticmethod
    def _extract_ticker(text: str) -> str | None:
        match = _TICKER_PATTERN.search(text)
        return match.group(1) if match else None

    @staticmethod
    def _extract_company_name(text: str) -> str | None:
        matches = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3}", text)
        stopwords = {"The", "This", "That", "What", "How", "Why", "Can", "Is"}
        companies = [m for m in matches if m.split()[0] not in stopwords]
        return companies[0] if companies else None
