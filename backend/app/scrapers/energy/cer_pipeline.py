"""
CER pipeline incident and compliance scraper.

Sources: Canada Energy Regulator (CER) incidents, compliance, and open data.
Signal: cer_pipeline_incident — fires on significant incidents,
non-compliance orders, and audit findings for pipeline operators.
"""

from __future__ import annotations

import re

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_CER_INCIDENTS_URL = (
    "https://www.cer-rec.gc.ca/en/safety-environment/industry-performance/pipeline-incidents/"
)
_CER_COMPLIANCE_URL = "https://www.cer-rec.gc.ca/en/safety-environment/compliance/"
_CER_OPEN_DATA_URL = "https://open.canada.ca/data/en/dataset/7dffedc4-23fa-4b36-9cc3-d3f3d3d4f66b"


@register
class CERPipelineScraper(BaseScraper):
    source_id = "energy_cer_pipeline"
    source_name = "Canada Energy Regulator"
    signal_types = ["cer_pipeline_incident"]
    CATEGORY = "energy"
    rate_limit_rps = 0.2
    concurrency = 1
    ttl_seconds = 14400

    async def scrape(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []

        for url, context in [
            (_CER_INCIDENTS_URL, "incident"),
            (_CER_COMPLIANCE_URL, "compliance"),
        ]:
            try:
                page_results = await self._scrape_page(url, context)
                results.extend(page_results)
            except Exception as exc:
                log.error("cer_pipeline_error", context=context, error=str(exc))

        return results

    async def _scrape_page(self, url: str, context: str) -> list[ScraperResult]:
        results: list[ScraperResult] = []

        try:
            soup = await self.get_soup(url)
            if not soup:
                return results
        except Exception as exc:
            log.warning("cer_fetch_error", url=url, error=str(exc))
            return results

        entries = (
            soup.select("table tbody tr")
            or soup.find_all("div", class_=re.compile(r"incident|result|item", re.I))
            or soup.find_all("article")
        )

        for entry in entries[:30]:
            try:
                text = self.safe_text(entry)
                if not text or len(text) < 10:
                    continue

                title_el = entry.find(["h2", "h3", "h4", "a", "strong"])
                title = self.safe_text(title_el) if title_el else text[:100]

                company = self._extract_company(text)

                link_el = entry.find("a", href=True)
                source_url = ""
                if link_el:
                    href = str(link_el.get("href", ""))
                    if href.startswith("http"):
                        source_url = href
                    elif href.startswith("/"):
                        source_url = f"https://www.cer-rec.gc.ca{href}"

                # Determine severity
                text_lower = text.lower()
                is_significant = any(
                    kw in text_lower
                    for kw in [
                        "significant",
                        "serious",
                        "fatality",
                        "release",
                        "non-compliance",
                        "order",
                        "violation",
                    ]
                )

                results.append(
                    ScraperResult(
                        source_id=self.source_id,
                        signal_type="cer_pipeline_incident",
                        raw_company_name=company,
                        source_url=source_url or url,
                        signal_value={
                            "title": title,
                            "context": context,
                            "is_significant": is_significant,
                            "regulator": "CER",
                        },
                        signal_text=f"CER {context}: {title}",
                        published_at=self._now_utc(),
                        practice_area_hints=[
                            "Environmental",
                            "Energy Regulatory",
                        ],
                        raw_payload={"title": title, "text": text[:500], "context": context},
                        confidence_score=0.85 if is_significant else 0.70,
                    )
                )
            except Exception as exc:
                log.warning("cer_entry_error", error=str(exc))

        return results

    @staticmethod
    def _extract_company(text: str) -> str | None:
        """Extract pipeline operator/company name."""
        patterns = [
            r"(?:company|operator|pipeline)\s*[:]\s*(.+?)(?:\n|$)",
            r"^(.+?)\s*[-–]\s*(?:pipeline|incident)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.I | re.M)
            if match:
                name = match.group(1).strip()
                if len(name) > 3:
                    return name
        return None
