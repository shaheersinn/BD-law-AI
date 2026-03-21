"""
app/scrapers/jobs.py — Job posting signal scraper.
Indeed RSS + Proxycurl LinkedIn (free tier: 10 req/month).
Schedule: daily at 6am.
"""

import logging
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import feedparser

from app.config import get_settings
from app.scrapers.base import BaseScraper, RawSignal

log = logging.getLogger(__name__)
settings = get_settings()

# (query snippet, signal type, practice area, urgency, base weight)
LEGAL_JOB_SIGNALS: list[tuple[str, str, str, int, float]] = [
    ('"General Counsel" "new" OR "first"',       "job_gc_hire",             "All Practice Areas",       78, 0.78),
    ('"Chief Compliance Officer" "urgent" OR "immediate"', "job_cco_urgent","Regulatory / AML",         85, 0.85),
    ('"Data Protection Officer" OR "Privacy Counsel"', "job_privacy_counsel","Privacy & Cybersecurity", 82, 0.82),
    ('"Senior M&A Counsel" "in-house"',          "job_ma_counsel",          "Corporate / M&A",          80, 0.80),
    ('"Senior Litigation Counsel" "in-house"',   "job_litigation_counsel",  "Litigation",               83, 0.83),
    ('"Deputy General Counsel" "Regulatory"',    "job_deputy_gc_regulatory","Regulatory",               77, 0.77),
    ('"Environmental Counsel" OR "Indigenous Counsel"',"job_environmental_counsel","Environmental",      79, 0.79),
    ('"VP Legal" OR "Head of Legal" "build"',    "job_gc_hire",             "All Practice Areas",       70, 0.70),
]


class JobsScraper(BaseScraper):
    source_name = "JOBS"
    request_delay_seconds = 2.0

    async def fetch_for_company(
        self, company_name: str
    ) -> list[RawSignal]:
        """Search job boards for legal role postings at a specific company."""
        signals: list[RawSignal] = []
        safe_company = company_name.replace('"', "").replace("&", "and")

        for query, sig_type, practice, urgency, weight in LEGAL_JOB_SIGNALS:
            rss_url = (
                f"https://www.indeed.com/rss?q={query}+{safe_company}"
                "&l=Canada&sort=date"
            )
            try:
                feed = feedparser.parse(rss_url)
                for entry in feed.entries[:5]:
                    title = entry.get("title", "")
                    if safe_company.lower() not in title.lower():
                        continue

                    try:
                        published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                    except (AttributeError, TypeError):
                        published = datetime.now(timezone.utc)

                    signals.append(
                        RawSignal(
                            source="JOBS",
                            trigger_type=sig_type,
                            company_name=company_name,
                            title=title,
                            practice_area=practice,
                            urgency=urgency,
                            filed_at=published,
                            description=f"Job posting detected: {title}. Signal: {sig_type.replace('_', ' ')}.",
                            url=entry.get("link", ""),
                            base_weight=weight,
                        )
                    )
            except Exception as e:
                log.debug("Jobs RSS error for %s / %s: %s", company_name, sig_type, e)

        return signals

    async def fetch_new(self) -> list[RawSignal]:
        """Stub — called by Celery task with company list injected."""
        return []
