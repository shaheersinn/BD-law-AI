"""
CCAA monitor report scraper.

Sources: EY, PwC, Deloitte, KSV Advisory, FTI Consulting, Alvarez & Marsal
CCAA case listing pages.
Signal: ccaa_monitor_report — HIGHEST weight (0.95) of any new signal.
CCAA monitoring is a direct mandate indicator.
"""

from __future__ import annotations

import re

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_MONITOR_SOURCES = [
    {
        "name": "EY Restructuring",
        "url": "https://www.ey.com/en_ca/services/transactions/restructuring",
        "firm": "Ernst & Young",
    },
    {
        "name": "PwC Insolvency",
        "url": "https://www.pwc.com/ca/en/services/insolvency-assignments.html",
        "firm": "PwC",
    },
    {
        "name": "Deloitte Restructuring",
        "url": "https://www.deloitte.com/ca/en/services/financial-advisory/services/restructuring-services.html",
        "firm": "Deloitte",
    },
    {
        "name": "KSV Advisory",
        "url": "https://www.ksvadvisory.com/insolvency-cases",
        "firm": "KSV Advisory",
    },
    {
        "name": "FTI Consulting",
        "url": "https://www.fticonsulting.com/en/canada/creditor-resources",
        "firm": "FTI Consulting",
    },
    {
        "name": "Alvarez & Marsal",
        "url": "https://www.alvarezandmarsal.com/global-locations/canada",
        "firm": "Alvarez & Marsal",
    },
]


@register
class CCAAMonitorsScraper(BaseScraper):
    source_id = "restructuring_ccaa_monitors"
    source_name = "CCAA Monitor Reports"
    signal_types = ["ccaa_monitor_report"]
    CATEGORY = "restructuring"
    rate_limit_rps = 0.2
    concurrency = 1
    ttl_seconds = 7200

    async def scrape(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []

        for source in _MONITOR_SOURCES:
            try:
                page_results = await self._scrape_monitor(source)
                results.extend(page_results)
                await self._rate_limit_sleep()
            except Exception as exc:
                log.error(
                    "ccaa_monitor_error",
                    firm=source["firm"],
                    error=str(exc),
                )

        return results

    async def _scrape_monitor(self, source: dict[str, str]) -> list[ScraperResult]:
        results: list[ScraperResult] = []

        try:
            soup = await self.get_soup(source["url"])
            if not soup:
                return results
        except Exception as exc:
            log.warning("ccaa_monitor_fetch_error", firm=source["firm"], error=str(exc))
            return results

        # Parse case listings — look for CCAA/BIA/receivership entries
        case_elements = (
            soup.find_all("div", class_=re.compile(r"case|filing|engagement|matter", re.I))
            or soup.find_all("li", class_=re.compile(r"case|filing", re.I))
            or soup.find_all("article")
            or soup.select("table tbody tr")
        )

        for case_el in case_elements[:40]:
            try:
                text = self.safe_text(case_el)
                if not text:
                    continue

                text_lower = text.lower()
                # Filter for CCAA/BIA/receivership content
                is_insolvency = any(
                    kw in text_lower
                    for kw in [
                        "ccaa",
                        "companies' creditors",
                        "receivership",
                        "receiver",
                        "bankruptcy",
                        "proposal",
                        "bia",
                        "winding-up",
                        "monitor",
                        "trustee",
                    ]
                )
                if not is_insolvency:
                    continue

                title_el = case_el.find(["h2", "h3", "h4", "a", "strong"])
                title = self.safe_text(title_el) if title_el else text[:100]

                # Extract debtor company name
                debtor = self._extract_debtor(title, text)

                link_el = case_el.find("a", href=True)
                case_url = ""
                if link_el:
                    href = str(link_el.get("href", ""))
                    if href.startswith("http"):
                        case_url = href
                    elif href.startswith("/"):
                        base = source["url"].split("/")[0] + "//" + source["url"].split("/")[2]
                        case_url = base + href

                # Determine proceeding type
                proceeding_type = "CCAA"
                if "receivership" in text_lower or "receiver" in text_lower:
                    proceeding_type = "Receivership"
                elif "bia" in text_lower or "proposal" in text_lower:
                    proceeding_type = "BIA"

                results.append(
                    ScraperResult(
                        source_id=self.source_id,
                        signal_type="ccaa_monitor_report",
                        raw_company_name=debtor,
                        source_url=case_url or source["url"],
                        signal_value={
                            "debtor": debtor or title,
                            "monitor_firm": source["firm"],
                            "proceeding_type": proceeding_type,
                            "case_title": title,
                        },
                        signal_text=(
                            f"{proceeding_type} — {debtor or title} (monitor: {source['firm']})"
                        ),
                        published_at=self._now_utc(),
                        practice_area_hints=["Restructuring / Insolvency"],
                        raw_payload={
                            "firm": source["firm"],
                            "title": title,
                            "text": text[:500],
                        },
                        confidence_score=0.90,
                    )
                )
            except Exception as exc:
                log.warning("ccaa_case_parse_error", firm=source["firm"], error=str(exc))

        return results

    @staticmethod
    def _extract_debtor(title: str, text: str) -> str | None:
        """Extract debtor company name from case listing."""
        combined = f"{title}\n{text}"
        patterns = [
            r"(?:in the matter of|re:?)\s+(.+?)(?:\s*[-–—]\s*|\s*\(|\n|$)",
            r"^(.+?)\s*[-–—]\s*(?:ccaa|receiver|monitor|trustee)",
            r"debtor:\s*(.+?)(?:\n|$)",
        ]
        for pattern in patterns:
            match = re.search(pattern, combined, re.I | re.M)
            if match:
                name = match.group(1).strip()
                # Clean up
                name = re.sub(r"\s+", " ", name)
                if len(name) > 3 and not name.lower().startswith(("the ", "a ")):
                    return name
        return None
