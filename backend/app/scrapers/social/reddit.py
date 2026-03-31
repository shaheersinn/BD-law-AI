"""
app/scrapers/social/reddit.py — Reddit scraper.

Sources: r/legaladvicecanada, r/PersonalFinanceCanada, r/canada,
         r/investing, r/CanadianInvestor

Auth: Reddit OAuth2 (free tier, 60 req/min)
Data: MongoDB ONLY — raw social content never goes to PostgreSQL.

Signal types:
  social_reddit_legal       — legal context mention (litigation, employment, class actions)
  social_reddit_regulatory  — regulatory complaint/enforcement discussion
"""

from __future__ import annotations

import base64
import re
import time
from datetime import UTC, datetime
from typing import Any

import structlog

from app.config import get_settings
from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_REDDIT_OAUTH = "https://oauth.reddit.com"
_REDDIT_TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
_REDDIT_UA = "ORACLE-BD-Intelligence/1.0 (legal-intelligence-platform; research)"

# (subreddit, query, signal_type, practice_area_hints)
_SUBREDDITS_QUERIES = [
    (
        "legaladvicecanada",
        "lawsuit OR litigation OR fired OR wrongful",
        "social_reddit_legal",
        ["litigation", "employment"],
    ),
    (
        "legaladvicecanada",
        "CCAA OR receivership OR bankruptcy OR insolvency",
        "social_reddit_legal",
        ["insolvency"],
    ),
    (
        "PersonalFinanceCanada",
        "lawsuit OR class action OR settlement",
        "social_reddit_legal",
        ["litigation"],
    ),
    (
        "canada",
        "regulatory fine OR enforcement OR securities fraud",
        "social_reddit_regulatory",
        ["regulatory", "securities"],
    ),
    (
        "investing",
        "SEC OR OSC OR enforcement OR fraud TSX",
        "social_reddit_regulatory",
        ["securities"],
    ),
    (
        "CanadianInvestor",
        "lawsuit OR investigation OR class action TSX",
        "social_reddit_legal",
        ["litigation", "securities"],
    ),
]

_STOPWORDS = {"I", "My", "The", "This", "That", "What", "How", "Why", "Can", "Am", "Is"}


@register
class RedditScraper(BaseScraper):
    source_id = "social_reddit"
    source_name = "Reddit (Canadian finance/legal subreddits)"
    signal_types = ["social_reddit_legal", "social_reddit_regulatory"]
    CATEGORY = "social"
    rate_limit_rps = 0.5
    concurrency = 2
    retry_attempts = 3
    timeout_seconds = 20.0
    ttl_seconds = 1800
    requires_auth = True

    def __init__(self) -> None:
        super().__init__()
        self._access_token: str | None = None
        self._token_expires: float = 0.0

    async def scrape(self) -> list[ScraperResult]:
        settings = get_settings()
        if not settings.reddit_client_id or not settings.reddit_client_secret:
            log.warning("reddit_no_credentials")
            return []

        token = await self._get_oauth_token(
            settings.reddit_client_id, settings.reddit_client_secret
        )
        if not token:
            log.warning("reddit_auth_failed")
            return []

        results: list[ScraperResult] = []
        for subreddit, query, signal_type, hints in _SUBREDDITS_QUERIES:
            try:
                posts = await self._search_subreddit(token, subreddit, query)
                for post in posts:
                    result = self._build_result(post, subreddit, signal_type, hints)
                    if result:
                        results.append(result)
                await self._rate_limit_sleep()
            except Exception as exc:
                log.error("reddit_subreddit_error", sub=subreddit, error=str(exc))

        log.info("reddit_scrape_complete", total=len(results))
        return results

    async def _get_oauth_token(self, client_id: str, client_secret: str) -> str | None:
        if self._access_token and time.time() < self._token_expires - 60:
            return self._access_token
        try:
            creds = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
            response = await self.post(
                _REDDIT_TOKEN_URL,
                data={"grant_type": "client_credentials"},
                headers={
                    "Authorization": f"Basic {creds}",
                    "User-Agent": _REDDIT_UA,
                },
            )
            if response.status_code == 200:
                data = response.json()
                self._access_token = data.get("access_token")
                self._token_expires = time.time() + data.get("expires_in", 3600)
                return self._access_token
            log.warning("reddit_token_non200", status=response.status_code)
        except Exception as exc:
            log.error("reddit_token_error", error=str(exc))
        return None

    async def _search_subreddit(
        self, token: str, subreddit: str, query: str
    ) -> list[dict[str, Any]]:
        response = await self.get(
            f"{_REDDIT_OAUTH}/r/{subreddit}/search.json",
            params={
                "q": query,
                "sort": "new",
                "t": "week",
                "limit": 25,
                "restrict_sr": "true",
            },
            headers={
                "Authorization": f"bearer {token}",
                "User-Agent": _REDDIT_UA,
            },
        )
        if response.status_code != 200:
            return []
        data = response.json()
        return [child["data"] for child in data.get("data", {}).get("children", [])]

    def _build_result(
        self,
        post: dict[str, Any],
        subreddit: str,
        signal_type: str,
        hints: list[str],
    ) -> ScraperResult | None:
        title = post.get("title", "")
        selftext = post.get("selftext", "")
        # Skip non-English posts
        text_lower = (title + " " + selftext).lower()
        if not text_lower.strip():
            return None

        company = self._extract_company_mention(title)
        created_utc = post.get("created_utc")
        pub_dt = None
        if created_utc:
            pub_dt = datetime.fromtimestamp(float(created_utc), tz=UTC)

        return ScraperResult(
            source_id=self.source_id,
            signal_type=signal_type,
            raw_company_name=company,
            source_url=f"https://www.reddit.com{post.get('permalink', '')}",
            signal_value={
                "subreddit": subreddit,
                "post_id": post.get("id"),
                "score": post.get("score", 0),
                "num_comments": post.get("num_comments", 0),
                "upvote_ratio": post.get("upvote_ratio", 0.0),
            },
            signal_text=title[:500],
            published_at=pub_dt,
            practice_area_hints=hints,
            raw_payload={
                "id": post.get("id"),
                "title": title,
                "selftext": selftext[:2000],
                "score": post.get("score", 0),
                "subreddit": subreddit,
            },
            confidence_score=0.6,
        )

    def _extract_company_mention(self, title: str) -> str | None:
        matches = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3}", title)
        companies = [m for m in matches if m.split()[0] not in _STOPWORDS]
        return companies[0] if companies else None
