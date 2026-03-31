"""
app/scrapers/class_actions/pacer_class_actions.py — US federal court class actions via CourtListener.

Data source: https://www.courtlistener.com/api/rest/v4/ (free API)
Approach: REST API (JSON) — filters for class actions mentioning Canadian companies
Signal value: HIGH — US securities class actions against dual-listed Canadian companies
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_API_BASE = "https://www.courtlistener.com/api/rest/v4"
_SEARCH_URL = f"{_API_BASE}/search/"

_CANADIAN_MARKERS = [
    "canada",
    "canadian",
    "ontario",
    "british columbia",
    "alberta",
    "quebec",
    "toronto",
    "vancouver",
    "montreal",
    "calgary",
    "tsx",
    "tsxv",
]


@register
class PACERClassActionsScraper(BaseScraper):
    """
    US federal court class actions scraper via CourtListener API.

    Filters for class actions naming companies in ORACLE's watchlist
    (TSX/TSXV listed or Canadian HQ). Uses free CourtListener API
    as PACER alternative. Rate limit: 0.5 rps (API with free tier).
    """

    source_id = "class_action_pacer"
    source_name = "CourtListener / PACER — US Class Actions"
    signal_types = ["class_action_filed_us", "class_action_certified_us"]
    CATEGORY = "class_actions"
    rate_limit_rps = 0.5
    concurrency = 1
    requires_auth = False

    async def scrape(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []
        cutoff = datetime.now(tz=UTC) - timedelta(days=90)

        try:
            after_date = cutoff.strftime("%Y-%m-%d")
            params = {
                "q": "class action",
                "type": "o",
                "filed_after": after_date,
                "order_by": "dateFiled desc",
                "format": "json",
            }

            data = await self.get_json(f"{_SEARCH_URL}?q=class+action+canada&type=o&filed_after={after_date}&order_by=dateFiled+desc")
            if not data:
                log.warning("pacer_api_empty")
                return results

            opinions = data.get("results", [])
            for opinion in opinions[:30]:
                result = self._parse_opinion(opinion, cutoff)
                if result:
                    results.append(result)

        except Exception as exc:
            log.error("pacer_scrape_error", error=str(exc))

        log.info("pacer_scrape_complete", count=len(results))
        return results

    def _parse_opinion(
        self, opinion: dict[str, Any], cutoff: datetime
    ) -> ScraperResult | None:
        case_name = opinion.get("caseName", "") or opinion.get("case_name", "")
        if not case_name or len(case_name) < 5:
            return None

        snippet = opinion.get("snippet", "") or ""
        combined = f"{case_name} {snippet}".lower()

        if not self._has_canadian_connection(combined):
            return None

        date_filed = opinion.get("dateFiled") or opinion.get("date_filed", "")
        published_at = self._parse_date(date_filed)
        if published_at and published_at < cutoff:
            return None

        absolute_url = opinion.get("absolute_url", "")
        source_url = (
            f"https://www.courtlistener.com{absolute_url}"
            if absolute_url
            else None
        )

        court = opinion.get("court", "") or ""
        docket_number = opinion.get("docketNumber", "") or opinion.get("docket_number", "")

        status = self._infer_status(snippet)
        company = self._extract_defendant(case_name)
        practice_areas = self._infer_practice_areas(case_name, snippet)

        return ScraperResult(
            source_id=self.source_id,
            signal_type=f"class_action_{status}_us",
            raw_company_name=company,
            source_url=source_url,
            signal_value={
                "case_name": case_name,
                "docket_number": docket_number,
                "jurisdiction": "US",
                "court": court,
                "status": status,
                "case_type": "class_action",
            },
            signal_text=f"US class action ({status}): {case_name}",
            published_at=published_at or self._now_utc(),
            practice_area_hints=practice_areas,
            raw_payload={
                "case_name": case_name,
                "court": court,
                "docket_number": docket_number,
                "snippet": snippet[:500],
            },
            confidence_score=0.75,
        )

    @staticmethod
    def _has_canadian_connection(text: str) -> bool:
        return any(marker in text for marker in _CANADIAN_MARKERS)

    @staticmethod
    def _extract_defendant(case_name: str) -> str | None:
        for sep in [" v. ", " v ", " vs. "]:
            if sep in case_name:
                parts = case_name.split(sep, 1)
                return parts[1].split(",")[0].split("(")[0].strip() if len(parts) > 1 else None
        return None

    @staticmethod
    def _infer_status(text: str) -> str:
        lower = text.lower()
        if "certif" in lower:
            return "certified"
        if "settl" in lower:
            return "settled"
        if "dismiss" in lower:
            return "dismissed"
        return "filed"

    @staticmethod
    def _infer_practice_areas(case_name: str, snippet: str) -> list[str]:
        areas: list[str] = ["class_actions", "litigation"]
        combined = f"{case_name} {snippet}".lower()
        if "securities" in combined or "10b-5" in combined or "shareholder" in combined:
            areas.append("securities_capital_markets")
        if "product" in combined or "defect" in combined:
            areas.append("product_liability")
        if "privacy" in combined or "data breach" in combined:
            areas.extend(["privacy_cybersecurity", "data_privacy_technology"])
        if "antitrust" in combined or "price fix" in combined:
            areas.append("competition_antitrust")
        if "employ" in combined or "wage" in combined:
            areas.append("employment_labour")
        return list(dict.fromkeys(areas))
