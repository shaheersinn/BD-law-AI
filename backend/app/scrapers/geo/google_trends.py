"""
app/scrapers/geo/google_trends.py — Google Trends scraper via pytrends.

Queries: Legal keywords by Canadian province to detect geographic spikes
in legal-related search activity that precede formal filings.

Examples:
  - "wrongful dismissal Ontario" spike → employment mandate signal
  - "CCAA filing" Canada spike → insolvency mandate signal
  - "class action lawsuit" BC → class action mandate signal

Uses pytrends (unofficial Google Trends API — no key required, rate limited).

Signal types:
  geo_trends_legal_spike — search volume spike detected
"""

from __future__ import annotations

from datetime import UTC, datetime

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_TREND_QUERIES = [
    (
        ["wrongful dismissal", "employment lawyer", "termination without cause"],
        ["employment"],
        "geo_trends_employment_spike",
    ),
    (
        ["CCAA filing", "insolvency Canada", "creditor protection"],
        ["insolvency"],
        "geo_trends_insolvency_spike",
    ),
    (
        ["class action lawsuit Canada", "securities fraud Canada"],
        ["class_actions", "securities"],
        "geo_trends_litigation_spike",
    ),
    (
        ["data breach Canada", "privacy violation", "PIPEDA complaint"],
        ["privacy"],
        "geo_trends_privacy_spike",
    ),
    (
        ["competition bureau investigation", "price fixing Canada"],
        ["competition"],
        "geo_trends_competition_spike",
    ),
]


@register
class GoogleTrendsScraper(BaseScraper):
    source_id = "geo_google_trends"
    source_name = "Google Trends (Canadian legal queries)"
    CATEGORY = "geo"
    signal_types = [
        "geo_trends_legal_spike",
        "geo_trends_employment_spike",
        "geo_trends_insolvency_spike",
        "geo_trends_litigation_spike",
    ]
    rate_limit_rps = 0.016  # 1 req / 60s — pytrends aggressive throttle
    concurrency = 1
    retry_attempts = 2
    timeout_seconds = 60.0
    ttl_seconds = 21600  # 6 hours
    requires_auth = False

    async def scrape(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []
        try:
            from pytrends.request import TrendReq

            def _run_trends() -> list[dict]:
                pt = TrendReq(hl="en-CA", tz=-300, geo="CA")
                trend_results = []
                for keywords, hints, sig_type in _TREND_QUERIES:
                    try:
                        pt.build_payload(keywords[:5], cat=0, timeframe="now 7-d", geo="CA")
                        df = pt.interest_over_time()
                        if df.empty:
                            continue
                        for kw in keywords:
                            if kw not in df.columns:
                                continue
                            recent_avg = float(df[kw].tail(7).mean())
                            historical_avg = float(df[kw].mean())
                            if historical_avg > 0 and recent_avg / historical_avg > 1.3:
                                trend_results.append(
                                    {
                                        "keyword": kw,
                                        "signal_type": sig_type,
                                        "hints": hints,
                                        "recent_avg": recent_avg,
                                        "historical_avg": historical_avg,
                                        "spike_ratio": recent_avg / historical_avg,
                                    }
                                )
                    except Exception as inner_exc:
                        log.warning("trends_query_failed", kw=keywords[0], error=str(inner_exc))
                return trend_results

            # pytrends is synchronous — run in executor
            loop = __import__("asyncio").get_event_loop()
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                trend_data = await loop.run_in_executor(executor, _run_trends)

            for item in trend_data:
                results.append(
                    ScraperResult(
                        source_id=self.source_id,
                        signal_type=item["signal_type"],
                        signal_value={
                            "keyword": item["keyword"],
                            "recent_avg": round(item["recent_avg"], 1),
                            "historical_avg": round(item["historical_avg"], 1),
                            "spike_ratio": round(item["spike_ratio"], 2),
                            "geo": "CA",
                        },
                        signal_text=f"Google Trends spike: '{item['keyword']}' in Canada ({item['spike_ratio']:.1f}x)",
                        published_at=datetime.now(tz=UTC),
                        practice_area_hints=item["hints"],
                        raw_payload=item,
                        confidence_score=0.65,
                    )
                )

        except ImportError:
            log.warning("pytrends_not_installed")
        except Exception as exc:
            log.error("google_trends_error", error=str(exc))

        return results
