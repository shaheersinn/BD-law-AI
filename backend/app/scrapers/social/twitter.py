"""
app/scrapers/social/twitter_x.py — Twitter/X scraper.

Source: Twitter/X API v2 (Bearer Token — free Basic tier)
        https://api.twitter.com/2/tweets/search/recent

Queries financial distress + legal signals on Canadian public companies.
Free Basic tier: 10,000 tweets/month read access.

Data: MongoDB ONLY.

Signal types:
  social_twitter_legal_mention   — company named in legal/enforcement context
  social_twitter_distress        — financial distress signals
  social_twitter_insider         — executive/insider commentary
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import structlog

from app.config import get_settings
from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_TWITTER_SEARCH = "https://api.twitter.com/2/tweets/search/recent"

_SEARCH_QUERIES = [
    ("lawsuit OR litigation OR \"class action\" OR \"cease trade\" lang:en", "social_twitter_legal_mention", ["litigation"]),
    ("CCAA OR receivership OR insolvency OR bankruptcy lang:en -is:retweet", "social_twitter_distress", ["insolvency"]),
    ("TSX OR TSXV SEC enforcement penalty investigation fraud lang:en", "social_twitter_distress", ["securities"]),
    ("\"data breach\" OR \"privacy violation\" Canada lang:en", "social_twitter_legal_mention", ["privacy"]),
    ("merger acquisition \"hostile bid\" \"going private\" TSX lang:en", "social_twitter_legal_mention", ["ma"]),
]


@register
class TwitterXScraper(BaseScraper):
    source_id = "social_twitter_x"
    source_name = "Twitter/X Financial Signals"
    signal_types = ["social_twitter_legal_mention", "social_twitter_distress"]
    rate_limit_rps = 0.1   # Very conservative — free tier 10k/month
    concurrency = 1
    retry_attempts = 3
    timeout_seconds = 20.0
    ttl_seconds = 1800
    requires_auth = True

    async def scrape(self) -> list[ScraperResult]:
        settings = get_settings()
        bearer_token = getattr(settings, "twitter_bearer_token", None)
        if not bearer_token:
            log.warning("twitter_no_bearer_token")
            return []

        results: list[ScraperResult] = []
        headers = {
            "Authorization": f"Bearer {bearer_token}",
            "User-Agent": "ORACLE-BD/1.0",
        }

        for query, signal_type, hints in _SEARCH_QUERIES:
            try:
                params = {
                    "query": query,
                    "max_results": 10,
                    "tweet.fields": "created_at,author_id,public_metrics,entities",
                    "start_time": (datetime.now(tz=UTC) - timedelta(hours=6)).isoformat(),
                }
                response = await self.get(_TWITTER_SEARCH, params=params, headers=headers)

                if response.status_code == 429:
                    log.warning("twitter_rate_limited")
                    break
                if response.status_code != 200:
                    continue

                data = response.json()
                for tweet in data.get("data", []):
                    metrics = tweet.get("public_metrics", {})
                    results.append(ScraperResult(
                        source_id=self.source_id,
                        signal_type=signal_type,
                        source_url=f"https://twitter.com/i/web/status/{tweet.get('id')}",
                        signal_value={
                            "tweet_id": tweet.get("id"),
                            "retweet_count": metrics.get("retweet_count", 0),
                            "like_count": metrics.get("like_count", 0),
                            "reply_count": metrics.get("reply_count", 0),
                        },
                        signal_text=tweet.get("text", "")[:500],
                        published_at=self._parse_date(tweet.get("created_at")),
                        practice_area_hints=hints,
                        raw_payload={
                            "id": tweet.get("id"),
                            "text": tweet.get("text", ""),
                            "metrics": metrics,
                        },
                        confidence_score=0.5,
                    ))
                await self._rate_limit_sleep()
            except Exception as exc:
                log.error("twitter_query_error", query=query[:50], error=str(exc))

        log.info("twitter_scrape_complete", total=len(results))
        return results
