"""CourtListener API — free PACER alternative for cross-border US class actions."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_API_BASE = "https://www.courtlistener.com/api/rest/v4"
_SEARCH_URL = f"{_API_BASE}/search/"
_STALE_DAYS = 90

_CANADIAN_COMPANY_KEYWORDS = [
    "Canadian",
    "Canada",
    "Toronto",
    "Ontario",
    "Alberta",
    "British Columbia",
    "Quebec",
    "Ltd.",
    "Inc.",
    "Corp.",
]

_KEYWORD_PA_MAP: dict[str, str] = {
    "securities": "securities_capital_markets",
    "investor": "securities_capital_markets",
    "shareholder": "securities_capital_markets",
    "10b-5": "securities_capital_markets",
    "sec fraud": "securities_capital_markets",
    "privacy": "privacy_cybersecurity",
    "data breach": "data_privacy_technology",
    "cyber": "privacy_cybersecurity",
    "employment": "employment_labour",
    "labor": "employment_labour",
    "wage": "employment_labour",
    "flsa": "employment_labour",
    "environmental": "environmental_indigenous_energy",
    "epa": "environmental_indigenous_energy",
    "product": "product_liability",
    "recall": "product_liability",
    "consumer": "product_liability",
    "antitrust": "competition_antitrust",
    "price-fixing": "competition_antitrust",
    "sherman act": "competition_antitrust",
    "pension": "pension_benefits",
    "erisa": "pension_benefits",
    "insurance": "insurance_reinsurance",
    "pharmaceutical": "health_life_sciences",
    "drug": "health_life_sciences",
    "fda": "health_life_sciences",
    "patent": "intellectual_property",
    "trademark": "intellectual_property",
    "copyright": "intellectual_property",
}

_DEFENDANT_RE = re.compile(
    r"(?:v\.?|vs\.?)\s+(.+?)(?:\s*,\s*(?:et al|No\.)|\s*$)",
    re.IGNORECASE,
)


def _infer_practice_areas(text: str) -> list[str]:
    """Map keywords in text to valid PRACTICE_AREA_BITS keys."""
    lower = text.lower()
    areas: set[str] = {"class_actions", "litigation"}
    for kw, pa in _KEYWORD_PA_MAP.items():
        if kw in lower:
            areas.add(pa)
    if "securities" in lower or "10b" in lower:
        areas.add("securities_capital_markets")
    return sorted(areas)


def _extract_company_name(case_name: str) -> str | None:
    """Try to extract the defendant company name from a US case caption."""
    m = _DEFENDANT_RE.search(case_name)
    if m:
        name = m.group(1).strip()
        name = re.sub(r"\s*et\s+al\.?\s*$", "", name, flags=re.IGNORECASE).strip()
        if len(name) > 2:
            return name
    parts = case_name.split(" v. ")
    if len(parts) < 2:
        parts = case_name.split(" v ")
    if len(parts) >= 2:
        candidate = parts[-1].strip()
        candidate = re.sub(r"\s*et\s+al\.?\s*$", "", candidate, flags=re.IGNORECASE).strip()
        if len(candidate) > 2:
            return candidate
    return None


def _has_canadian_nexus(case_data: dict[str, Any]) -> bool:
    """Check whether a case has a Canadian company or entity connection."""
    text = f"{case_data.get('caseName', '')} {case_data.get('suitNature', '')}".lower()
    return any(kw.lower() in text for kw in _CANADIAN_COMPANY_KEYWORDS)


@register
class CourtListenerClassActionsScraper(BaseScraper):
    source_id = "class_actions_courtlistener"
    source_name = "CourtListener PACER Class Actions"
    signal_types = ["class_action_filed_us", "class_action_certified_us"]
    CATEGORY = "class_actions"
    rate_limit_rps = 0.5
    concurrency = 2
    ttl_seconds = 21600

    async def scrape(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []
        try:
            cutoff = datetime.now(tz=UTC) - timedelta(days=_STALE_DAYS)
            cutoff_str = cutoff.strftime("%Y-%m-%d")

            params = {
                "type": "o",
                "q": '"class action"',
                "filed_after": cutoff_str,
                "order_by": "dateFiled desc",
                "page_size": 50,
            }

            data = await self.get_json(_SEARCH_URL, params=params)
            if not data or "results" not in data:
                return results

            for item in data["results"]:
                case_name = item.get("caseName", "") or item.get("case_name", "")
                if not case_name:
                    continue

                if not _has_canadian_nexus(item):
                    continue

                filed_date_str = item.get("dateFiled") or item.get("date_filed")
                pub_date = self._parse_date(filed_date_str)
                if pub_date and pub_date < cutoff:
                    continue

                absolute_url = item.get("absolute_url", "")
                url = f"https://www.courtlistener.com{absolute_url}" if absolute_url else None

                company = _extract_company_name(case_name)
                pa_hints = _infer_practice_areas(case_name)
                nature = (item.get("suitNature") or "").lower()
                signal_type = (
                    "class_action_certified_us"
                    if "certified" in nature or "certified" in case_name.lower()
                    else "class_action_filed_us"
                )

                results.append(
                    ScraperResult(
                        source_id=self.source_id,
                        signal_type=signal_type,
                        raw_company_name=company,
                        source_url=url,
                        signal_value={
                            "case_name": case_name,
                            "court": item.get("court", ""),
                            "nature_of_suit": item.get("suitNature", ""),
                            "docket_number": item.get("docketNumber", ""),
                        },
                        signal_text=f"US class action (cross-border): {case_name}",
                        confidence_score=0.75,
                        published_at=pub_date,
                        practice_area_hints=pa_hints,
                        raw_payload=dict(item),
                    )
                )

            await self._rate_limit_sleep()

        except Exception as exc:
            log.error("courtlistener_scrape_error", error=str(exc), exc_info=True)
        return results

    async def health_check(self) -> bool:
        try:
            resp = await self.get(f"{_API_BASE}/search/?type=o&q=test&page_size=1")
            return resp.status_code == 200
        except Exception:
            return False
