"""
app/scrapers/social/stockhouse.py — Stockhouse Bullboards scraper.

Source: https://stockhouse.com/companies/bullboard (Canadian retail investor forum)

Stockhouse Bullboards are the primary Canadian retail investor discussion forum.
Signal value: mentions of lawsuits, management problems, regulatory probes
that surface on Bullboards before mainstream media.

Signal types:
  social_stockhouse_bear   — bearish sentiment with legal/distress keywords
  social_stockhouse_legal  — explicit legal/regulatory mention in post

Data: MongoDB ONLY.
Rate: 0.1 rps (no official API — respectful scraping)
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
_STOCKHOUSE_SEARCH = f"{_STOCKHOUSE_BASE}/search?q={{ticker}}&type=bullboard"

_BEAR_KEYWORDS = [
    "lawsuit",
    "class action",
    "fraud",
    "investigation",
    "cease trade",
    "receivership",
    "insolvency",
    "regulatory",
    "SEC",
    "OSC",
    "BCSC",
    "going concern",
]

_DISTRESS_KEYWORDS = [
    "ccaa",
    "receivership",
    "insolvency",
    "bankrupt",
    "going concern",
    "delisted",
]

_TOP_TSX_TICKERS = [
    "RY",
    "TD",
    "BNS",
    "BMO",
    "CM",
    "ENB",
    "CNR",
    "CP",
    "SU",
    "CNQ",
    "BCE",
    "TRP",
    "MFC",
    "SLF",
    "ABX",
    "NTR",
    "FTS",
    "AEM",
    "WCN",
    "CSU",
]


@register
class StockhouseScraper(BaseScraper):
    source_id = "social_stockhouse"
    source_name = "Stockhouse Bullboards"
    signal_types = ["social_stockhouse_bear", "social_stockhouse_legal"]
    CATEGORY = "social"
    rate_limit_rps = 0.1
    concurrency = 1
    retry_attempts = 3
    timeout_seconds = 30.0
    ttl_seconds = 3600
    requires_auth = False

    async def scrape(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []

        for ticker in _TOP_TSX_TICKERS:
            try:
                url = _STOCKHOUSE_SEARCH.format(ticker=ticker)
                response = await self.get(
                    url,
                    headers={"Referer": _STOCKHOUSE_BASE},
                )
                if response.status_code != 200:
                    continue

                soup = BeautifulSoup(response.text, "html.parser")
                posts = self._parse_posts(soup, ticker)

                for post in posts:
                    text = (post.get("title", "") + " " + post.get("body", "")).lower()
                    if not any(kw.lower() in text for kw in _BEAR_KEYWORDS):
                        continue

                    is_distress = any(kw in text for kw in _DISTRESS_KEYWORDS)
                    signal_type = (
                        "social_stockhouse_bear" if is_distress else "social_stockhouse_legal"
                    )
                    hints = ["insolvency"] if is_distress else ["litigation", "securities"]

                    results.append(
                        ScraperResult(
                            source_id=self.source_id,
                            signal_type=signal_type,
                            raw_company_name=post.get("company"),
                            source_url=post.get("url"),
                            signal_value={
                                "ticker": ticker,
                                "company": post.get("company"),
                                "views": post.get("views", 0),
                                "replies": post.get("replies", 0),
                            },
                            signal_text=post.get("title", "")[:500],
                            published_at=self._parse_date(post.get("date")),
                            practice_area_hints=hints,
                            raw_payload={
                                "ticker": ticker,
                                "title": post.get("title", ""),
                                "body": post.get("body", "")[:2000],
                            },
                            confidence_score=0.55,
                        )
                    )

                await self._rate_limit_sleep()
            except Exception as exc:
                log.error("stockhouse_ticker_error", ticker=ticker, error=str(exc))

        log.info("stockhouse_scrape_complete", total=len(results))
        return results

    def _parse_posts(self, soup: BeautifulSoup, ticker: str) -> list[dict[str, Any]]:
        posts: list[dict[str, Any]] = []
        try:
            for article in soup.select(
                "article.post, div.post-item, div.discussion-item, div.search-result"
            )[:50]:
                post: dict[str, Any] = {"ticker": ticker}

                title_el = article.select_one("h2 a, h3 a, .post-title a, a.title")
                if title_el:
                    post["title"] = title_el.get_text(strip=True)
                    href_val = title_el.get("href", "")
                    href = (
                        href_val[0]
                        if isinstance(href_val, list)
                        else str(href_val)
                        if href_val
                        else ""
                    )
                    post["url"] = f"{_STOCKHOUSE_BASE}{href}" if href.startswith("/") else href

                    company_match = re.search(r"/bullboard/([A-Z]+\.?[A-Z]*)/", href)
                    if company_match:
                        post["company"] = company_match.group(1)

                date_el = article.select_one("time, .post-date, .date")
                if date_el:
                    post["date"] = date_el.get("datetime") or date_el.get_text(strip=True)

                body_el = article.select_one(".post-content, .post-body, p")
                if body_el:
                    post["body"] = body_el.get_text(strip=True)[:1000]

                if post.get("title"):
                    posts.append(post)
        except Exception as exc:
            log.warning("stockhouse_parse_error", error=str(exc))
        return posts
