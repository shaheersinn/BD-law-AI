"""
app/scrapers/social/breach_monitor.py — Data breach monitoring scraper.

Sources:
  - HaveIBeenPwned API v3 (breaches endpoint — free public API)
  - Canadian Cyber Centre advisories RSS

A corporate data breach is a reliable leading indicator for:
  - Privacy/cybersecurity litigation
  - OPC investigation
  - Class action (in 8-18 months)
  - Reputational/securities impact

Signal types:
  social_breach_detected     — new data breach recorded in HIBP
  regulatory_cccs_advisory   — Canadian Centre for Cyber Security advisory

Rate limit: 0.1 rps
"""
from __future__ import annotations
import xml.etree.ElementTree as ET
import structlog
from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register
from app.config import get_settings

log = structlog.get_logger(__name__)

_HIBP_BREACHES = "https://haveibeenpwned.com/api/v3/breaches"
_CCCS_RSS = "https://www.cyber.gc.ca/en/rss/all.xml"


@register
class BreachMonitorScraper(BaseScraper):
    source_id = "social_breach_monitor"
    source_name = "Data Breach Monitor (HIBP + CCCS)"
    signal_types = ["social_breach_detected", "regulatory_cccs_advisory"]
    rate_limit_rps = 0.1
    concurrency = 1
    retry_attempts = 3
    timeout_seconds = 30.0
    ttl_seconds = 43200
    requires_auth = True

    async def scrape(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []

        # HIBP breaches feed
        try:
            settings = get_settings()
            hibp_key = getattr(settings, "hibp_api_key", None)
            if hibp_key:
                response = await self.get(
                    _HIBP_BREACHES,
                    headers={
                        "hibp-api-key": hibp_key,
                        "User-Agent": "ORACLE-BD/1.0",
                    },
                )
                if response.status_code == 200:
                    breaches = response.json()
                    from datetime import datetime, timezone, timedelta
                    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=30)
                    for breach in breaches:
                        breach_date = self._parse_date(breach.get("AddedDate"))
                        if breach_date and breach_date < cutoff:
                            continue
                        if breach.get("DataClasses") and breach.get("IsVerified"):
                            results.append(ScraperResult(
                                source_id=self.source_id,
                                signal_type="social_breach_detected",
                                raw_company_name=breach.get("Name"),
                                source_url=f"https://haveibeenpwned.com/PwnedWebsites#{breach.get('Name')}",
                                signal_value={
                                    "breach_name": breach.get("Name"),
                                    "breach_date": breach.get("BreachDate"),
                                    "pwn_count": breach.get("PwnCount", 0),
                                    "data_classes": breach.get("DataClasses", []),
                                    "is_sensitive": breach.get("IsSensitive", False),
                                    "domain": breach.get("Domain"),
                                },
                                signal_text=f"Data breach: {breach.get('Name')} — {breach.get('PwnCount', 0):,} records",
                                published_at=self._parse_date(breach.get("AddedDate")),
                                practice_area_hints=["privacy", "technology", "class_actions"],
                                raw_payload=breach,
                                confidence_score=0.9,
                            ))
        except Exception as exc:
            log.error("hibp_error", error=str(exc))

        await self._rate_limit_sleep()

        # CCCS advisories
        try:
            resp = await self.get(_CCCS_RSS)
            if resp.status_code == 200:
                root = ET.fromstring(resp.text)
                for item in root.iter("item"):
                    title = (item.findtext("title") or "").strip()
                    results.append(ScraperResult(
                        source_id=self.source_id,
                        signal_type="regulatory_cccs_advisory",
                        source_url=(item.findtext("link") or "").strip(),
                        signal_value={"title": title},
                        signal_text=f"CCCS Advisory: {title}",
                        published_at=self._parse_date((item.findtext("pubDate") or "").strip()),
                        practice_area_hints=["privacy", "technology"],
                        raw_payload={"title": title},
                    ))
        except Exception as exc:
            log.error("cccs_rss_error", error=str(exc))

        return results
