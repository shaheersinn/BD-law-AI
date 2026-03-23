"""
app/scrapers/legal/scc.py — Supreme Court of Canada decisions (full text).

Source: https://decisions.scc-csc.ca/scc-csc/scc-csc/en/nav_date.do (HTML)
        https://www.scc-csc.ca/case-dossier/info/all-tout-eng.aspx

What it scrapes:
  - Recent SCC decisions with full text HTML
  - Extracts: parties, date, case summary, practice area classification
  - These are training data candidates (caselaw spec in Word doc)

Signal types:
  - litigation_scc_decision: SCC ruling
"""
from __future__ import annotations
from datetime import datetime, timezone, timedelta
import structlog
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_SCC_RSS = "https://www.scc-csc.ca/rss/judgments-jugements-eng.xml"
_SCC_BASE = "https://www.scc-csc.ca"


@register
class SCCScraper(BaseScraper):
    source_id = "legal_scc"
    source_name = "Supreme Court of Canada"
    signal_types = ["litigation_scc_decision"]
    rate_limit_rps = 0.1
    concurrency = 1
    ttl_seconds = 86400

    async def scrape(self) -> list[ScraperResult]:
        import xml.etree.ElementTree as ET
        results: list[ScraperResult] = []
        try:
            response = await self.get(_SCC_RSS)
            if response.status_code != 200:
                return results
            root = ET.fromstring(response.text)
            for item in root.iter("item"):
                title = (item.findtext("title") or "").strip()
                link = (item.findtext("link") or "").strip()
                pub_date = (item.findtext("pubDate") or "").strip()
                description = (item.findtext("description") or "").strip()

                results.append(ScraperResult(
                    source_id=self.source_id,
                    signal_type="litigation_scc_decision",
                    source_url=link,
                    signal_value={"title": title, "date": pub_date, "description": description},
                    signal_text=f"SCC Decision: {title}",
                    published_at=self._parse_date(pub_date),
                    practice_area_hints=self._classify(title + " " + description),
                    raw_payload={"title": title, "link": link, "description": description},
                ))
                await self._rate_limit_sleep()
        except Exception as exc:
            log.error("scc_error", error=str(exc))
        return results

    def _classify(self, text: str) -> list[str]:
        text = text.lower()
        areas = []
        if any(k in text for k in ["employment", "labour", "discrimination", "human rights"]): areas.append("employment")
        if any(k in text for k in ["contract", "negligence", "tort", "liability"]): areas.append("litigation")
        if any(k in text for k in ["criminal", "charter", "evidence"]): areas.append("litigation")
        if any(k in text for k in ["tax", "income", "assessment"]): areas.append("tax")
        if any(k in text for k in ["aboriginal", "indigenous", "treaty"]): areas.append("indigenous")
        if any(k in text for k in ["competition", "merger", "antitrust"]): areas.append("competition")
        if any(k in text for k in ["privacy", "data", "information"]): areas.append("privacy")
        if any(k in text for k in ["securities", "investment", "fraud"]): areas.append("securities")
        return areas or ["litigation"]
