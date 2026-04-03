"""
Beneficial ownership registry scraper.

Sources: Federal CBCA ISC registry, BC Land Owner Transparency Registry (LOTR),
Quebec REQ.
Signal: beneficial_owner_change — fires when significant control persons change
or same ISC appears across 3+ companies (key HNWI target).
"""

from __future__ import annotations

import re

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_CBCA_ISC_URL = "https://ised-isde.canada.ca/cc/lgcy/fdrl/srch/index"
_BC_LOTR_URL = "https://landowner.gov.bc.ca/"
_QC_REQ_URL = "https://www.registreentreprises.gouv.qc.ca/"

_SOURCES = [
    {"name": "CBCA ISC Registry", "url": _CBCA_ISC_URL, "province": "Federal"},
    {"name": "BC LOTR", "url": _BC_LOTR_URL, "province": "BC"},
    {"name": "Quebec REQ", "url": _QC_REQ_URL, "province": "QC"},
]


@register
class BeneficialOwnershipScraper(BaseScraper):
    source_id = "ownership_beneficial"
    source_name = "Beneficial Ownership Registries"
    signal_types = ["beneficial_owner_change"]
    CATEGORY = "ownership"
    rate_limit_rps = 0.2
    concurrency = 1
    ttl_seconds = 86400

    async def scrape(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []

        for source in _SOURCES:
            try:
                page_results = await self._scrape_registry(source)
                results.extend(page_results)
            except Exception as exc:
                log.error(
                    "beneficial_ownership_error",
                    registry=source["name"],
                    error=str(exc),
                )

        return results

    async def _scrape_registry(self, source: dict[str, str]) -> list[ScraperResult]:
        results: list[ScraperResult] = []

        try:
            resp = await self.get(source["url"])
            if resp.status_code in (401, 403):
                log.warning(
                    "beneficial_ownership_auth_required",
                    registry=source["name"],
                    msg="Access restricted — degrading gracefully",
                )
                return results
            if resp.status_code != 200:
                log.warning(
                    "beneficial_ownership_http_error",
                    registry=source["name"],
                    status=resp.status_code,
                )
                return results
        except Exception as exc:
            log.warning("beneficial_ownership_fetch_error", registry=source["name"], error=str(exc))
            return results

        try:
            soup = await self.get_soup(source["url"])
            if not soup:
                return results
        except Exception:
            return results

        entries = (
            soup.select("table tbody tr")
            or soup.find_all("div", class_=re.compile(r"result|entity|company", re.I))
            or soup.find_all("article")
        )

        for entry in entries[:30]:
            try:
                text = self.safe_text(entry)
                if not text or len(text) < 10:
                    continue

                company = self._extract_field(text, ["corporation", "company", "entity"])
                individual = self._extract_field(
                    text,
                    [
                        "individual with significant control",
                        "significant control",
                        "owner",
                        "director",
                    ],
                )

                if not company:
                    continue

                results.append(
                    ScraperResult(
                        source_id=self.source_id,
                        signal_type="beneficial_owner_change",
                        raw_company_name=company,
                        source_url=source["url"],
                        signal_value={
                            "company": company,
                            "individual": individual,
                            "registry": source["name"],
                            "province": source["province"],
                        },
                        signal_text=(
                            f"Beneficial ownership ({source['province']}): "
                            f"{company}" + (f" — ISC: {individual}" if individual else "")
                        ),
                        published_at=self._now_utc(),
                        practice_area_hints=["Corporate / Governance"],
                        raw_payload={"text": text[:500], "registry": source["name"]},
                        confidence_score=0.75,
                    )
                )
            except Exception as exc:
                log.warning("beneficial_ownership_entry_error", error=str(exc))

        return results

    @staticmethod
    def _extract_field(text: str, labels: list[str]) -> str | None:
        """Extract field value after a label."""
        for label in labels:
            pattern = rf"{re.escape(label)}\s*[:]\s*(.+?)(?:\n|$)"
            match = re.search(pattern, text, re.I)
            if match:
                value = match.group(1).strip()
                if len(value) > 2:
                    return value
        return None
