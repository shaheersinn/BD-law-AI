"""
app/scrapers/consumer/cpsc_recalls.py — US Consumer Product Safety Commission recalls.

Source:  https://www.cpsc.gov/Recalls
RSS:     https://www.cpsc.gov/rss/recalls.xml
API:     https://www.saferproducts.gov/RestWebServices/Recall?format=json

What it scrapes:
  - CPSC product recall announcements for Canadian companies selling into the US
  - Extracts: product name, hazard description, company, units affected, remedy

Signal types:
  - recall_cpsc_us: CPSC product recall (US)

Practice areas: product_liability, class_actions

Why: Canadian companies selling in the US get CPSC recalls → cross-border class actions.
     A CPSC recall is often filed in both Canada and the US simultaneously.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET  # nosec B405

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_RSS_URL = "https://www.cpsc.gov/rss/recalls.xml"
_API_URL = "https://www.saferproducts.gov/RestWebServices/Recall"
_BASE_URL = "https://www.cpsc.gov/Recalls"

_PRACTICE_AREAS = ["product_liability", "class_actions"]

# Canadian company indicators in CPSC filings
_CANADIAN_INDICATORS = [
    "canada", "canadian", " inc.", " ltd.", " corp.", "ontario", "british columbia",
    "alberta", "quebec", "toronto", "montreal", "vancouver",
]


@register
class CPSCRecallsScraper(BaseScraper):
    source_id = "consumer_cpsc_recalls"
    source_name = "US Consumer Product Safety Commission Recalls"
    CATEGORY = "consumer"
    signal_types = ["recall_cpsc_us"]
    rate_limit_rps = 0.3
    concurrency = 1
    ttl_seconds = 3600

    async def scrape(self) -> list[ScraperResult]:
        # Try RSS first — faster and simpler
        rss_results = await self._scrape_rss()
        if rss_results:
            return rss_results
        # Fallback to JSON API
        return await self._scrape_api()

    async def _scrape_rss(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []
        try:
            response = await self.get(_RSS_URL)
            if response.status_code != 200:
                return results

            root = ET.fromstring(response.text)  # nosec B314 — trusted government RSS
            for item in root.iter("item"):
                title = (item.findtext("title") or "").strip()
                link = (item.findtext("link") or "").strip()
                pub_date = (item.findtext("pubDate") or "").strip()
                description = (item.findtext("description") or "").strip()

                company = self._extract_company(title, description)
                hazard = self._extract_hazard(description)
                is_canadian = self._is_canadian_company(title, description)

                results.append(
                    ScraperResult(
                        source_id=self.source_id,
                        signal_type="recall_cpsc_us",
                        raw_company_name=company,
                        source_url=link or _BASE_URL,
                        signal_value={
                            "title": title,
                            "company": company,
                            "hazard": hazard,
                            "is_canadian_company": is_canadian,
                            "date": pub_date,
                            "description": description[:500],
                        },
                        signal_text=f"CPSC Recall: {title}",
                        confidence_score=0.95 if is_canadian else 0.7,
                        published_at=self._parse_date(pub_date),
                        practice_area_hints=_PRACTICE_AREAS,
                        raw_payload={"title": title, "link": link, "description": description},
                    )
                )
                await self._rate_limit_sleep()

        except ET.ParseError as exc:
            log.warning("cpsc_rss_parse_error", error=str(exc))
        except Exception as exc:
            log.error("cpsc_rss_error", error=str(exc))

        return results

    async def _scrape_api(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []
        try:
            data = await self.get_json(_API_URL, params={"format": "json"})
            if not data or not isinstance(data, list):
                return results

            for recall in data[:50]:  # cap at 50 most recent
                title = recall.get("Title", "") or ""
                description = recall.get("Description", "") or ""
                company = recall.get("Firm", "") or recall.get("Importer", "") or ""
                recall_date = recall.get("RecallDate", "") or ""
                url = recall.get("URL", "") or _BASE_URL
                hazards = recall.get("Hazards", []) or []
                hazard_text = "; ".join(h.get("Name", "") for h in hazards if h.get("Name"))

                results.append(
                    ScraperResult(
                        source_id=self.source_id,
                        signal_type="recall_cpsc_us",
                        raw_company_name=company or None,
                        source_url=url,
                        signal_value={
                            "title": title,
                            "company": company,
                            "hazard": hazard_text,
                            "recall_date": recall_date,
                            "description": description[:500],
                        },
                        signal_text=f"CPSC Recall: {title}",
                        confidence_score=0.9,
                        published_at=self._parse_date(recall_date),
                        practice_area_hints=_PRACTICE_AREAS,
                        raw_payload=recall,
                    )
                )

        except Exception as exc:
            log.error("cpsc_api_error", error=str(exc))

        return results

    @staticmethod
    def _extract_company(title: str, description: str) -> str | None:
        for sep in [" by ", " from ", "sold by ", "manufactured by ", "distributed by "]:
            combined = f"{title} {description}"
            lower = combined.lower()
            if sep.lower() in lower:
                idx = lower.index(sep.lower())
                candidate = combined[idx + len(sep) : idx + len(sep) + 80].split(".")[0].strip()
                if len(candidate) > 3:
                    return candidate[:100]
        return None

    @staticmethod
    def _extract_hazard(description: str) -> str:
        text = description.lower()
        if any(k in text for k in ["fire", "burn", "flame", "smoke", "overheat"]):
            return "fire_hazard"
        if any(k in text for k in ["chok", "suffoc", "strangul"]):
            return "choking_hazard"
        if any(k in text for k in ["lacerat", "cut", "sharp edge"]):
            return "laceration_hazard"
        if any(k in text for k in ["electr", "shock", "circuit"]):
            return "electrical_hazard"
        if any(k in text for k in ["fall", "tip", "topple", "unstable"]):
            return "fall_hazard"
        if any(k in text for k in ["toxic", "poison", "chemical", "lead", "contaminat"]):
            return "chemical_hazard"
        return "other"

    @staticmethod
    def _is_canadian_company(title: str, description: str) -> bool:
        text = f"{title} {description}".lower()
        return any(indicator in text for indicator in _CANADIAN_INDICATORS)
