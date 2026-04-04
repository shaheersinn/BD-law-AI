"""
Bank of Canada scraper — rate decisions, financial system alerts, BOS and SLOS surveys.
Source: https://www.bankofcanada.ca/rss/ (RSS feeds)
Signals: monetary_policy_rate_change, financial_system_alert, macro_bos_credit_tightening
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET  # nosec B405
from typing import Any

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_BOC_RSS_FEEDS = [
    ("https://www.bankofcanada.ca/rss/press-releases/", "monetary_policy_rate_change"),
    ("https://www.bankofcanada.ca/rss/publications/", "financial_system_alert"),
]

_BOS_URL = "https://www.bankofcanada.ca/publications/bos/"
_SLOS_URL = "https://www.bankofcanada.ca/publications/slos/"

# If SLOS net tightening exceeds this threshold for a sector,
# generate a macro_bos_credit_tightening signal
_SLOS_TIGHTENING_THRESHOLD = 20.0  # net % tightening


@register
class BankOfCanadaScraper(BaseScraper):
    source_id = "corporate_bank_of_canada"
    CATEGORY = "corporate"
    source_name = "Bank of Canada"
    signal_types = [
        "monetary_policy_rate_change",
        "financial_system_alert",
        "macro_bos_credit_tightening",
    ]
    rate_limit_rps = 0.1
    concurrency = 1
    ttl_seconds = 3600

    async def scrape(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []

        # Existing RSS feeds
        for feed_url, default_type in _BOC_RSS_FEEDS:
            try:
                response = await self.get(feed_url)
                if response.status_code != 200:
                    continue
                root = ET.fromstring(response.text)  # nosec B314 — trusted government/news RSS source
                for item in root.iter("item"):
                    title = (item.findtext("title") or "").strip()
                    title_lower = title.lower()
                    is_rate = any(
                        k in title_lower for k in ["rate", "policy", "overnight", "basis point"]
                    )
                    signal_type = "monetary_policy_rate_change" if is_rate else default_type
                    results.append(
                        ScraperResult(
                            source_id=self.source_id,
                            signal_type=signal_type,
                            source_url=(item.findtext("link") or "").strip(),
                            signal_value={
                                "title": title,
                                "date": (item.findtext("pubDate") or "").strip(),
                            },
                            signal_text=title,
                            published_at=self._parse_date((item.findtext("pubDate") or "").strip()),
                            practice_area_hints=["banking", "insolvency", "financial_regulatory"],
                            raw_payload={"title": title},
                        )
                    )
                await self._rate_limit_sleep()
            except Exception as exc:
                log.error("boc_feed_error", feed=feed_url, error=str(exc))

        # BOS + SLOS survey scraping (quarterly)
        try:
            bos_slos_results = await self._scrape_bos_slos()
            results.extend(bos_slos_results)
        except Exception as exc:
            log.error("boc_bos_slos_error", error=str(exc))

        return results

    async def _scrape_bos_slos(self) -> list[ScraperResult]:
        """
        Scrape BOS (Business Outlook Survey) and SLOS (Senior Loan Officer Survey)
        publication pages for credit tightening signals.
        """
        results: list[ScraperResult] = []

        # Scrape SLOS page for lending condition indicators
        try:
            soup = await self.get_soup(_SLOS_URL)
            if soup:
                results.extend(self._parse_slos(soup))
        except Exception as exc:
            log.warning("boc_slos_error", error=str(exc))

        # Scrape BOS page for business outlook indicators
        try:
            soup = await self.get_soup(_BOS_URL)
            if soup:
                results.extend(self._parse_bos(soup))
        except Exception as exc:
            log.warning("boc_bos_error", error=str(exc))

        return results

    def _parse_slos(self, soup: Any) -> list[ScraperResult]:
        """Parse SLOS publications for credit tightening signals."""
        results: list[ScraperResult] = []

        articles = (
            soup.find_all("article")  # type: ignore[union-attr]
            or soup.find_all("div", class_=re.compile(r"publication|post|entry", re.I))  # type: ignore[union-attr]
        )

        for article in articles[:5]:
            try:
                title_el = article.find(["h2", "h3", "h4", "a"])
                title = self.safe_text(title_el) if title_el else ""
                if not title:
                    continue

                text = self.safe_text(article).lower()

                # Check for tightening language
                is_tightening = any(
                    kw in text
                    for kw in [
                        "tightening",
                        "tightened",
                        "restrictive",
                        "stricter",
                        "reduced availability",
                    ]
                )
                if not is_tightening:
                    continue

                link_el = article.find("a", href=True)
                source_url = ""
                if link_el:
                    href = str(link_el.get("href", ""))
                    if href.startswith("http"):
                        source_url = href
                    elif href.startswith("/"):
                        source_url = f"https://www.bankofcanada.ca{href}"

                date_el = article.find("time")
                published_at = None
                if date_el:
                    date_str = date_el.get("datetime") or self.safe_text(date_el)
                    published_at = self._parse_date(str(date_str))

                results.append(
                    ScraperResult(
                        source_id=self.source_id,
                        signal_type="macro_bos_credit_tightening",
                        source_url=source_url or _SLOS_URL,
                        signal_value={
                            "title": title,
                            "survey": "SLOS",
                            "indicator": "credit_tightening",
                        },
                        signal_text=f"SLOS credit tightening: {title}",
                        published_at=published_at or self._now_utc(),
                        practice_area_hints=[
                            "Banking & Finance",
                            "Restructuring / Insolvency",
                        ],
                        raw_payload={"title": title, "survey": "SLOS"},
                        confidence_score=0.72,
                    )
                )
            except Exception as exc:
                log.warning("boc_slos_article_error", error=str(exc))

        return results

    def _parse_bos(self, soup: Any) -> list[ScraperResult]:
        """Parse BOS publications for business outlook deterioration signals."""
        results: list[ScraperResult] = []

        articles = (
            soup.find_all("article")  # type: ignore[union-attr]
            or soup.find_all("div", class_=re.compile(r"publication|post|entry", re.I))  # type: ignore[union-attr]
        )

        for article in articles[:5]:
            try:
                title_el = article.find(["h2", "h3", "h4", "a"])
                title = self.safe_text(title_el) if title_el else ""
                if not title:
                    continue

                text = self.safe_text(article).lower()

                # Check for deterioration language
                is_negative = any(
                    kw in text
                    for kw in [
                        "deteriorat",
                        "weaken",
                        "decline",
                        "pessimis",
                        "downturn",
                        "contraction",
                    ]
                )
                if not is_negative:
                    continue

                link_el = article.find("a", href=True)
                source_url = ""
                if link_el:
                    href = str(link_el.get("href", ""))
                    if href.startswith("http"):
                        source_url = href
                    elif href.startswith("/"):
                        source_url = f"https://www.bankofcanada.ca{href}"

                date_el = article.find("time")
                published_at = None
                if date_el:
                    date_str = date_el.get("datetime") or self.safe_text(date_el)
                    published_at = self._parse_date(str(date_str))

                results.append(
                    ScraperResult(
                        source_id=self.source_id,
                        signal_type="macro_bos_credit_tightening",
                        source_url=source_url or _BOS_URL,
                        signal_value={
                            "title": title,
                            "survey": "BOS",
                            "indicator": "business_outlook_deterioration",
                        },
                        signal_text=f"BOS outlook deterioration: {title}",
                        published_at=published_at or self._now_utc(),
                        practice_area_hints=[
                            "Banking & Finance",
                            "Restructuring / Insolvency",
                        ],
                        raw_payload={"title": title, "survey": "BOS"},
                        confidence_score=0.70,
                    )
                )
            except Exception as exc:
                log.warning("boc_bos_article_error", error=str(exc))

        return results
