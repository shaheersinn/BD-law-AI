"""
SOQUIJ Quebec Superior Court scraper.

Source: SOQUIJ (soquij.qc.ca) — Quebec Superior Court publication feed.
Signal: quebec_superior_court_filing — fires when watchlist companies
appear in Quebec Superior Court filings/decisions.

NOTE: Subscription may be required. Degrades gracefully.
"""

from __future__ import annotations

import re

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_SOQUIJ_URL = "https://soquij.qc.ca/portail/recherche/en/decisions-recentes"


@register
class SOQUIJScraper(BaseScraper):
    source_id = "courts_soquij"
    source_name = "SOQUIJ Quebec Courts"
    signal_types = ["quebec_superior_court_filing"]
    CATEGORY = "courts"
    rate_limit_rps = 0.2
    concurrency = 1
    ttl_seconds = 7200

    async def scrape(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []

        try:
            resp = await self.get(_SOQUIJ_URL)
            if resp.status_code in (401, 403):
                log.warning(
                    "soquij_auth_required",
                    msg="SOQUIJ subscription may be required — degrading gracefully",
                )
                return results
            if resp.status_code != 200:
                log.warning("soquij_http_error", status=resp.status_code)
                return results
        except Exception as exc:
            log.error("soquij_fetch_error", error=str(exc))
            return results

        try:
            soup = await self.get_soup(_SOQUIJ_URL)
            if not soup:
                return results
        except Exception:
            return results

        entries = (
            soup.find_all("div", class_=re.compile(r"decision|result|case", re.I))
            or soup.find_all("article")
            or soup.find_all("li", class_=re.compile(r"decision|result", re.I))
            or soup.select("table tbody tr")
        )

        for entry in entries[:30]:
            try:
                text = self.safe_text(entry)
                if not text or len(text) < 10:
                    continue

                title_el = entry.find(["h2", "h3", "h4", "a"])
                title = self.safe_text(title_el) if title_el else text[:100]

                # Extract party names
                party = self._extract_party(title, text)

                link_el = entry.find("a", href=True)
                source_url = ""
                if link_el:
                    href = str(link_el.get("href", ""))
                    if href.startswith("http"):
                        source_url = href

                date_el = entry.find("time") or entry.find(
                    ["span"], class_=lambda c: c and "date" in str(c).lower()
                )
                published_at = None
                if date_el:
                    date_str = date_el.get("datetime") or self.safe_text(date_el)
                    published_at = self._parse_date(str(date_str))

                results.append(
                    ScraperResult(
                        source_id=self.source_id,
                        signal_type="quebec_superior_court_filing",
                        raw_company_name=party,
                        source_url=source_url or _SOQUIJ_URL,
                        signal_value={
                            "title": title,
                            "court": "Quebec Superior Court",
                        },
                        signal_text=f"Quebec Superior Court: {title}",
                        published_at=published_at or self._now_utc(),
                        practice_area_hints=["Litigation"],
                        raw_payload={"title": title, "text": text[:500]},
                        confidence_score=0.85,
                    )
                )
            except Exception as exc:
                log.warning("soquij_entry_error", error=str(exc))

        return results

    @staticmethod
    def _extract_party(title: str, text: str) -> str | None:
        """Extract party name from Quebec court decision."""
        combined = f"{title}\n{text}"
        # French-style: "X c. Y" or "X v. Y"
        match = re.search(r"(.+?)\s+(?:c\.|v\.)\s+", combined)
        if match:
            name = match.group(1).strip()
            if len(name) > 2:
                return name
        return None
