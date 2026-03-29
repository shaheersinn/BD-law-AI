"""
app/scrapers/consumer/health_canada_recalls.py — Health Canada product recalls & safety alerts.

Source: https://recalls-rappels.canada.ca/en/search/site?f%5B0%5D=category%3A180
RSS:    https://recalls-rappels.canada.ca/en/rss

What it scrapes:
  - Health Canada product recalls and safety alerts
  - Extracts: product name, company, recall reason, date, risk level

Signal types:
  - recall_health_canada: product recall from Health Canada

Practice areas: product_liability, health_life_sciences, class_actions

Why: Product recalls are the #1 precursor to product liability class actions in Canada.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET  # nosec B405

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_RSS_URL = "https://recalls-rappels.canada.ca/en/rss"
_BASE_URL = "https://recalls-rappels.canada.ca"

_PRACTICE_AREAS = ["product_liability", "health_life_sciences", "class_actions"]


@register
class HealthCanadaRecallsScraper(BaseScraper):
    source_id = "consumer_health_canada_recalls"
    source_name = "Health Canada Recalls & Safety Alerts"
    CATEGORY = "consumer"
    signal_types = ["recall_health_canada"]
    rate_limit_rps = 0.2
    concurrency = 1
    ttl_seconds = 3600

    async def scrape(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []
        try:
            response = await self.get(_RSS_URL)
            if response.status_code != 200:
                log.warning("health_canada_recalls_bad_status", status=response.status_code)
                return results

            root = ET.fromstring(response.text)  # nosec B314 — trusted government RSS
            for item in root.iter("item"):
                title = (item.findtext("title") or "").strip()
                link = (item.findtext("link") or "").strip()
                pub_date = (item.findtext("pubDate") or "").strip()
                description = (item.findtext("description") or "").strip()
                category = (item.findtext("category") or "").strip()

                company_name = self._extract_company(title, description)
                risk_level = self._extract_risk_level(title, description)

                results.append(
                    ScraperResult(
                        source_id=self.source_id,
                        signal_type="recall_health_canada",
                        raw_company_name=company_name,
                        source_url=link or _BASE_URL,
                        signal_value={
                            "title": title,
                            "category": category,
                            "risk_level": risk_level,
                            "date": pub_date,
                            "description": description[:500],
                        },
                        signal_text=f"Health Canada Recall: {title}",
                        confidence_score=0.9,
                        published_at=self._parse_date(pub_date),
                        practice_area_hints=_PRACTICE_AREAS,
                        raw_payload={"title": title, "link": link, "description": description},
                    )
                )
                await self._rate_limit_sleep()

        except ET.ParseError as exc:
            log.error("health_canada_recalls_parse_error", error=str(exc))
        except Exception as exc:
            log.error("health_canada_recalls_error", error=str(exc))

        return results

    @staticmethod
    def _extract_company(title: str, description: str) -> str | None:
        text = f"{title} {description}".lower()
        combined = f"{title} {description}"
        # Look for "by [Company]" or "– [Company]" patterns
        for sep in [" by ", " - ", " – ", "issued by "]:
            if sep.lower() in text:
                idx = text.index(sep.lower())
                candidate = combined[idx + len(sep) : idx + len(sep) + 80].split(".")[0].strip()
                if len(candidate) > 3:
                    return candidate[:100]
        return None

    @staticmethod
    def _extract_risk_level(title: str, description: str) -> str:
        text = f"{title} {description}".lower()
        if any(k in text for k in ["death", "fatal", "serious injury", "life-threatening"]):
            return "high"
        if any(k in text for k in ["injury", "illness", "burn", "choking", "laceration"]):
            return "medium"
        return "low"
