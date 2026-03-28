"""
app/scrapers/social/reddit.py — Reddit scraper.

Sources: r/legaladvicecanada, r/PersonalFinanceCanada, r/canada,
         r/investing, r/CanadianInvestor

Auth: Reddit OAuth2 (free tier, 60 req/min)
Data: MongoDB ONLY — raw social content never goes to PostgreSQL.

Signal types:
  social_reddit_legal_mention  — company named in legal context
  social_reddit_distress       — financial distress discussion
  social_reddit_regulatory     — regulatory complaint/enforcement discussion
"""
from __future__ import annotations

import base64
import re
import time
from datetime import UTC
from typing import Any

import structlog

from app.config import get_settings
from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_REDDIT_OAUTH = "https://oauth.reddit.com"
_REDDIT_TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
_REDDIT_UA = "ORACLE-BD/1.0 (legal-intelligence-platform; research)"

_SUBREDDITS = [
    ("legaladvicecanada",    "social_reddit_legal_mention",  ["litigation", "employment"]),
    ("PersonalFinanceCanada","social_reddit_distress",       ["insolvency", "banking"]),
    ("canada",               "social_reddit_regulatory",     ["regulatory"]),
    ("investing",            "social_reddit_distress",       ["securities"]),
    ("CanadianInvestor",     "social_reddit_distress",       ["securities", "ma"]),
]

_SIGNAL_KEYWORDS = [
    "lawsuit", "suing", "sued", "legal action", "class action",
    "investigation", "enforcement", "laid off", "bankruptcy",
    "ccaa", "receivership", "regulatory", "fine", "penalty",
    "fraud", "sec", "osc", "ciro", "compliance",
    "acquisition", "merger", "takeover", "hostile bid",
    "data breach", "privacy", "hacked", "breach",
]

_STOPWORDS = {"I", "My", "The", "This", "That", "What", "How", "Why", "Can", "Am", "Is"}


@register
class RedditScraper(BaseScraper):
    source_id = "social_reddit"
    source_name = "Reddit (Canadian finance/legal subreddits)"
    signal_types = ["social_reddit_legal_mention", "social_reddit_distress", "social_reddit_regulatory"]
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
        client_id = getattr(settings, "reddit_client_id", None)
        client_secret = getattr(settings, "reddit_client_secret", None)
        if not client_id or not client_secret:
            log.warning("reddit_no_credentials")
            return []

        token = await self._get_token(client_id, client_secret)
        if not token:
            return []

        results: list[ScraperResult] = []
        for subreddit, signal_type, hints in _SUBREDDITS:
            try:
                posts = await self._fetch_new_posts(subreddit, token)
                for post in posts:
                    text = (post.get("title", "") + " " + post.get("selftext", "")).lower()
                    if not any(kw in text for kw in _SIGNAL_KEYWORDS):
                        continue
                    company = self._extract_company_mention(post.get("title", ""))
                    created_utc = post.get("created_utc")
                    pub_dt = None
                    if created_utc:
                        from datetime import datetime
                        pub_dt = datetime.fromtimestamp(float(created_utc), tz=UTC)

                    results.append(ScraperResult(
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
                        signal_text=post.get("title", "")[:500],
                        published_at=pub_dt,
                        practice_area_hints=hints,
                        raw_payload={
                            "id": post.get("id"),
                            "title": post.get("title", ""),
                            "selftext": post.get("selftext", "")[:2000],
                            "score": post.get("score", 0),
                            "subreddit": subreddit,
                        },
                        confidence_score=0.6,
                    ))
                await self._rate_limit_sleep()
            except Exception as exc:
                log.error("reddit_subreddit_error", sub=subreddit, error=str(exc))

        log.info("reddit_scrape_complete", total=len(results))
        return results

    async def _get_token(self, client_id: str, client_secret: str) -> str | None:
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

    async def _fetch_new_posts(self, subreddit: str, token: str) -> list[dict[str, Any]]:
        response = await self.get(
            f"{_REDDIT_OAUTH}/r/{subreddit}/new",
            params={"limit": 100, "sort": "new"},
            headers={"Authorization": f"bearer {token}", "User-Agent": _REDDIT_UA},
        )
        if response.status_code != 200:
            return []
        data = response.json()
        return [child["data"] for child in data.get("data", {}).get("children", [])]

    def _extract_company_mention(self, title: str) -> str | None:
        matches = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3}', title)
        companies = [m for m in matches if m.split()[0] not in _STOPWORDS]
        return companies[0] if companies else None
