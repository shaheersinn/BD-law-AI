"""
app/scrapers/consumer/transport_canada_recalls.py — Transport Canada vehicle & equipment recalls.

Source: https://tc.canada.ca/en/road-transportation/safety-regulations-compliance/
        vehicle-safety-defects-recalls/defect-investigations-recalls
RSS:    https://tc.canada.ca/en/corporate-services/newsroom/rss-feeds

What it scrapes:
  - Vehicle, tire, and child car seat recalls
  - Extracts: vehicle make/model, recall reason, units affected, manufacturer

Signal types:
  - recall_transport_canada: vehicle/equipment recall from Transport Canada

Practice areas: product_liability, class_actions
"""

from __future__ import annotations

import xml.etree.ElementTree as ET  # nosec B405

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_RSS_URL = "https://tc.canada.ca/en/feed/recalls"
_FALLBACK_URL = "https://tc.canada.ca/en/road-transportation/safety-regulations-compliance/vehicle-safety-defects-recalls"
_SAFERCAR_API = "https://api.nhtsa.gov/recalls/recallsByVehicle"

_PRACTICE_AREAS = ["product_liability", "class_actions"]

# Canadian auto brands frequently subject to class actions
_AUTO_MANUFACTURERS = {
    "honda",
    "toyota",
    "ford",
    "gm",
    "general motors",
    "chrysler",
    "stellantis",
    "fca",
    "volkswagen",
    "vw",
    "bmw",
    "mercedes",
    "hyundai",
    "kia",
    "subaru",
    "nissan",
    "mazda",
    "tesla",
    "jeep",
    "dodge",
    "ram",
    "chevrolet",
}


@register
class TransportCanadaRecallsScraper(BaseScraper):
    source_id = "consumer_transport_canada_recalls"
    source_name = "Transport Canada Vehicle Recalls"
    CATEGORY = "consumer"
    signal_types = ["recall_transport_canada"]
    rate_limit_rps = 0.2
    concurrency = 1
    ttl_seconds = 3600

    async def scrape(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []
        try:
            response = await self.get(_RSS_URL)
            if response.status_code == 200:
                results.extend(self._parse_rss(response.text))
            else:
                log.warning(
                    "transport_canada_rss_unavailable",
                    status=response.status_code,
                    fallback=_FALLBACK_URL,
                )
        except Exception as exc:
            log.error("transport_canada_recalls_error", error=str(exc))

        return results

    def _parse_rss(self, xml_text: str) -> list[ScraperResult]:
        results: list[ScraperResult] = []
        try:
            root = ET.fromstring(xml_text)  # nosec B314 — trusted government RSS
        except ET.ParseError as exc:
            log.warning("transport_canada_parse_error", error=str(exc))
            return results

        for item in root.iter("item"):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            pub_date = (item.findtext("pubDate") or "").strip()
            description = (item.findtext("description") or "").strip()

            # Only process vehicle/equipment recalls
            if not self._is_vehicle_recall(title, description):
                continue

            manufacturer = self._extract_manufacturer(title, description)
            units_str = self._extract_units(title, description)

            results.append(
                ScraperResult(
                    source_id=self.source_id,
                    signal_type="recall_transport_canada",
                    raw_company_name=manufacturer,
                    source_url=link or _FALLBACK_URL,
                    signal_value={
                        "title": title,
                        "manufacturer": manufacturer,
                        "units_affected": units_str,
                        "date": pub_date,
                        "description": description[:500],
                    },
                    signal_text=f"Transport Canada Recall: {title}",
                    confidence_score=0.9,
                    published_at=self._parse_date(pub_date),
                    practice_area_hints=_PRACTICE_AREAS,
                    raw_payload={"title": title, "link": link, "description": description},
                )
            )

        return results

    @staticmethod
    def _is_vehicle_recall(title: str, description: str) -> bool:
        text = f"{title} {description}".lower()
        return any(
            k in text
            for k in ["vehicle", "recall", "tire", "car seat", "automobile", "truck", "suv"]
        )

    @staticmethod
    def _extract_manufacturer(title: str, description: str) -> str | None:
        text = f"{title} {description}".lower()
        for brand in _AUTO_MANUFACTURERS:
            if brand in text:
                return brand.title()
        return None

    @staticmethod
    def _extract_units(title: str, description: str) -> str | None:
        import re  # noqa: PLC0415

        text = f"{title} {description}"
        match = re.search(r"([\d,]+)\s*(vehicle|unit|car|truck)", text, re.IGNORECASE)
        if match:
            return match.group(1).replace(",", "")
        return None
