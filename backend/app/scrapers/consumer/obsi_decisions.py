"""
app/scrapers/consumer/obsi_decisions.py — OBSI (Ombudsman for Banking Services and Investments).

Source: https://www.obsi.ca/en/decisions
        https://www.obsi.ca/en/news

What it scrapes:
  - OBSI decisions and case reports against financial institutions
  - Annual reports with complaint statistics by firm
  - Cases not resolved by financial institution → escalated to OBSI

Signal types:
  - consumer_complaint_financial: OBSI complaint/decision against financial firm

Practice areas: class_actions, banking_finance, securities_capital_markets

Why: Unresolved OBSI complaints at scale → securities/banking class actions.
     OBSI publishes "non-compliant" banks — those institutions face class action risk.
"""

from __future__ import annotations

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_OBSI_DECISIONS_URL = "https://www.obsi.ca/en/decisions"
_OBSI_NEWS_URL = "https://www.obsi.ca/en/news"
_OBSI_REPORTS_URL = "https://www.obsi.ca/en/annual-reports"
_OBSI_BASE = "https://www.obsi.ca"

_PRACTICE_AREAS = ["class_actions", "banking_finance", "securities_capital_markets"]

# Financial institutions with OBSI exposure
_FI_KEYWORDS = [
    "bank",
    "credit union",
    "caisse",
    "investment",
    "broker",
    "dealer",
    "mutual fund",
    "portfolio",
    "advisor",
    "insurance",
    "td",
    "rbc",
    "bmo",
    "cibc",
    "scotiabank",
    "desjardins",
    "national bank",
    "manulife",
    "sunlife",
    "great-west",
    "canada life",
]


@register
class OBSIDecisionsScraper(BaseScraper):
    source_id = "consumer_obsi_decisions"
    source_name = "OBSI Ombudsman for Banking Services and Investments"
    CATEGORY = "consumer"
    signal_types = ["consumer_complaint_financial"]
    rate_limit_rps = 0.1
    concurrency = 1
    ttl_seconds = 21600  # 6-hour cache; decisions updated infrequently

    async def scrape(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []
        results.extend(await self._scrape_decisions_page())
        results.extend(await self._scrape_news_page())
        return results

    async def _scrape_decisions_page(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []
        try:
            soup = await self.get_soup(_OBSI_DECISIONS_URL)
            if soup is None:
                return results

            # OBSI decisions page has summary cards / table rows
            for item in soup.select("article, .decision-item, .case-summary, tr"):
                title_el = item.find(["h2", "h3", "h4", "a", "td"])
                if not title_el:
                    continue
                title = self.safe_text(title_el)
                if not title or len(title) < 10:
                    continue

                link_el = item.find("a", href=True)
                url = ""
                if link_el:
                    href = link_el.get("href", "")
                    url = href if href.startswith("http") else f"{_OBSI_BASE}{href}"

                description_el = item.find(["p", ".summary", ".description"])
                description = self.safe_text(description_el) if description_el else ""

                date_el = item.find(["time", ".date", ".published"])
                date_str = self.safe_text(date_el) if date_el else ""

                firm = self._extract_firm(title, description)

                results.append(
                    ScraperResult(
                        source_id=self.source_id,
                        signal_type="consumer_complaint_financial",
                        raw_company_name=firm,
                        source_url=url or _OBSI_DECISIONS_URL,
                        signal_value={
                            "title": title,
                            "firm": firm,
                            "date": date_str,
                            "description": description[:500],
                            "source": "obsi_decisions",
                        },
                        signal_text=f"OBSI Decision: {title}",
                        confidence_score=0.85,
                        published_at=self._parse_date(date_str),
                        practice_area_hints=_PRACTICE_AREAS,
                        raw_payload={"title": title, "url": url, "description": description},
                    )
                )
                await self._rate_limit_sleep()

        except Exception as exc:
            log.error("obsi_decisions_scrape_error", error=str(exc))

        return results

    async def _scrape_news_page(self) -> list[ScraperResult]:
        """Parse OBSI news for non-compliance announcements (high class action signal)."""
        results: list[ScraperResult] = []
        try:
            soup = await self.get_soup(_OBSI_NEWS_URL)
            if soup is None:
                return results

            for item in soup.select("article, .news-item, li.news"):
                title_el = item.find(["h2", "h3", "a"])
                if not title_el:
                    continue
                title = self.safe_text(title_el)
                if not title:
                    continue

                # Non-compliance announcements are highest-value signals
                if not self._is_compliance_signal(title):
                    continue

                link_el = item.find("a", href=True)
                url = ""
                if link_el:
                    href = link_el.get("href", "")
                    url = href if href.startswith("http") else f"{_OBSI_BASE}{href}"

                results.append(
                    ScraperResult(
                        source_id=self.source_id,
                        signal_type="consumer_complaint_financial",
                        raw_company_name=self._extract_firm(title, ""),
                        source_url=url or _OBSI_NEWS_URL,
                        signal_value={
                            "title": title,
                            "source": "obsi_news",
                            "is_noncompliance": "non-compli" in title.lower(),
                        },
                        signal_text=f"OBSI News: {title}",
                        confidence_score=0.9 if "non-compli" in title.lower() else 0.7,
                        practice_area_hints=_PRACTICE_AREAS,
                        raw_payload={"title": title, "url": url},
                    )
                )
                await self._rate_limit_sleep()

        except Exception as exc:
            log.error("obsi_news_scrape_error", error=str(exc))

        return results

    @staticmethod
    def _is_compliance_signal(title: str) -> bool:
        text = title.lower()
        return any(
            k in text
            for k in [
                "non-complian",
                "refus",
                "decision",
                "award",
                "recommend",
                "investig",
                "settlement",
                "complaint",
                "case",
            ]
        )

    @staticmethod
    def _extract_firm(title: str, description: str) -> str | None:
        text = f"{title} {description}".lower()
        for keyword in _FI_KEYWORDS:
            if keyword in text:
                # Try to extract the surrounding company name
                idx = text.index(keyword)
                window = f"{title} {description}"
                start = max(0, idx - 20)
                candidate = window[start : idx + len(keyword) + 30].strip()
                candidate = candidate.split(".")[0].split(",")[0].strip()
                if 3 < len(candidate) < 60:
                    return candidate
        return None
