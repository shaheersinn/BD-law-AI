"""
app/scrapers/enforcement.py — Regulatory enforcement action RSS scraper.
Monitors OSC, OSFI, Competition Bureau, FINTRAC.
Schedule: every 4 hours.
"""

import logging
from datetime import datetime, timezone
from typing import Any

import feedparser

from app.scrapers.base import BaseScraper, RawSignal

log = logging.getLogger(__name__)

ENFORCEMENT_FEEDS: dict[str, tuple[str, str, int, float]] = {
    "OSC":         ("https://www.osc.ca/en/news-events/enforcement/enforcement-decisions-rss",  "Securities",          90, 0.90),
    "OSFI":        ("https://www.osfi-bsif.gc.ca/eng/fi-if/pages/rss.aspx",                    "Banking & Finance",   88, 0.88),
    "CompBureau":  ("https://www.canada.ca/en/competition-bureau/news/enforcement.rss",          "Competition",         91, 0.91),
    "FINTRAC":     ("https://www.fintrac-canafe.gc.ca/publications/index-eng",                   "Banking & Finance",   87, 0.87),
    "ECCC":        ("https://www.canada.ca/en/environment-climate-change/news.rss",              "Environmental",       89, 0.89),
    "HealthCan":   ("https://healthycanadians.gc.ca/recall-alert-rappel-avis/index-eng.php",     "Regulatory",          82, 0.82),
}


def _extract_company_from_title(title: str) -> str:
    """Best-effort company name extraction from enforcement notice title."""
    # Enforcement titles often start with company name, e.g. "Acme Corp — Order"
    for sep in [" — ", " - ", " : ", " v. ", " vs ", " in the matter of "]:
        if sep.lower() in title.lower():
            return title.split(sep)[0].strip()[:200]
    # Fall back to first 5 words
    words = title.split()
    return " ".join(words[:5]) if words else title[:50]


class EnforcementScraper(BaseScraper):
    source_name = "ENFORCEMENT"
    request_delay_seconds = 1.0

    async def fetch_new(self) -> list[RawSignal]:
        signals: list[RawSignal] = []

        for source, (feed_url, practice, urgency, weight) in ENFORCEMENT_FEEDS.items():
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:20]:
                    title = entry.get("title", "")
                    company = _extract_company_from_title(title)
                    summary = entry.get("summary", "")[:400]

                    try:
                        published = datetime(
                            *entry.published_parsed[:6], tzinfo=timezone.utc
                        )
                    except (AttributeError, TypeError):
                        published = datetime.now(timezone.utc)

                    signals.append(
                        RawSignal(
                            source=source,
                            trigger_type="enforcement_action",
                            company_name=company,
                            title=title,
                            practice_area=practice,
                            urgency=urgency,
                            filed_at=published,
                            description=summary or f"{source} enforcement action: {title}",
                            url=entry.get("link", ""),
                            base_weight=weight,
                        )
                    )
            except Exception as e:
                log.warning("Enforcement feed error for %s: %s", source, e)

        log.info("Enforcement: %d signals", len(signals))
        return signals
