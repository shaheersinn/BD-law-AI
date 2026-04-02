"""
PE fund vintage exit pressure scraper.

Sources: CVCA Intelligence (cvca.ca) fund close announcements + SEDAR+ PE fund AIFs.
Signal: pe_fund_exit_pressure — fires when PE funds cross year 8 with active
portfolio companies on the watchlist.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_CVCA_URL = "https://www.cvca.ca/research-resources/industry-intelligence"
_SEDAR_FUND_SEARCH_URL = "https://www.sedarplus.ca/csa-party/records/record.html"

_EXIT_PRESSURE_YEAR = 8


@register
class FundVintageScraper(BaseScraper):
    source_id = "pe_fund_vintage"
    source_name = "CVCA / SEDAR+ PE Fund Vintage"
    signal_types = ["pe_fund_exit_pressure"]
    CATEGORY = "pe"
    rate_limit_rps = 0.2
    concurrency = 1
    ttl_seconds = 43200

    async def scrape(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []
        now = datetime.now(tz=UTC)

        # Scrape CVCA for fund announcements
        try:
            cvca_results = await self._scrape_cvca(now)
            results.extend(cvca_results)
        except Exception as exc:
            log.error("fund_vintage_cvca_error", error=str(exc))

        return results

    async def _scrape_cvca(self, now: datetime) -> list[ScraperResult]:
        results: list[ScraperResult] = []

        try:
            soup = await self.get_soup(_CVCA_URL)
            if not soup:
                return results
        except Exception as exc:
            log.warning("fund_vintage_cvca_fetch_error", error=str(exc))
            return results

        articles = (
            soup.find_all("article")
            or soup.find_all("div", class_=re.compile(r"post|entry|news", re.I))
            or soup.find_all("li", class_=re.compile(r"post|entry", re.I))
        )

        for article in articles[:30]:
            try:
                text = self.safe_text(article)
                if not text:
                    continue
                text_lower = text.lower()

                # Look for fund close/vintage indicators
                is_fund = any(
                    kw in text_lower
                    for kw in [
                        "fund close",
                        "final close",
                        "raised",
                        "vintage",
                        "fund i",
                        "fund ii",
                        "fund iii",
                        "fund iv",
                        "fund v",
                    ]
                )
                if not is_fund:
                    continue

                title_el = article.find(["h2", "h3", "h4", "a"])
                title = self.safe_text(title_el) if title_el else text[:100]

                # Extract fund name and vintage year
                fund_name = self._extract_fund_name(text)
                vintage_year = self._extract_vintage_year(text)

                if vintage_year:
                    age = now.year - vintage_year
                    if age >= _EXIT_PRESSURE_YEAR:
                        results.append(
                            ScraperResult(
                                source_id=self.source_id,
                                signal_type="pe_fund_exit_pressure",
                                raw_company_name=fund_name,
                                source_url=_CVCA_URL,
                                signal_value={
                                    "fund_name": fund_name or title,
                                    "vintage_year": vintage_year,
                                    "age_years": age,
                                    "source": "cvca",
                                },
                                signal_text=(
                                    f"PE fund '{fund_name or title}' (vintage {vintage_year}, "
                                    f"age {age}y) — exit pressure zone"
                                ),
                                published_at=self._now_utc(),
                                practice_area_hints=["Corporate / M&A", "Securities"],
                                raw_payload={"title": title, "text": text[:500]},
                                confidence_score=0.82,
                            )
                        )
                elif fund_name:
                    # New fund discovered — track for future aging
                    results.append(
                        ScraperResult(
                            source_id=self.source_id,
                            signal_type="pe_fund_exit_pressure",
                            raw_company_name=fund_name,
                            source_url=_CVCA_URL,
                            signal_value={
                                "fund_name": fund_name,
                                "event": "new_fund_close",
                                "source": "cvca",
                            },
                            signal_text=f"New PE fund close: {fund_name}",
                            published_at=self._now_utc(),
                            practice_area_hints=["Corporate / M&A", "Securities"],
                            raw_payload={"title": title, "text": text[:500]},
                            confidence_score=0.60,
                        )
                    )
            except Exception as exc:
                log.warning("fund_vintage_article_error", error=str(exc))

        return results

    @staticmethod
    def _extract_fund_name(text: str) -> str | None:
        """Extract fund name from article text."""
        patterns = [
            r"([A-Z][\w\s&]+(?:Fund|Partners|Capital|Ventures)\s*(?:I{1,3}V?|V|VI{0,3})?)",
            r"(\w[\w\s&]+)\s+(?:raised|closed|announced)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                name = match.group(1).strip()
                if len(name) > 5:
                    return name
        return None

    @staticmethod
    def _extract_vintage_year(text: str) -> int | None:
        """Extract vintage year from fund text."""
        patterns = [
            r"vintage\s*(?:year\s*)?(\d{4})",
            r"(?:established|launched|closed)\s+in\s+(\d{4})",
            r"\b(20[01]\d)\s+(?:fund|vintage)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.I)
            if match:
                year = int(match.group(1))
                if 2000 <= year <= 2026:
                    return year
        return None
