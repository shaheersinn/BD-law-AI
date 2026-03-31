"""
app/scrapers/consumer/opc_breach_reports.py — OPC breach reports + PIPEDA findings.

Sources:
  - OPC Breach Notifications: https://www.priv.gc.ca/en/opc-actions-and-decisions/
  - PIPEDA Findings: https://www.priv.gc.ca/en/opc-actions-and-decisions/pipeda-findings/
  - Breach Reports: https://www.priv.gc.ca/en/opc-actions-and-decisions/breach-reports/

What it scrapes:
  - OPC privacy breach reports (mandatory reporting under PIPEDA)
  - PIPEDA enforcement findings
  - Organizations found to have violated PIPEDA

Signal types:
  - privacy_breach_report: Data breach reported to OPC
  - privacy_enforcement: PIPEDA finding / enforcement action

Practice areas: privacy_cybersecurity, data_privacy_technology, class_actions

Why: Data breaches affecting >10,000 Canadians almost always lead to class actions.
     OPC breach reports are the earliest public signal of a breach-driven class action.
     Average time: breach report → class action filing = 6–18 months.
"""

from __future__ import annotations

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_OPC_BASE = "https://www.priv.gc.ca"
_OPC_ACTIONS_URL = "https://www.priv.gc.ca/en/opc-actions-and-decisions/"
_OPC_PIPEDA_URL = "https://www.priv.gc.ca/en/opc-actions-and-decisions/pipeda-findings/"
_OPC_BREACHES_URL = "https://www.priv.gc.ca/en/opc-actions-and-decisions/breach-reports/"

_PRACTICE_AREAS_BREACH = ["privacy_cybersecurity", "data_privacy_technology", "class_actions"]
_PRACTICE_AREAS_PIPEDA = [
    "privacy_cybersecurity",
    "data_privacy_technology",
    "regulatory_compliance",
]

# Threshold at which breach → class action risk is high
_CLASS_ACTION_THRESHOLD = 10_000  # individuals affected


