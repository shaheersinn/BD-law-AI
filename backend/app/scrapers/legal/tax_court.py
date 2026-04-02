"""
Tax Court of Canada scraper.

Source: Tax Court of Canada latest decisions + CanLII Tax Court corpus.
Signal: tax_court_dispute — fires when watchlist companies appear as parties.
"""

from __future__ import annotations

import re

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_TCC_DECISIONS_URL = (
    "https://decision.tcc-cci.gc.ca/tcc-cci/en/d/rss.xml"
)
_TCC_HTML_URL = (
    "https://decision.tcc-cci.gc.ca/tcc-cci/en/nav.do"
)


@register
class TaxCourtScraper(BaseScraper):
    source_id = "legal_tax_court"
    source_name = "Tax Court of Canada"
    signal_types = ["tax_court_dispute"]
    CATEGORY = "legal"
    rate_limit_rps = 0.2
    concurrency = 1
    ttl_seconds = 7200

    async def scrape(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []

        # Try RSS feed first
        try:
            rss_results = await self._scrape_rss()
            results.extend(rss_results)
        except Exception as exc:
            log.error("tax_court_rss_error", error=str(exc))

        # Fallback to HTML scraping
        if not results:
            try:
                html_results = await self._scrape_html()
                results.extend(html_results)
            except Exception as exc:
                log.error("tax_court_html_error", error=str(exc))

        return results

    async def _scrape_rss(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []

        import xml.etree.ElementTree as ET  # nosec B405

        try:
            resp = await self.get(_TCC_DECISIONS_URL)
            if resp.status_code != 200:
                return results

            root = ET.fromstring(resp.text)  # nosec B314 — trusted government RSS
        except Exception as exc:
            log.warning("tax_court_rss_fetch_error", error=str(exc))
            return results

        for item in root.iter("item"):
            try:
                title = (item.findtext("title") or "").strip()
                link = (item.findtext("link") or "").strip()
                pub_date = (item.findtext("pubDate") or "").strip()
                description = (item.findtext("description") or "").strip()

                if not title:
                    continue

                # Extract party name
                party = self._extract_party(title)

                results.append(
                    ScraperResult(
                        source_id=self.source_id,
                        signal_type="tax_court_dispute",
                        raw_company_name=party,
                        source_url=link,
                        signal_value={
                            "title": title,
                            "court": "Tax Court of Canada",
                            "description": description[:300],
                        },
                        signal_text=f"Tax Court: {title}",
                        published_at=self._parse_date(pub_date),
                        practice_area_hints=["Tax"],
                        raw_payload={"title": title, "description": description[:500]},
                        confidence_score=0.82,
                    )
                )
            except Exception as exc:
                log.warning("tax_court_item_error", error=str(exc))

        return results

    async def _scrape_html(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []

        try:
            soup = await self.get_soup(_TCC_HTML_URL)
            if not soup:
                return results
        except Exception as exc:
            log.warning("tax_court_html_fetch_error", error=str(exc))
            return results

        items = (
            soup.find_all("div", class_=re.compile(r"result|decision|item", re.I))
            or soup.find_all("li", class_=re.compile(r"result|decision", re.I))
            or soup.select("table tbody tr")
        )

        for item in items[:30]:
            try:
                title_el = item.find(["h2", "h3", "h4", "a"])
                title = self.safe_text(title_el) if title_el else ""
                if not title or len(title) < 5:
                    continue

                link_el = item.find("a", href=True)
                source_url = ""
                if link_el:
                    href = str(link_el.get("href", ""))
                    source_url = href if href.startswith("http") else f"https://decision.tcc-cci.gc.ca{href}"

                party = self._extract_party(title)

                date_el = item.find("time") or item.find(
                    ["span", "div"], class_=lambda c: c and "date" in str(c).lower()
                )
                published_at = None
                if date_el:
                    date_str = date_el.get("datetime") or self.safe_text(date_el)
                    published_at = self._parse_date(str(date_str))

                results.append(
                    ScraperResult(
                        source_id=self.source_id,
                        signal_type="tax_court_dispute",
                        raw_company_name=party,
                        source_url=source_url or _TCC_HTML_URL,
                        signal_value={
                            "title": title,
                            "court": "Tax Court of Canada",
                        },
                        signal_text=f"Tax Court: {title}",
                        published_at=published_at or self._now_utc(),
                        practice_area_hints=["Tax"],
                        raw_payload={"title": title},
                        confidence_score=0.80,
                    )
                )
            except Exception as exc:
                log.warning("tax_court_html_item_error", error=str(exc))

        return results

    @staticmethod
    def _extract_party(title: str) -> str | None:
        """Extract party name from Tax Court case title."""
        # Pattern: "Name v. The Queen" or "Name v. His Majesty the King"
        match = re.match(r"(.+?)\s+v\.\s+", title, re.I)
        if match:
            name = match.group(1).strip()
            if len(name) > 2:
                return name
        return None
