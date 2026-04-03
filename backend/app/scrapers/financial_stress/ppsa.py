"""
PPSA layered lending scraper.

Sources: Ontario PPSR, BC PPSR, Alberta PPSA registries.
Signal: ppsa_layered_lending — fires when 3+ distinct secured parties are
registered against the same debtor within 90 days.

NOTE: These registries may require subscription/API access. Fully degradable.
"""

from __future__ import annotations

import re

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_SOURCES = [
    {
        "name": "Ontario PPSR",
        "url": "https://www.ppsr.ontario.ca/",
        "province": "ON",
    },
    {
        "name": "BC PPSR",
        "url": "https://www.bcregistry.ca/ppr/",
        "province": "BC",
    },
    {
        "name": "Alberta PPSA",
        "url": "https://www.servicealberta.ca/find-if-personal-property-is-registered.cfm",
        "province": "AB",
    },
]


@register
class PPSAScraper(BaseScraper):
    source_id = "financial_stress_ppsa"
    source_name = "Provincial PPSA Registries"
    signal_types = ["ppsa_layered_lending"]
    CATEGORY = "financial_stress"
    rate_limit_rps = 0.2
    concurrency = 1
    ttl_seconds = 7200
    requires_auth = True  # Subscription required

    async def scrape(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []

        for source in _SOURCES:
            try:
                page_results = await self._scrape_registry(source)
                results.extend(page_results)
            except Exception as exc:
                log.error("ppsa_scrape_error", registry=source["name"], error=str(exc))

        return results

    async def _scrape_registry(self, source: dict[str, str]) -> list[ScraperResult]:
        results: list[ScraperResult] = []

        try:
            resp = await self.get(source["url"])
            if resp.status_code in (401, 403):
                log.warning(
                    "ppsa_auth_required",
                    registry=source["name"],
                    msg="Subscription required — degrading gracefully",
                )
                return results
            if resp.status_code != 200:
                log.warning("ppsa_http_error", registry=source["name"], status=resp.status_code)
                return results
        except Exception as exc:
            log.warning("ppsa_fetch_error", registry=source["name"], error=str(exc))
            return results

        try:
            soup = await self.get_soup(source["url"])
            if not soup:
                return results
        except Exception:
            return results

        # Parse registration entries
        entries = soup.select("table tbody tr") or soup.find_all(
            "div", class_=re.compile(r"registration|result", re.I)
        )

        for entry in entries[:50]:
            try:
                text = self.safe_text(entry)
                if not text:
                    continue

                debtor = self._extract_field(text, ["debtor", "name"])
                secured_party = self._extract_field(text, ["secured party", "creditor"])

                if not debtor:
                    continue

                results.append(
                    ScraperResult(
                        source_id=self.source_id,
                        signal_type="ppsa_layered_lending",
                        raw_company_name=debtor,
                        source_url=source["url"],
                        signal_value={
                            "debtor": debtor,
                            "secured_party": secured_party,
                            "registry": source["name"],
                            "province": source["province"],
                        },
                        signal_text=(
                            f"PPSA registration ({source['province']}): "
                            f"{debtor} — secured by {secured_party or 'unknown'}"
                        ),
                        published_at=self._now_utc(),
                        practice_area_hints=[
                            "Restructuring / Insolvency",
                            "Banking & Finance",
                        ],
                        raw_payload={"text": text[:500], "registry": source["name"]},
                        confidence_score=0.75,
                    )
                )
            except Exception as exc:
                log.warning("ppsa_entry_parse_error", error=str(exc))

        return results

    @staticmethod
    def _extract_field(text: str, labels: list[str]) -> str | None:
        """Extract field value following a label."""
        for label in labels:
            pattern = rf"{label}\s*[:]\s*(.+?)(?:\n|$)"
            match = re.search(pattern, text, re.I)
            if match:
                value = match.group(1).strip()
                if len(value) > 2:
                    return value
        return None
