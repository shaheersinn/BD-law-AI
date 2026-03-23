"""
app/scrapers/legal/canlii.py — CanLII API scraper.

Source: https://api.canlii.org/v1/ (REST API — free tier, API key required)

What it scrapes:
  - Recent case metadata (English only per project rules)
  - Specific database IDs for highest-value courts:
    csc-scc (SCC), onca (ONCA), bcca (BCCA), abca (ABCA),
    onsc (ONSC), onct (Competition Tribunal), irb (IRB)

Research findings:
  - API returns metadata ONLY (no full text)
  - Max 10,000 results per request, offset pagination
  - Free tier: ~500 requests/day
  - Rate: 0.1 rps (10s between requests)
  - API key required: register at developer.canlii.org

Signal types:
  - litigation_judgment: case decision
  - litigation_competition: competition tribunal decision
  - litigation_immigration: IRB decision (for refugee/immigration signal)
"""
from __future__ import annotations
from datetime import datetime, timezone, timedelta
from typing import Any
import structlog
from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register
from app.config import get_settings

log = structlog.get_logger(__name__)

_CANLII_BASE = "https://api.canlii.org/v1"

# (database_id, signal_type, practice_area_hints)
_TARGET_DATABASES = [
    ("csc-scc", "litigation_scc_decision", ["litigation"]),
    ("onct", "litigation_competition", ["competition"]),
    ("irb", "litigation_immigration", ["immigration"]),
    ("onca", "litigation_judgment", ["litigation"]),
    ("bcca", "litigation_judgment", ["litigation"]),
    ("abca", "litigation_judgment", ["litigation"]),
    ("onsc", "litigation_judgment", ["litigation"]),
    ("qcca", "litigation_judgment", ["litigation"]),
]


@register
class CanLIIScraper(BaseScraper):
    source_id = "legal_canlii"
    source_name = "CanLII (Canadian Legal Information Institute)"
    signal_types = ["litigation_judgment", "litigation_competition", "litigation_scc_decision"]
    rate_limit_rps = 0.1   # 10 seconds between requests — free tier safety
    concurrency = 1
    retry_attempts = 3
    timeout_seconds = 30.0
    ttl_seconds = 86400    # 24 hours — court decisions don't change
    requires_auth = True

    async def scrape(self) -> list[ScraperResult]:
        settings = get_settings()
        api_key = settings.canlii_api_key
        if not api_key:
            log.warning("canlii_no_api_key")
            return []

        results: list[ScraperResult] = []
        cutoff = (datetime.now(tz=timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")

        for db_id, signal_type, hints in _TARGET_DATABASES:
            try:
                db_results = await self._fetch_recent_cases(
                    db_id=db_id,
                    signal_type=signal_type,
                    hints=hints,
                    api_key=api_key,
                    published_after=cutoff,
                )
                results.extend(db_results)
                await self._rate_limit_sleep()
            except Exception as exc:
                log.error("canlii_db_error", db_id=db_id, error=str(exc))
                continue

        log.info("canlii_scrape_complete", total=len(results))
        return results

    async def _fetch_recent_cases(
        self,
        db_id: str,
        signal_type: str,
        hints: list[str],
        api_key: str,
        published_after: str,
        result_count: int = 100,
    ) -> list[ScraperResult]:
        """Fetch recent cases from a CanLII database."""
        url = f"{_CANLII_BASE}/caseBrowse/en/{db_id}/"
        params = {
            "api_key": api_key,
            "offset": 0,
            "resultCount": result_count,
            "publishedAfter": published_after,
        }
        response = await self.get(url, params=params)
        if response.status_code != 200:
            log.warning("canlii_non200", db_id=db_id, status=response.status_code)
            return []

        data = response.json()
        cases = data.get("cases", [])
        results = []

        for case in cases:
            case_id = case.get("caseId", {})
            en_id = case_id.get("en", "") if isinstance(case_id, dict) else str(case_id)
            results.append(ScraperResult(
                source_id=self.source_id,
                signal_type=signal_type,
                source_url=case.get("url") or f"https://www.canlii.org/en/{db_id}/{en_id}/",
                signal_value={
                    "database_id": db_id,
                    "case_id": en_id,
                    "title": case.get("title"),
                    "citation": case.get("citation"),
                    "decision_date": case.get("decisionDate"),
                    "keywords": case.get("keywords"),
                },
                signal_text=f"{case.get('title')} — {case.get('citation')}",
                published_at=self._parse_date(case.get("decisionDate")),
                practice_area_hints=hints,
                raw_payload=case,
            ))

        return results

    async def health_check(self) -> bool:
        settings = get_settings()
        if not settings.canlii_api_key:
            return False
        try:
            url = f"{_CANLII_BASE}/caseBrowse/en/"
            response = await self.get(url, params={"api_key": settings.canlii_api_key, "resultCount": 1})
            return response.status_code == 200
        except Exception:
            return False
