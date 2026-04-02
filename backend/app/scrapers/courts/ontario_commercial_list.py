"""
Ontario Commercial List scraper.

Source: Ontario Courts Public Portal — Commercial List.
Signal: ontario_commercial_list_filing — fires 2-4 weeks ahead of CanLII
for CCAA, receiverships, and oppression filings.
"""

from __future__ import annotations

import re

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_COMMERCIAL_LIST_URL = "https://www.ontariocourts.ca/scj/practice/commercial-list/"


@register
class OntarioCommercialListScraper(BaseScraper):
    source_id = "courts_ontario_commercial"
    source_name = "Ontario Commercial List"
    signal_types = ["ontario_commercial_list_filing"]
    CATEGORY = "courts"
    rate_limit_rps = 0.2
    concurrency = 1
    ttl_seconds = 7200

    async def scrape(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []

        try:
            soup = await self.get_soup(_COMMERCIAL_LIST_URL)
            if not soup:
                return results
        except Exception as exc:
            log.error("ontario_commercial_fetch_error", error=str(exc))
            return results

        entries = (
            soup.select("table tbody tr")
            or soup.find_all("div", class_=re.compile(r"case|filing|matter", re.I))
            or soup.find_all("li", class_=re.compile(r"case|filing", re.I))
            or soup.find_all("article")
        )

        for entry in entries[:40]:
            try:
                text = self.safe_text(entry)
                if not text or len(text) < 10:
                    continue

                text_lower = text.lower()
                is_commercial = any(
                    kw in text_lower
                    for kw in [
                        "ccaa",
                        "receivership",
                        "oppression",
                        "arrangement",
                        "winding-up",
                        "plan of compromise",
                        "commercial list",
                    ]
                )
                if not is_commercial:
                    continue

                title_el = entry.find(["h2", "h3", "h4", "a", "strong"])
                title = self.safe_text(title_el) if title_el else text[:100]

                parties = self._extract_parties(title, text)

                link_el = entry.find("a", href=True)
                source_url = ""
                if link_el:
                    href = str(link_el.get("href", ""))
                    if href.startswith("http"):
                        source_url = href
                    elif href.startswith("/"):
                        source_url = f"https://www.ontariocourts.ca{href}"

                results.append(
                    ScraperResult(
                        source_id=self.source_id,
                        signal_type="ontario_commercial_list_filing",
                        raw_company_name=parties.get("applicant") or parties.get("respondent"),
                        source_url=source_url or _COMMERCIAL_LIST_URL,
                        signal_value={
                            "title": title,
                            "court": "Ontario Superior Court — Commercial List",
                            "parties": parties,
                        },
                        signal_text=f"Commercial List: {title}",
                        published_at=self._now_utc(),
                        practice_area_hints=[
                            "Restructuring / Insolvency",
                            "Litigation",
                        ],
                        raw_payload={"title": title, "text": text[:500]},
                        confidence_score=0.88,
                    )
                )
            except Exception as exc:
                log.warning("ontario_commercial_entry_error", error=str(exc))

        return results

    @staticmethod
    def _extract_parties(title: str, text: str) -> dict[str, str | None]:
        """Extract applicant/respondent from filing."""
        parties: dict[str, str | None] = {"applicant": None, "respondent": None}
        combined = f"{title}\n{text}"

        for role in ["applicant", "respondent", "debtor", "petitioner"]:
            pattern = rf"{role}\s*[:]\s*(.+?)(?:\n|$)"
            match = re.search(pattern, combined, re.I)
            if match:
                key = "applicant" if role in ("applicant", "petitioner", "debtor") else "respondent"
                parties[key] = match.group(1).strip()

        # Fallback: "X v. Y" pattern
        if not parties["applicant"]:
            match = re.search(r"(.+?)\s+v\.\s+(.+?)(?:\s*[-–—(]|$)", combined)
            if match:
                parties["applicant"] = match.group(1).strip()
                parties["respondent"] = match.group(2).strip()

        return parties
