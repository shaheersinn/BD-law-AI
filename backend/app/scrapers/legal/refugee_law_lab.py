"""Refugee Law Lab — ML-ready JSON immigration decisions for NLP training."""

from __future__ import annotations

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

# Refugee Law Lab bulk JSON (GitHub releases)
_RLL_BASE = "https://api.github.com/repos/refugee-law-lab/refugee-law-lab/releases/latest"


@register
class RefugeeLawLabScraper(BaseScraper):
    source_id = "legal_refugee_law_lab"
    source_name = "Refugee Law Lab (ML-ready IRB decisions)"
    CATEGORY = "legal"
    signal_types = ["litigation_immigration"]
    rate_limit_rps = 0.05
    concurrency = 1
    ttl_seconds = 604800  # 1 week

    async def scrape(self) -> list[ScraperResult]:
        # RLL publishes bulk JSON datasets — we index latest release metadata
        # Actual file download happens in Phase 3 ground truth pipeline
        results: list[ScraperResult] = []
        try:
            headers = {"Accept": "application/vnd.github.v3+json", "User-Agent": "ORACLE-Research"}
            resp = await self.get(_RLL_BASE, headers=headers)
            if resp.status_code != 200:
                return results
            data = resp.json()
            results.append(
                ScraperResult(
                    source_id=self.source_id,
                    signal_type="litigation_immigration",
                    source_url=data.get("html_url"),
                    signal_value={
                        "tag": data.get("tag_name"),
                        "published": data.get("published_at"),
                        "assets": [a.get("name") for a in data.get("assets", [])],
                    },
                    signal_text=f"RLL Dataset Release: {data.get('tag_name')}",
                    published_at=self._parse_date(data.get("published_at")),
                    practice_area_hints=["immigration"],
                    raw_payload={"tag": data.get("tag_name")},
                )
            )
        except Exception as exc:
            log.error("rll_error", error=str(exc))
        return results
