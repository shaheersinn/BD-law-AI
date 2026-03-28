"""
app/scrapers/social/stockhouse.py — Stockhouse Bullboards scraper.

Source: https://stockhouse.com/companies/bullboard (Canadian retail investor forum)

Stockhouse Bullboards are the primary Canadian retail investor discussion forum.
Signal value: mentions of lawsuits, management problems, regulatory probes
that surface on Bullboards before mainstream media.

Signal types:
  social_stockhouse_legal_mention   — legal/regulatory mention in post
  social_stockhouse_distress        — financial distress discussion

Data: MongoDB ONLY.
Rate: 0.2 rps (no official API — respectful scraping)
"""
from __future__ import annotations

import re
from typing import Any

import structlog
from bs4 import BeautifulSoup

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_STOCKHOUSE_BASE = "https://stockhouse.com"
_STOCKHOUSE_SEARCH = f"{_STOCKHOUSE_BASE}/companies/bullboard"

_SIGNAL_KEYWORDS = [
    "lawsuit", "suing", "class action", "investigation", "fraud", "sec",
    "osc", "cease trade", "receivership", "ccaa", "insolvency", "delisted",
    "management departing", "ceo resign", "cfo quit", "scandal", "misleading",
    "class action", "securities fraud", "ponzi",
]


@register
class StockhouseScraper(BaseScraper):
    source_id = "social_stockhouse"
    source_name = "Stockhouse Bullboards"
    signal_types = ["social_stockhouse_legal_mention", "social_stockhouse_distress"]
    rate_limit_rps = 0.2
    concurrency = 1
    retry_attempts = 3
    timeout_seconds = 30.0
    ttl_seconds = 3600
    requires_auth = False

    async def scrape(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []
        try:
            # Scrape most active/recent bullboard discussions
            response = await self.get(
                f"{_STOCKHOUSE_BASE}/news/recent",
                headers={"Referer": "https://stockhouse.com"},
            )
            if response.status_code != 200:
                return results

            soup = BeautifulSoup(response.text, "html.parser")
            posts = self._parse_recent_posts(soup)

            for post in posts:
                text = (post.get("title", "") + " " + post.get("body", "")).lower()
                if not any(kw in text for kw in _SIGNAL_KEYWORDS):
                    continue

                is_distress = any(kw in text for kw in ["ccaa", "receivership", "insolvency", "bankrupt"])
                signal_type = "social_stockhouse_distress" if is_distress else "social_stockhouse_legal_mention"
                hints = ["insolvency"] if is_distress else ["litigation", "securities"]

                results.append(ScraperResult(
                    source_id=self.source_id,
                    signal_type=signal_type,
                    raw_company_name=post.get("company"),
                    source_url=post.get("url"),
                    signal_value={
                        "ticker": post.get("ticker"),
                        "company": post.get("company"),
                        "views": post.get("views", 0),
                        "replies": post.get("replies", 0),
                    },
                    signal_text=post.get("title", "")[:500],
                    published_at=self._parse_date(post.get("date")),
                    practice_area_hints=hints,
                    raw_payload={
                        "ticker": post.get("ticker"),
                        "title": post.get("title", ""),
                        "body": post.get("body", "")[:2000],
                    },
                    confidence_score=0.55,
                ))
            await self._rate_limit_sleep()
        except Exception as exc:
            log.error("stockhouse_error", error=str(exc))

        return results

    def _parse_recent_posts(self, soup: BeautifulSoup) -> list[dict[str, Any]]:
        posts = []
        try:
            for article in soup.select("article.post, div.post-item, div.discussion-item")[:50]:
                post: dict[str, Any] = {}
                title_el = article.select_one("h2 a, h3 a, .post-title a")
                if title_el:
                    post["title"] = title_el.get_text(strip=True)
                    href_val = title_el.get("href", "")
                    href = href_val[0] if isinstance(href_val, list) else str(href_val) if href_val else ""
                    post["url"] = f"{_STOCKHOUSE_BASE}{href}" if href.startswith("/") else href

                    # Extract ticker from URL pattern /companies/bullboard/TICKER/...
                    ticker_match = re.search(r"/bullboard/([A-Z]+\.?[A-Z]*)/", href)
                    if ticker_match:
                        post["ticker"] = ticker_match.group(1)

                date_el = article.select_one("time, .post-date, .date")
                if date_el:
                    post["date"] = date_el.get("datetime") or date_el.get_text(strip=True)

                body_el = article.select_one(".post-content, .post-body, p")
                if body_el:
                    post["body"] = body_el.get_text(strip=True)[:1000]

                if post.get("title"):
                    posts.append(post)
        except Exception as e:
            log.warning("stockhouse_parse_error", error=str(e))
        return posts
