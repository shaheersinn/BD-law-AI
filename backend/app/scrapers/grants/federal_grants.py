"""
Federal grants scraper.

Sources: Buyandsell.gc.ca, NSERC awards database, NRC-IRAP project listings.
Signal: federal_grant_awarded — fires when watchlist companies receive
grants > $1M (scaling signal — company will need IP/corporate counsel).
"""

from __future__ import annotations

import re

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_SOURCES = [
    {
        "name": "Buyandsell.gc.ca",
        "url": "https://buyandsell.gc.ca/procurement-data/contract-history",
        "type": "procurement",
    },
    {
        "name": "NSERC Awards",
        "url": "https://www.nserc-crsng.gc.ca/ase-ore/index_eng.asp",
        "type": "research",
    },
    {
        "name": "NRC-IRAP",
        "url": "https://nrc.canada.ca/en/support-technology-innovation",
        "type": "innovation",
    },
]

_GRANT_HIGH_VALUE = 1_000_000  # $1M


@register
class FederalGrantsScraper(BaseScraper):
    source_id = "grants_federal"
    source_name = "Federal Grants & Procurement"
    signal_types = ["federal_grant_awarded"]
    CATEGORY = "grants"
    rate_limit_rps = 0.2
    concurrency = 1
    ttl_seconds = 86400

    async def scrape(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []

        for source in _SOURCES:
            try:
                page_results = await self._scrape_source(source)
                results.extend(page_results)
            except Exception as exc:
                log.error("federal_grants_error", source=source["name"], error=str(exc))

        return results

    async def _scrape_source(self, source: dict[str, str]) -> list[ScraperResult]:
        results: list[ScraperResult] = []

        try:
            soup = await self.get_soup(source["url"])
            if not soup:
                return results
        except Exception as exc:
            log.warning("federal_grants_fetch_error", source=source["name"], error=str(exc))
            return results

        entries = (
            soup.select("table tbody tr")
            or soup.find_all("div", class_=re.compile(r"result|award|contract|grant", re.I))
            or soup.find_all("article")
        )

        for entry in entries[:50]:
            try:
                text = self.safe_text(entry)
                if not text:
                    continue

                # Extract recipient and amount
                recipient = self._extract_recipient(text)
                amount = self._extract_amount(text)

                if not recipient:
                    continue

                is_high_value = amount is not None and amount >= _GRANT_HIGH_VALUE

                title_el = entry.find(["h2", "h3", "h4", "a", "strong"])
                title = self.safe_text(title_el) if title_el else text[:100]

                link_el = entry.find("a", href=True)
                entry_url = ""
                if link_el:
                    href = str(link_el.get("href", ""))
                    if href.startswith("http"):
                        entry_url = href

                results.append(
                    ScraperResult(
                        source_id=self.source_id,
                        signal_type="federal_grant_awarded",
                        raw_company_name=recipient,
                        source_url=entry_url or source["url"],
                        signal_value={
                            "recipient": recipient,
                            "amount_cad": amount,
                            "source_name": source["name"],
                            "grant_type": source["type"],
                            "is_high_value": is_high_value,
                            "title": title,
                        },
                        signal_text=(
                            f"Grant ({source['name']}): {recipient}"
                            + (f" — ${amount:,}" if amount else "")
                        ),
                        published_at=self._now_utc(),
                        practice_area_hints=["Corporate / M&A", "IP"],
                        raw_payload={"text": text[:500], "source": source["name"]},
                        confidence_score=0.80 if is_high_value else 0.65,
                    )
                )
            except Exception as exc:
                log.warning("federal_grants_entry_error", error=str(exc))

        return results

    @staticmethod
    def _extract_recipient(text: str) -> str | None:
        """Extract grant recipient name."""
        patterns = [
            r"(?:vendor|supplier|recipient|awarded to|contractor)\s*[:]\s*(.+?)(?:\n|$)",
            r"^(.+?)(?:\s*[-–]\s*|\s*\$)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.I | re.M)
            if match:
                name = match.group(1).strip()
                if len(name) > 3:
                    return name
        return None

    @staticmethod
    def _extract_amount(text: str) -> int | None:
        """Extract dollar amount from text."""
        match = re.search(r"\$\s*([\d,]+(?:\.\d{2})?)", text)
        if match:
            try:
                return int(float(match.group(1).replace(",", "")))
            except ValueError:
                return None
        return None
