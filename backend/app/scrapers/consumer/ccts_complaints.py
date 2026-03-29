"""
app/scrapers/consumer/ccts_complaints.py — CCTS telecom complaint reports.

Source: https://www.ccts-cprst.ca/resources/annual-reports/
        https://www.ccts-cprst.ca/resources/mid-year-reports/
        https://www.ccts-cprst.ca/news/

What it scrapes:
  - CCTS annual and mid-year reports (top providers by complaint volume)
  - Press releases about complaint volumes by TSP (Telecom Service Provider)
  - Identifies providers with YoY complaint increases → class action risk

Signal types:
  - consumer_complaint_telecom: CCTS complaint report against telecom provider

Practice areas: class_actions, regulatory_compliance

Why: Rogers, Bell, Telus, Shaw, WIND — high complaint volume precedes CRTC actions
     and consumer class actions (billing, service outages, contract disputes).
"""

from __future__ import annotations

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_CCTS_NEWS_URL = "https://www.ccts-cprst.ca/news/"
_CCTS_REPORTS_URL = "https://www.ccts-cprst.ca/resources/"
_CCTS_BASE = "https://www.ccts-cprst.ca"

_PRACTICE_AREAS = ["class_actions", "regulatory_compliance"]

# Major Canadian TSPs tracked for complaint spikes
_TELCOS = [
    "rogers", "bell", "telus", "shaw", "videotron", "freedom",
    "eastlink", "cogeco", "sasktel", "mts", "wind", "public mobile",
    "koodo", "fido", "virgin", "lucky mobile",
]


@register
class CCTSComplaintsScraper(BaseScraper):
    source_id = "consumer_ccts_complaints"
    source_name = "CCTS Commission for Complaints for Telecom-television Services"
    CATEGORY = "consumer"
    signal_types = ["consumer_complaint_telecom"]
    rate_limit_rps = 0.1
    concurrency = 1
    ttl_seconds = 43200  # 12-hour cache; reports released infrequently

    async def scrape(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []
        results.extend(await self._scrape_news())
        results.extend(await self._scrape_reports())
        return results

    async def _scrape_news(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []
        try:
            soup = await self.get_soup(_CCTS_NEWS_URL)
            if soup is None:
                return results

            for item in soup.select("article, .news-item, .post, li.news"):
                title_el = item.find(["h2", "h3", "h4", "a"])
                if not title_el:
                    continue
                title = self.safe_text(title_el)
                if not title or len(title) < 10:
                    continue

                link_el = item.find("a", href=True)
                url = ""
                if link_el:
                    href = link_el.get("href", "")
                    url = href if href.startswith("http") else f"{_CCTS_BASE}{href}"

                date_el = item.find(["time", ".date"])
                date_str = self.safe_text(date_el) if date_el else ""

                description_el = item.find("p")
                description = self.safe_text(description_el) if description_el else ""

                provider = self._extract_provider(title, description)
                is_report = self._is_complaint_report(title)

                results.append(
                    ScraperResult(
                        source_id=self.source_id,
                        signal_type="consumer_complaint_telecom",
                        raw_company_name=provider,
                        source_url=url or _CCTS_NEWS_URL,
                        signal_value={
                            "title": title,
                            "provider": provider,
                            "is_annual_report": is_report,
                            "date": date_str,
                            "description": description[:500],
                        },
                        signal_text=f"CCTS Complaint Report: {title}",
                        confidence_score=0.85 if is_report else 0.7,
                        published_at=self._parse_date(date_str),
                        practice_area_hints=_PRACTICE_AREAS,
                        raw_payload={"title": title, "url": url, "description": description},
                    )
                )
                await self._rate_limit_sleep()

        except Exception as exc:
            log.error("ccts_news_scrape_error", error=str(exc))

        return results

    async def _scrape_reports(self) -> list[ScraperResult]:
        """Scrape the reports/resources page for annual and mid-year report links."""
        results: list[ScraperResult] = []
        try:
            soup = await self.get_soup(_CCTS_REPORTS_URL)
            if soup is None:
                return results

            for link_el in soup.select("a[href]"):
                href = link_el.get("href", "")
                text = self.safe_text(link_el)
                if not text:
                    continue

                if not any(k in text.lower() for k in ["annual report", "mid-year", "midyear"]):
                    continue

                url = href if href.startswith("http") else f"{_CCTS_BASE}{href}"

                results.append(
                    ScraperResult(
                        source_id=self.source_id,
                        signal_type="consumer_complaint_telecom",
                        raw_company_name=None,
                        source_url=url,
                        signal_value={
                            "title": text,
                            "report_type": "annual" if "annual" in text.lower() else "mid_year",
                            "source": "ccts_reports",
                        },
                        signal_text=f"CCTS Report Published: {text}",
                        confidence_score=0.9,
                        practice_area_hints=_PRACTICE_AREAS,
                        raw_payload={"title": text, "url": url},
                    )
                )

        except Exception as exc:
            log.error("ccts_reports_scrape_error", error=str(exc))

        return results

    @staticmethod
    def _is_complaint_report(title: str) -> bool:
        text = title.lower()
        return any(k in text for k in ["annual report", "mid-year", "complaint", "report"])

    @staticmethod
    def _extract_provider(title: str, description: str) -> str | None:
        text = f"{title} {description}".lower()
        for provider in _TELCOS:
            if provider in text:
                return provider.title()
        return None
