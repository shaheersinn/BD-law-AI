"""Branch MacMaster LLP — major BC class action firm."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_BASE_URL = "https://www.branmac.com/class-actions/"
_STALE_DAYS = 90

_KEYWORD_PA_MAP: dict[str, str] = {
    "securities": "securities_capital_markets",
    "investor": "securities_capital_markets",
    "shareholder": "securities_capital_markets",
    "privacy": "privacy_cybersecurity",
    "data breach": "data_privacy_technology",
    "cyber": "privacy_cybersecurity",
    "employment": "employment_labour",
    "labour": "employment_labour",
    "worker": "employment_labour",
    "wage": "employment_labour",
    "environmental": "environmental_indigenous_energy",
    "pollution": "environmental_indigenous_energy",
    "product": "product_liability",
    "recall": "product_liability",
    "consumer": "product_liability",
    "competition": "competition_antitrust",
    "price-fixing": "competition_antitrust",
    "antitrust": "competition_antitrust",
    "pension": "pension_benefits",
    "insurance": "insurance_reinsurance",
    "pharmaceutical": "health_life_sciences",
    "drug": "health_life_sciences",
    "medical": "health_life_sciences",
}

_DEFENDANT_RE = re.compile(
    r"(?:v\.?|vs\.?|against)\s+(.+?)(?:\s*[-–—,]|\s+class\s+action|\s*$)",
    re.IGNORECASE,
)


def _infer_practice_areas(text: str) -> list[str]:
    """Map keywords in text to valid PRACTICE_AREA_BITS keys."""
    lower = text.lower()
    areas: set[str] = {"class_actions", "litigation"}
    for kw, pa in _KEYWORD_PA_MAP.items():
        if kw in lower:
            areas.add(pa)
    return sorted(areas)


def _extract_company_name(title: str) -> str | None:
    """Try to extract the defendant company name from a case title."""
    m = _DEFENDANT_RE.search(title)
    if m:
        name = m.group(1).strip()
        if len(name) > 2:
            return name
    parts = title.split(" v. ")
    if len(parts) < 2:
        parts = title.split(" v ")
    if len(parts) >= 2:
        candidate = parts[-1].strip().rstrip(".")
        if len(candidate) > 2:
            return candidate
    return None


@register
class BranchMacMasterClassActionsScraper(BaseScraper):
    source_id = "class_actions_branch_macmaster"
    source_name = "Branch MacMaster LLP Class Actions"
    signal_types = ["class_action_investigation"]
    CATEGORY = "class_actions"
    rate_limit_rps = 0.5
    concurrency = 1
    ttl_seconds = 21600

    async def scrape(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []
        try:
            soup = await self.get_soup(_BASE_URL)
            if soup is None:
                return results

            cutoff = datetime.now(tz=UTC) - timedelta(days=_STALE_DAYS)
            articles = soup.select("article, .case-item, .entry, .post, .class-action")
            if not articles:
                articles = soup.select("a[href*='class-action']")

            for item in articles[:50]:
                title = self.safe_text(item.find(["h2", "h3", "h4", "a"]))
                if not title:
                    continue

                link_el = item.find("a", href=True)
                url = link_el["href"] if link_el else None
                if url and not url.startswith("http"):
                    url = f"https://www.branmac.com{url}"

                date_el = item.find(["time", "span"], class_=re.compile(r"date|time|posted"))
                pub_date = self._parse_date(self.safe_text(date_el)) if date_el else None
                if pub_date and pub_date < cutoff:
                    continue

                company = _extract_company_name(title)
                pa_hints = _infer_practice_areas(title)

                results.append(
                    ScraperResult(
                        source_id=self.source_id,
                        signal_type="class_action_investigation",
                        raw_company_name=company,
                        source_url=url,
                        signal_value={"title": title, "firm": "Branch MacMaster LLP"},
                        signal_text=f"Branch MacMaster class action: {title}",
                        confidence_score=0.75,
                        published_at=pub_date,
                        practice_area_hints=pa_hints,
                        raw_payload={"title": title, "url": url, "date": str(pub_date)},
                    )
                )
        except Exception as exc:
            log.error("branch_macmaster_scrape_error", error=str(exc), exc_info=True)
        return results

    async def health_check(self) -> bool:
        try:
            resp = await self.get(_BASE_URL)
            return resp.status_code == 200
        except Exception:
            return False
