"""
app/scrapers/class_actions/ontario_class_proceedings.py — Ontario Superior Court class proceedings.

Data source: https://www.ontariocourts.ca/scj/class-actions/
Approach: HTML scraping with BeautifulSoup
Signal value: HIGH — Ontario is Canada's largest class action jurisdiction
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_BASE_URL = "https://www.ontariocourts.ca"
_CLASS_ACTIONS_URL = f"{_BASE_URL}/scj/class-actions/"


@register
class OntarioClassProceedingsScraper(BaseScraper):
    """
    Ontario Superior Court of Justice class proceedings scraper.

    Scrapes the class proceedings list page for filed, certified,
    and settled class actions. Rate limit: 0.2 rps (government court site).
    """

    source_id = "class_action_ontario"
    source_name = "Ontario Superior Court — Class Proceedings"
    signal_types = [
        "class_action_filed",
        "class_action_certified",
        "class_action_settled",
    ]
    CATEGORY = "class_actions"
    rate_limit_rps = 0.2
    concurrency = 1
    requires_auth = False

    async def scrape(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []
        cutoff = datetime.now(tz=UTC) - timedelta(days=180)

        try:
            resp = await self.get(_CLASS_ACTIONS_URL)
            if resp.status_code != 200:
                log.warning("ontario_ca_fetch_failed", status=resp.status_code)
                return results

            from bs4 import BeautifulSoup

            soup = BeautifulSoup(resp.text, "html.parser")

            items = (
                soup.select("table tbody tr")
                or soup.select("ul.class-actions li")
                or soup.select("div.view-content div.views-row")
                or soup.select("article, div.card")
            )

            for item in items[:50]:
                result = self._parse_item(item, cutoff)
                if result:
                    results.append(result)

        except Exception as exc:
            log.error("ontario_ca_scrape_error", error=str(exc))

        log.info("ontario_ca_scrape_complete", count=len(results))
        return results

    def _parse_item(
        self, item: Any, cutoff: datetime
    ) -> ScraperResult | None:
        cells = item.find_all("td")
        if cells and len(cells) >= 2:
            return self._parse_table_row(cells, cutoff)

        title_el = item.find(["h2", "h3", "h4", "a"])
        if not title_el:
            return None
        title = self.safe_text(title_el)
        if not title or len(title) < 5:
            return None

        link_el = item.find("a", href=True)
        source_url = self._resolve_url(link_el)

        date_el = item.find("time") or item.find(
            class_=lambda c: c and "date" in str(c).lower()
        )
        published_at = None
        if date_el:
            published_at = self._parse_date(
                date_el.get("datetime") or self.safe_text(date_el)
            )

        if published_at and published_at < cutoff:
            return None

        status = self._infer_status(title)
        company = self._extract_parties(title)
        practice_areas = self._infer_practice_areas(title)

        return ScraperResult(
            source_id=self.source_id,
            signal_type=f"class_action_{status}",
            raw_company_name=company,
            source_url=source_url,
            signal_value={
                "case_name": title,
                "jurisdiction": "ON",
                "court": "Ontario Superior Court of Justice",
                "status": status,
                "case_type": "class_action",
            },
            signal_text=f"Ontario class action ({status}): {title}",
            published_at=published_at or self._now_utc(),
            practice_area_hints=practice_areas,
            raw_payload={"case_name": title, "url": source_url},
            confidence_score=0.90,
        )

    def _parse_table_row(
        self, cells: list[Any], cutoff: datetime
    ) -> ScraperResult | None:
        case_name = self.safe_text(cells[0])
        if not case_name or len(case_name) < 5:
            return None

        # Columns vary by court: try to detect layout
        if len(cells) >= 4:
            case_number = self.safe_text(cells[1])
            status_text = self.safe_text(cells[2])
            date_str = self.safe_text(cells[3])
        elif len(cells) == 3:
            case_number = ""
            status_text = self.safe_text(cells[1])
            date_str = self.safe_text(cells[2])
        else:
            case_number = ""
            status_text = self.safe_text(cells[1]) if len(cells) > 1 else ""
            date_str = ""

        published_at = self._parse_date(date_str)
        if published_at and published_at < cutoff:
            return None

        link_el = cells[0].find("a", href=True)
        source_url = self._resolve_url(link_el)

        status = self._infer_status(f"{case_name} {status_text}")
        company = self._extract_parties(case_name)
        practice_areas = self._infer_practice_areas(case_name)

        return ScraperResult(
            source_id=self.source_id,
            signal_type=f"class_action_{status}",
            raw_company_name=company,
            source_url=source_url,
            signal_value={
                "case_name": case_name,
                "case_number": case_number,
                "jurisdiction": "ON",
                "court": "Ontario Superior Court of Justice",
                "status": status,
                "case_type": "class_action",
            },
            signal_text=f"Ontario class action ({status}): {case_name}",
            published_at=published_at or self._now_utc(),
            practice_area_hints=practice_areas,
            raw_payload={
                "case_name": case_name,
                "status_text": status_text,
                "case_number": case_number,
            },
            confidence_score=0.90,
        )

    def _resolve_url(self, link_el: Any) -> str | None:
        if not link_el:
            return None
        href = str(link_el.get("href", ""))
        if not href:
            return None
        return href if href.startswith("http") else f"{_BASE_URL}{href}"

    @staticmethod
    def _extract_parties(case_name: str) -> str | None:
        for sep in [" v. ", " v ", " vs. ", " vs "]:
            if sep in case_name:
                parts = case_name.split(sep, 1)
                return parts[1].split(",")[0].split("(")[0].strip() if len(parts) > 1 else None
        return None

    @staticmethod
    def _infer_status(text: str) -> str:
        lower = text.lower()
        if "settl" in lower or "approv" in lower:
            return "settled"
        if "certif" in lower:
            return "certified"
        if "dismiss" in lower:
            return "dismissed"
        if "appeal" in lower:
            return "appealed"
        return "filed"

    @staticmethod
    def _infer_practice_areas(text: str) -> list[str]:
        areas: list[str] = ["class_actions", "litigation"]
        lower = text.lower()
        mapping = {
            "securities": ["securities_capital_markets"],
            "fraud": ["securities_capital_markets"],
            "product": ["product_liability"],
            "privacy": ["privacy_cybersecurity", "data_privacy_technology"],
            "breach": ["privacy_cybersecurity"],
            "employ": ["employment_labour"],
            "labour": ["employment_labour"],
            "environ": ["environmental_indigenous_energy"],
            "competi": ["competition_antitrust"],
            "price fix": ["competition_antitrust"],
            "insur": ["insurance_reinsurance"],
            "pension": ["pension_benefits"],
        }
        for keyword, hints in mapping.items():
            if keyword in lower:
                areas.extend(hints)
        return list(dict.fromkeys(areas))
