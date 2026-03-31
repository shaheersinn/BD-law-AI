"""ClassAction.org + classactionlawsuit.com — Canadian class action aggregator."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta

import structlog
from bs4 import BeautifulSoup, Tag

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_CLASSACTION_ORG_URL = "https://www.classaction.org/canada"
_CLASSACTIONLAWSUIT_URL = "https://www.classactionlawsuit.com"

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
    "overtime": "employment_labour",
    "environmental": "environmental_indigenous_energy",
    "pollution": "environmental_indigenous_energy",
    "contamination": "environmental_indigenous_energy",
    "product": "product_liability",
    "defect": "product_liability",
    "recall": "product_liability",
    "injury": "product_liability",
    "competition": "competition_antitrust",
    "price-fixing": "competition_antitrust",
    "antitrust": "competition_antitrust",
    "insurance": "insurance_reinsurance",
    "pension": "pension_benefits",
    "benefit": "pension_benefits",
    "pharmaceutical": "health_life_sciences",
    "drug": "health_life_sciences",
    "medical": "health_life_sciences",
}

_DEFENDANT_RE = re.compile(
    r"(?:v\.|vs\.?|against)\s+(.+?)(?:\s+et\s+al\.?)?$",
    re.IGNORECASE,
)

_COMPANY_TITLE_RE = re.compile(
    r"^(.+?)\s+(?:class action|lawsuit|investigation|settlement|sued)",
    re.IGNORECASE,
)


@register
class ClassActionAggregatorScraper(BaseScraper):
    source_id = "class_actions_aggregator"
    source_name = "ClassAction.org / classactionlawsuit.com — Canadian Aggregator"
    CATEGORY = "class_actions"
    signal_types = ["class_action_news", "class_action_investigation"]
    rate_limit_rps = 0.5
    concurrency = 2
    ttl_seconds = 21600

    async def scrape(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []
        cutoff = datetime.now(tz=UTC) - timedelta(days=90)

        org_results = await self._scrape_classaction_org(cutoff)
        results.extend(org_results)

        await self._rate_limit_sleep()

        lawsuit_results = await self._scrape_classactionlawsuit(cutoff)
        results.extend(lawsuit_results)

        return results

    async def _scrape_classaction_org(self, cutoff: datetime) -> list[ScraperResult]:
        results: list[ScraperResult] = []
        try:
            resp = await self.get(_CLASSACTION_ORG_URL)
            if resp.status_code != 200:
                log.warning("classaction_org_non200", status=resp.status_code)
                return results

            soup = BeautifulSoup(resp.text, "lxml")
            articles = soup.select("article, .node--type-article, .views-row, .teaser")
            for article in articles[:40]:
                try:
                    result = self._parse_article(article, cutoff, _CLASSACTION_ORG_URL)
                    if result:
                        results.append(result)
                except Exception as exc:
                    log.debug("classaction_org_row_skip", error=str(exc))
                    continue
        except Exception as exc:
            log.error("classaction_org_error", error=str(exc))
        return results

    async def _scrape_classactionlawsuit(self, cutoff: datetime) -> list[ScraperResult]:
        results: list[ScraperResult] = []
        try:
            resp = await self.get(_CLASSACTIONLAWSUIT_URL)
            if resp.status_code != 200:
                log.warning("classactionlawsuit_non200", status=resp.status_code)
                return results

            soup = BeautifulSoup(resp.text, "lxml")
            articles = soup.select("article, .post, .entry, .views-row")
            for article in articles[:40]:
                try:
                    result = self._parse_article(article, cutoff, _CLASSACTIONLAWSUIT_URL)
                    if result:
                        results.append(result)
                except Exception as exc:
                    log.debug("classactionlawsuit_row_skip", error=str(exc))
                    continue
        except Exception as exc:
            log.error("classactionlawsuit_error", error=str(exc))
        return results

    def _parse_article(self, article: Tag, cutoff: datetime, base_url: str) -> ScraperResult | None:
        title_tag = article.find(["h2", "h3", "h4", "a"])
        title = self.safe_text(title_tag) if title_tag else self.safe_text(article)
        if not title or len(title) < 10:
            return None

        if self._is_french_only(title):
            return None

        link_tag = article.find("a")
        source_url = None
        if link_tag and link_tag.get("href"):
            href = str(link_tag["href"])
            source_url = href if href.startswith("http") else f"{base_url}{href}"

        time_tag = article.find("time")
        date_str = (
            time_tag.get("datetime")
            if time_tag and time_tag.get("datetime")
            else self.safe_text(time_tag)
        )
        published = self._parse_date(date_str)
        if published and published < cutoff:
            return None

        company = self._extract_company_name(title)
        signal_type = self._infer_signal_type(title)
        hints = self._infer_practice_areas(title)

        return ScraperResult(
            source_id=self.source_id,
            signal_type=signal_type,
            raw_company_name=company,
            source_url=source_url,
            signal_value={
                "headline": title,
                "aggregator_source": base_url,
            },
            signal_text=f"Class action aggregator: {title}",
            published_at=published,
            practice_area_hints=hints,
            raw_payload={"headline": title, "source": base_url},
            confidence_score=0.70,
        )

    async def health_check(self) -> bool:
        try:
            resp = await self.get(_CLASSACTION_ORG_URL)
            return resp.status_code == 200
        except Exception:
            return False

    @staticmethod
    def _is_french_only(text: str) -> bool:
        french_markers = ["recours collectif", "demandeur", "défendeur", "tribunal"]
        lower = text.lower()
        french_hits = sum(1 for m in french_markers if m in lower)
        english_markers = ["class action", "plaintiff", "defendant", "lawsuit", "settlement"]
        english_hits = sum(1 for m in english_markers if m in lower)
        return french_hits >= 2 and english_hits == 0

    @staticmethod
    def _extract_company_name(title: str) -> str | None:
        match = _DEFENDANT_RE.search(title)
        if match:
            name = match.group(1).strip().rstrip(".")
            if len(name) > 2:
                return name
        match = _COMPANY_TITLE_RE.match(title)
        if match:
            name = match.group(1).strip().rstrip(".")
            if len(name) > 2:
                return name
        return None

    @staticmethod
    def _infer_signal_type(text: str) -> str:
        lower = text.lower()
        if "investigation" in lower or "probe" in lower or "looking into" in lower:
            return "class_action_investigation"
        return "class_action_news"

    @staticmethod
    def _infer_practice_areas(text: str) -> list[str]:
        hints: set[str] = {"class_actions", "litigation"}
        lower = text.lower()
        for keyword, pa in _KEYWORD_PA_MAP.items():
            if keyword in lower:
                hints.add(pa)
        return sorted(hints)
