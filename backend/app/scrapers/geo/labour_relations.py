"""
app/scrapers/geo/labour_relations.py — Labour Relations Board decisions scraper.

Sources:
  - Ontario LRB (OLRB): https://www.olrb.gov.on.ca/
    Decisions page with searchable case database
  - Federal CIRB: https://cirb-ccri.gc.ca/en/decisions/
    Canada Industrial Relations Board decisions

A union certification application against a company →
predict employment law mandate within 60–90 days.

Signal types:
  geo_labour_decision       — LRB decision (unfair labour practice, certification, etc.)
  geo_union_certification   — union certification or decertification application

Rate: 0.2 rps (government sites)
"""

from __future__ import annotations

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_CIRB_DECISIONS_URL = "https://cirb-ccri.gc.ca/en/decisions/"

# Keywords indicating union certification actions
_CERTIFICATION_KEYWORDS = frozenset(
    {
        "certification",
        "decertification",
        "bargaining unit",
        "union representation",
        "bargaining agent",
    }
)

# Keywords for unfair labour practices and disputes
_DISPUTE_KEYWORDS = frozenset(
    {
        "unfair labour practice",
        "unfair labor practice",
        "strike",
        "lockout",
        "arbitration",
        "termination",
        "dismissal",
        "reinstatement",
        "collective agreement",
        "duty of fair representation",
    }
)


@register
class LabourRelationsScraper(BaseScraper):
    """
    Labour Relations Board decisions scraper.

    Scrapes decisions from federal CIRB and provincial LRBs —
    signals employment disputes, union certifications, and labour law exposure.
    """

    source_id = "geo_labour"
    source_name = "Labour Relations Boards (Provincial + Federal)"
    signal_types = ["geo_labour_decision", "geo_union_certification"]
    CATEGORY = "geo"
    rate_limit_rps = 0.2
    concurrency = 1
    requires_auth = False

    async def scrape(self) -> list[ScraperResult]:
        """Scrape Labour Relations Board decisions."""
        results: list[ScraperResult] = []

        # Federal CIRB decisions
        try:
            results.extend(await self._scrape_cirb())
        except Exception as exc:
            log.error("cirb_scrape_error", error=str(exc))

        return results

    async def _scrape_cirb(self) -> list[ScraperResult]:
        """Scrape Canada Industrial Relations Board decisions page."""
        soup = await self.get_soup(_CIRB_DECISIONS_URL)
        if soup is None:
            log.warning("cirb_page_unavailable")
            return []

        results: list[ScraperResult] = []

        # CIRB decisions are typically listed as links/articles on the page
        links = soup.select(
            "article a, .views-row a, table.views-table a, "
            "main a[href*='decision'], .field-content a"
        )
        if not links:
            links = soup.select("main a[href]")

        seen_titles: set[str] = set()
        for link in links[:50]:
            title = self.safe_text(link)
            if not title or len(title) < 10 or title in seen_titles:
                continue
            seen_titles.add(title)

            href = link.get("href", "") or ""
            if href and not href.startswith("http"):
                href = f"https://cirb-ccri.gc.ca{href}"

            parsed = self._parse_decision(title, href)
            if parsed:
                results.append(parsed)

        log.info("cirb_decisions_parsed", count=len(results))
        return results

    def _parse_decision(self, title: str, url: str) -> ScraperResult | None:
        """Parse a CIRB decision link into a ScraperResult."""
        title_lower = title.lower()

        # Classify the decision type
        if any(kw in title_lower for kw in _CERTIFICATION_KEYWORDS):
            signal_type = "geo_union_certification"
        elif any(kw in title_lower for kw in _DISPUTE_KEYWORDS):
            signal_type = "geo_labour_decision"
        else:
            # Only include if it looks like a case decision
            if not any(kw in title_lower for kw in ("decision", "case", "order", "board")):
                return None
            signal_type = "geo_labour_decision"

        # Try to extract respondent/company name from title
        # CIRB format: often "Union v. Company" or "Company - Decision #"
        company = None
        for sep in (" v. ", " vs. ", " and ", " c. "):
            if sep in title:
                parts = title.split(sep)
                if len(parts) >= 2:
                    company = parts[1].split(" - ")[0].strip()
                    break

        return ScraperResult(
            source_id=self.source_id,
            signal_type=signal_type,
            raw_company_name=company,
            source_url=url or _CIRB_DECISIONS_URL,
            signal_value={
                "title": title,
                "board": "CIRB",
                "jurisdiction": "federal",
            },
            signal_text=f"CIRB Decision: {title}",
            practice_area_hints=["employment_labour"],
            raw_payload={"title": title, "url": url},
            confidence_score=0.7,
        )
