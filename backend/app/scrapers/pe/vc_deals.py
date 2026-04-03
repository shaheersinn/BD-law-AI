"""
VC deal flow scraper.

Sources: BetaKit RSS (betakit.com/feed) + Crunchbase free API (optional).
Signal: vc_series_b_plus — fires when Canadian companies raise Series B+
rounds above $10M threshold.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET  # nosec B405

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_BETAKIT_RSS_URL = "https://betakit.com/feed/"
_FUNDING_THRESHOLD = 10_000_000  # $10M


@register
class VCDealsScraper(BaseScraper):
    source_id = "pe_vc_deals"
    source_name = "BetaKit / VC Deals"
    signal_types = ["vc_series_b_plus"]
    CATEGORY = "pe"
    rate_limit_rps = 0.3
    concurrency = 1
    ttl_seconds = 7200

    async def scrape(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []

        # BetaKit RSS
        try:
            betakit_results = await self._scrape_betakit()
            results.extend(betakit_results)
        except Exception as exc:
            log.error("vc_deals_betakit_error", error=str(exc))

        return results

    async def _scrape_betakit(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []

        try:
            resp = await self.get(_BETAKIT_RSS_URL)
            if resp.status_code != 200:
                log.warning("vc_deals_betakit_http_error", status=resp.status_code)
                return results
        except Exception as exc:
            log.warning("vc_deals_betakit_fetch_error", error=str(exc))
            return results

        try:
            root = ET.fromstring(resp.text)  # nosec B314 — trusted news RSS
        except ET.ParseError as exc:
            log.warning("vc_deals_betakit_xml_error", error=str(exc))
            return results

        for item in root.iter("item"):
            try:
                title = (item.findtext("title") or "").strip()
                description = (item.findtext("description") or "").strip()
                link = (item.findtext("link") or "").strip()
                pub_date = (item.findtext("pubDate") or "").strip()

                combined = f"{title} {description}".lower()

                # Check for Series B+ or large funding rounds
                is_series_b_plus = bool(re.search(r"series\s+[b-z]", combined, re.I))
                amount = self._extract_amount(combined)
                is_large_round = amount is not None and amount >= _FUNDING_THRESHOLD

                if not (is_series_b_plus or is_large_round):
                    continue

                # Extract company name from title
                company = self._extract_company_name(title)

                results.append(
                    ScraperResult(
                        source_id=self.source_id,
                        signal_type="vc_series_b_plus",
                        raw_company_name=company,
                        source_url=link,
                        signal_value={
                            "title": title,
                            "amount_cad": amount,
                            "is_series_b_plus": is_series_b_plus,
                            "source": "betakit",
                        },
                        signal_text=f"BetaKit: {title}",
                        published_at=self._parse_date(pub_date),
                        practice_area_hints=["Corporate / M&A", "Securities"],
                        raw_payload={"title": title, "description": description[:500]},
                        confidence_score=0.80 if is_series_b_plus else 0.70,
                    )
                )
            except Exception as exc:
                log.warning("vc_deals_item_error", error=str(exc))

        return results

    @staticmethod
    def _extract_amount(text: str) -> int | None:
        """Extract dollar amount from text."""
        patterns = [
            r"\$\s*([\d.]+)\s*(?:m|million)",
            r"raised\s+\$?\s*([\d.]+)\s*(?:m|million)",
            r"([\d.]+)\s*(?:m|million)\s*(?:cad|cdn|usd)?\s*(?:round|funding|raise)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.I)
            if match:
                try:
                    amount = float(match.group(1)) * 1_000_000
                    return int(amount)
                except ValueError:
                    continue
        return None

    @staticmethod
    def _extract_company_name(title: str) -> str | None:
        """Extract company name from funding headline."""
        patterns = [
            r"^(.+?)\s+(?:raises?|secures?|closes?|announces?)",
            r"^(.+?)\s+(?:Series\s+[A-Z])",
        ]
        for pattern in patterns:
            match = re.match(pattern, title, re.I)
            if match:
                name = match.group(1).strip()
                if len(name) > 2:
                    return name
        return None
