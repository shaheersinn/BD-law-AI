"""
Accelerator cohort scraper.

Sources: MaRS, CDL, DMZ, Communitech, L-SPARK, BetaKit RSS.
Signal: accelerator_cohort_member — fires when new companies appear in
accelerator cohort/portfolio pages.
"""

from __future__ import annotations

import re

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_ACCELERATOR_SOURCES = [
    {
        "name": "MaRS",
        "url": "https://www.marsdd.com/our-portfolio/",
    },
    {
        "name": "DMZ",
        "url": "https://dmz.torontomu.ca/startups/",
    },
    {
        "name": "CDL",
        "url": "https://www.creativedestructionlab.com/companies/",
    },
    {
        "name": "Communitech",
        "url": "https://www.communitech.ca/companies/",
    },
]


@register
class AcceleratorCohortsScraper(BaseScraper):
    source_id = "startups_accelerators"
    source_name = "Accelerator Cohorts"
    signal_types = ["accelerator_cohort_member"]
    CATEGORY = "startups"
    rate_limit_rps = 0.2
    concurrency = 1
    ttl_seconds = 86400

    async def scrape(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []

        for source in _ACCELERATOR_SOURCES:
            try:
                page_results = await self._scrape_accelerator(source)
                results.extend(page_results)
                await self._rate_limit_sleep()
            except Exception as exc:
                log.error("accelerator_error", source=source["name"], error=str(exc))

        return results

    async def _scrape_accelerator(self, source: dict[str, str]) -> list[ScraperResult]:
        results: list[ScraperResult] = []

        try:
            soup = await self.get_soup(source["url"])
            if not soup:
                return results
        except Exception as exc:
            log.warning("accelerator_fetch_error", source=source["name"], error=str(exc))
            return results

        company_elements = (
            soup.find_all("div", class_=re.compile(r"company|startup|portfolio|card", re.I))
            or soup.find_all("article")
            or soup.find_all("li", class_=re.compile(r"company|startup", re.I))
        )

        for element in company_elements[:50]:
            try:
                name_el = element.find(["h2", "h3", "h4", "a", "strong"])
                name = self.safe_text(name_el) if name_el else ""
                if not name or len(name) < 3:
                    continue

                description = self.safe_text(element)

                link_el = element.find("a", href=True)
                company_url = ""
                if link_el:
                    href = str(link_el.get("href", ""))
                    if href.startswith("http"):
                        company_url = href

                results.append(
                    ScraperResult(
                        source_id=self.source_id,
                        signal_type="accelerator_cohort_member",
                        raw_company_name=name,
                        source_url=company_url or source["url"],
                        signal_value={
                            "company_name": name,
                            "accelerator": source["name"],
                            "description": description[:200] if description else None,
                        },
                        signal_text=f"{source['name']} portfolio: {name}",
                        published_at=self._now_utc(),
                        practice_area_hints=["Corporate / M&A", "IP"],
                        raw_payload={"name": name, "accelerator": source["name"]},
                        confidence_score=0.60,
                    )
                )
            except Exception as exc:
                log.warning("accelerator_entry_error", error=str(exc))

        return results
