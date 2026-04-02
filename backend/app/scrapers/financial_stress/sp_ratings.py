"""
S&P Global Ratings downgrade scraper.

Source: S&P Global Ratings alerts RSS/HTML.
Signal: credit_rating_downgrade_sp — fires when Canadian issuers are
downgraded. Enhanced to 0.93 when concurrent with DBRS downgrade.
"""

from __future__ import annotations

import re

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_SP_ALERTS_URL = (
    "https://www.spglobal.com/ratings/en/research-insights/articles/ratingsdirect-alerts"
)


@register
class SPRatingsScraper(BaseScraper):
    source_id = "financial_stress_sp_ratings"
    source_name = "S&P Global Ratings"
    signal_types = ["credit_rating_downgrade_sp"]
    CATEGORY = "financial_stress"
    rate_limit_rps = 0.2
    concurrency = 1
    ttl_seconds = 7200

    async def scrape(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []

        try:
            soup = await self.get_soup(_SP_ALERTS_URL)
            if not soup:
                return results
        except Exception as exc:
            log.error("sp_ratings_fetch_error", error=str(exc))
            return results

        # Parse alert entries
        alert_elements = (
            soup.find_all("div", class_=re.compile(r"article|alert|card|item", re.I))
            or soup.find_all("article")
            or soup.find_all("li", class_=re.compile(r"article|alert", re.I))
        )

        for alert in alert_elements[:40]:
            try:
                text = self.safe_text(alert)
                if not text:
                    continue

                text_lower = text.lower()

                # Filter for downgrades of Canadian issuers
                is_downgrade = any(
                    kw in text_lower
                    for kw in [
                        "downgrade",
                        "lowered",
                        "revised to",
                        "outlook negative",
                        "creditwatch negative",
                    ]
                )
                if not is_downgrade:
                    continue

                is_canadian = any(
                    kw in text_lower
                    for kw in [
                        "canada",
                        "canadian",
                        "toronto",
                        "calgary",
                        "vancouver",
                        "montreal",
                        "tsx",
                        "ontario",
                        "alberta",
                        "british columbia",
                        "quebec",
                    ]
                )
                if not is_canadian:
                    continue

                title_el = alert.find(["h2", "h3", "h4", "a"])
                title = self.safe_text(title_el) if title_el else text[:100]

                issuer = self._extract_issuer(title, text)

                link_el = alert.find("a", href=True)
                source_url = ""
                if link_el:
                    href = str(link_el.get("href", ""))
                    if href.startswith("http"):
                        source_url = href

                # Extract rating details
                rating_from, rating_to = self._extract_ratings(text)

                date_el = alert.find("time") or alert.find(
                    ["span"], class_=lambda c: c and "date" in str(c).lower()
                )
                published_at = None
                if date_el:
                    date_str = date_el.get("datetime") or self.safe_text(date_el)
                    published_at = self._parse_date(str(date_str))

                results.append(
                    ScraperResult(
                        source_id=self.source_id,
                        signal_type="credit_rating_downgrade_sp",
                        raw_company_name=issuer,
                        source_url=source_url or _SP_ALERTS_URL,
                        signal_value={
                            "issuer": issuer or title,
                            "rating_from": rating_from,
                            "rating_to": rating_to,
                            "action": "downgrade",
                            "agency": "S&P",
                        },
                        signal_text=f"S&P downgrade: {title}",
                        published_at=published_at or self._now_utc(),
                        practice_area_hints=[
                            "Restructuring / Insolvency",
                            "Banking & Finance",
                        ],
                        raw_payload={"title": title, "text": text[:500]},
                        confidence_score=0.85,
                    )
                )
            except Exception as exc:
                log.warning("sp_ratings_alert_error", error=str(exc))

        return results

    @staticmethod
    def _extract_issuer(title: str, text: str) -> str | None:
        """Extract issuer name from S&P alert."""
        combined = f"{title}\n{text}"
        patterns = [
            r"(.+?)\s+(?:downgraded|lowered|revised|outlook|creditwatch)",
            r"(?:ratings? on|rating on)\s+(.+?)\s+(?:lowered|revised|downgraded)",
        ]
        for pattern in patterns:
            match = re.search(pattern, combined, re.I)
            if match:
                name = match.group(1).strip()
                if len(name) > 3:
                    return name
        return None

    @staticmethod
    def _extract_ratings(text: str) -> tuple[str | None, str | None]:
        """Extract from/to ratings."""
        match = re.search(
            r"(?:from|was)\s+['\"]?([A-D][A-Za-z+\-]*)['\"]?\s+(?:to|lowered to)\s+['\"]?([A-D][A-Za-z+\-]*)",
            text,
            re.I,
        )
        if match:
            return match.group(1), match.group(2)
        return None, None
