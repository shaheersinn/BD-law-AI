"""Registre des actions collectives du Québec — English section only."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta

import structlog
from bs4 import BeautifulSoup, Tag

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_BASE_URL = "https://www.registredesactionscollectives.gouv.qc.ca/en"

_KEYWORD_PA_MAP: dict[str, str] = {
    "securities": "securities_capital_markets",
    "stock": "securities_capital_markets",
    "investor": "securities_capital_markets",
    "shareholder": "securities_capital_markets",
    "privacy": "privacy_cybersecurity",
    "data breach": "data_privacy_technology",
    "cyber": "privacy_cybersecurity",
    "employment": "employment_labour",
    "labour": "employment_labour",
    "labor": "employment_labour",
    "wage": "employment_labour",
    "environmental": "environmental_indigenous_energy",
    "pollution": "environmental_indigenous_energy",
    "contamination": "environmental_indigenous_energy",
    "product": "product_liability",
    "defect": "product_liability",
    "recall": "product_liability",
    "competition": "competition_antitrust",
    "price-fixing": "competition_antitrust",
    "antitrust": "competition_antitrust",
    "insurance": "insurance_reinsurance",
    "pension": "pension_benefits",
    "benefit": "pension_benefits",
}

_DEFENDANT_RE = re.compile(
    r"(?:v\.|vs\.?|against|c\.)\s+(.+?)(?:\s+et\s+al\.?)?$",
    re.IGNORECASE,
)


@register
class QuebecClassProceedingsScraper(BaseScraper):
    source_id = "class_actions_quebec"
    source_name = "Registre des actions collectives du Québec"
    CATEGORY = "class_actions"
    signal_types = ["class_action_filed", "class_action_certified"]
    rate_limit_rps = 0.2
    concurrency = 1
    ttl_seconds = 43200

    async def scrape(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []
        try:
            resp = await self.get(_BASE_URL)
            if resp.status_code != 200:
                log.warning("quebec_class_non200", status=resp.status_code)
                return results

            soup = BeautifulSoup(resp.text, "lxml")
            cutoff = datetime.now(tz=UTC) - timedelta(days=90)

            rows = soup.select("table tr, .views-row, .item-list li")
            for row in rows[:80]:
                try:
                    result = self._parse_row(row, cutoff)
                    if result:
                        results.append(result)
                except Exception as exc:
                    log.debug("quebec_class_row_skip", error=str(exc))
                    continue

            await self._rate_limit_sleep()
        except Exception as exc:
            log.error("quebec_class_error", error=str(exc))
        return results

    def _parse_row(
        self, row: Tag, cutoff: datetime
    ) -> ScraperResult | None:
        text = self.safe_text(row)
        if not text or len(text) < 10:
            return None

        if self._is_french_only(text):
            return None

        link_tag = row.find("a")
        source_url = None
        if link_tag and link_tag.get("href"):
            href = str(link_tag["href"])
            if href.startswith("http"):
                source_url = href
            else:
                source_url = f"https://www.registredesactionscollectives.gouv.qc.ca{href}"

        cells = row.find_all("td") if row.name == "tr" else []
        date_str = self.safe_text(cells[-1]) if len(cells) >= 2 else None
        published = self._parse_date(date_str)
        if published and published < cutoff:
            return None

        case_title = self.safe_text(cells[0]) if cells else text
        company = self._extract_company_name(case_title)
        signal_type = "class_action_certified" if "certified" in text.lower() or "autorisé" in text.lower() else "class_action_filed"
        hints = self._infer_practice_areas(text)

        court_file = ""
        file_match = re.search(r"(?:No\.?|500-06)\s*[\-:]?\s*([\w\-/]+)", text)
        if file_match:
            court_file = file_match.group(0).strip()

        return ScraperResult(
            source_id=self.source_id,
            signal_type=signal_type,
            raw_company_name=company,
            source_url=source_url,
            signal_value={
                "case_title": case_title,
                "court_file_number": court_file,
                "status": signal_type.replace("class_action_", ""),
            },
            signal_text=f"Quebec class proceeding: {case_title}",
            published_at=published,
            practice_area_hints=hints,
            raw_payload={"case_title": case_title, "raw_text": text[:500]},
            confidence_score=0.80,
        )

    async def health_check(self) -> bool:
        try:
            resp = await self.get(_BASE_URL)
            return resp.status_code == 200
        except Exception:
            return False

    @staticmethod
    def _is_french_only(text: str) -> bool:
        french_markers = ["recours collectif", "demandeur", "défendeur", "jugement"]
        lower = text.lower()
        french_hits = sum(1 for m in french_markers if m in lower)
        english_markers = ["class action", "plaintiff", "defendant", "court", "judgment"]
        english_hits = sum(1 for m in english_markers if m in lower)
        return french_hits >= 2 and english_hits == 0

    @staticmethod
    def _extract_company_name(title: str) -> str | None:
        match = _DEFENDANT_RE.search(title)
        if match:
            name = match.group(1).strip().rstrip(".")
            if len(name) > 2:
                return name
        return None

    @staticmethod
    def _infer_practice_areas(text: str) -> list[str]:
        hints: set[str] = {"class_actions", "litigation"}
        lower = text.lower()
        for keyword, pa in _KEYWORD_PA_MAP.items():
            if keyword in lower:
                hints.add(pa)
        return sorted(hints)