@register
class OPCBreachReportsScraper(BaseScraper):
    source_id = "consumer_opc_breach_reports"
    source_name = "OPC Privacy Breach Reports and PIPEDA Findings"
    CATEGORY = "consumer"
    signal_types = ["privacy_breach_report", "privacy_enforcement"]
    rate_limit_rps = 0.1
    concurrency = 1
    ttl_seconds = 14400  # 4-hour cache

    async def scrape(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []
        results.extend(await self._scrape_pipeda_findings())
        results.extend(await self._scrape_actions_news())
        return results

    async def _scrape_pipeda_findings(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []
        try:
            soup = await self.get_soup(_OPC_PIPEDA_URL)
            if soup is None:
                return results

            for item in soup.select("article, .finding-item, li, tr"):
                title_el = item.find(["h2", "h3", "h4", "a", "td"])
                if not title_el:
                    continue
                title = self.safe_text(title_el)
                if not title or len(title) < 15:
                    continue

                link_el = item.find("a", href=True)
                url = ""
                if link_el:
                    href = link_el.get("href", "")
                    url = href if href.startswith("http") else f"{_OPC_BASE}{href}"

                date_el = item.find(["time", ".date", "td"])
                date_str = self.safe_text(date_el) if date_el else ""

                description_el = item.find("p")
                description = self.safe_text(description_el) if description_el else ""

                company = self._extract_organization(title, description)
                individuals = self._extract_individuals_count(title, description)
                is_high_risk = individuals is not None and individuals >= _CLASS_ACTION_THRESHOLD

                results.append(
                    ScraperResult(
                        source_id=self.source_id,
                        signal_type="privacy_enforcement",
                        raw_company_name=company,
                        source_url=url or _OPC_PIPEDA_URL,
                        signal_value={
                            "title": title,
                            "organization": company,
                            "individuals_affected": individuals,
                            "class_action_risk": is_high_risk,
                            "date": date_str,
                            "description": description[:500],
                        },
                        signal_text=f"OPC PIPEDA Finding: {title}",
                        confidence_score=0.9 if is_high_risk else 0.75,
                        published_at=self._parse_date(date_str),
                        practice_area_hints=_PRACTICE_AREAS_PIPEDA
                        + (["class_actions"] if is_high_risk else []),
                        raw_payload={"title": title, "url": url, "description": description},
                    )
                )
                await self._rate_limit_sleep()

        except Exception as exc:
            log.error("opc_pipeda_scrape_error", error=str(exc))

        return results

    async def _scrape_actions_news(self) -> list[ScraperResult]:
        """Parse OPC actions and decisions page for breach notifications."""
        results: list[ScraperResult] = []
        try:
            soup = await self.get_soup(_OPC_ACTIONS_URL)
            if soup is None:
                return results

            for item in soup.select("article, .news-item, li"):
                title_el = item.find(["h2", "h3", "a"])
                if not title_el:
                    continue
                title = self.safe_text(title_el)
                if not title or len(title) < 10:
                    continue

                if not self._is_breach_signal(title):
                    continue

                link_el = item.find("a", href=True)
                url = ""
                if link_el:
                    href = link_el.get("href", "")
                    url = href if href.startswith("http") else f"{_OPC_BASE}{href}"

                description_el = item.find("p")
                description = self.safe_text(description_el) if description_el else ""

                individuals = self._extract_individuals_count(title, description)

                results.append(
                    ScraperResult(
                        source_id=self.source_id,
                        signal_type="privacy_breach_report",
                        raw_company_name=self._extract_organization(title, description),
                        source_url=url or _OPC_ACTIONS_URL,
                        signal_value={
                            "title": title,
                            "individuals_affected": individuals,
                            "class_action_risk": individuals is not None
                            and individuals >= _CLASS_ACTION_THRESHOLD,
                            "description": description[:500],
                        },
                        signal_text=f"OPC Breach Report: {title}",
                        confidence_score=0.85,
                        practice_area_hints=_PRACTICE_AREAS_BREACH,
                        raw_payload={"title": title, "url": url},
                    )
                )
                await self._rate_limit_sleep()

        except Exception as exc:
            log.error("opc_actions_scrape_error", error=str(exc))

        return results

    @staticmethod
    def _is_breach_signal(title: str) -> bool:
        text = title.lower()
        return any(
            k in text
            for k in ["breach", "incident", "unauthorized", "hack", "data exposure", "leak"]
        )

    @staticmethod
    def _extract_organization(title: str, description: str) -> str | None:
        combined = f"{title} {description}"
        lower = combined.lower()
        for sep in [" by ", " against ", " involving ", "re: ", "regarding "]:
            if sep in lower:
                idx = lower.index(sep)
                candidate = combined[idx + len(sep) : idx + len(sep) + 80]
                candidate = candidate.split(".")[0].split(",")[0].strip()
                if 3 < len(candidate) < 80:
                    return candidate
        # Extract PIPEDA finding number pattern: "PIPEDA Report of Findings #NNN – Organization"
        if "–" in combined:
            parts = combined.split("–")
            if len(parts) >= 2:
                return parts[-1].strip()[:80]
        return None

    @staticmethod
    def _extract_individuals_count(title: str, description: str) -> int | None:
        import re  # noqa: PLC0415

        text = f"{title} {description}"
        patterns = [
            # "250,000 individuals affected" or "affecting 250,000 individuals"
            r"([\d,]+)\s*(?:individuals?|Canadians?|people|persons?|accounts?|customers?|users?)(?:\s+affected|\s+impacted|\s+compromised|\s+exposed)?",
            # "affected approximately 250,000" or "affecting 250,000"
            r"affect(?:ed|ing)\s+(?:approximately\s+)?([\d,]+)",
            # "250,000 records compromised"
            r"([\d,]+)\s*(?:records?|files?)\s*(?:affected|compromised|exposed)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    # Some patterns have the number in group 1, others in group 2
                    raw = match.group(1).replace(",", "")
                    return int(raw)
                except (ValueError, IndexError):
                    continue
        return None
