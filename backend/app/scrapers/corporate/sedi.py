"""
app/scrapers/corporate/sedi.py — SEDI Insider Trading scraper.

Source: https://www.sedi.ca/sedi/SVTframe.jsp (SEDI public search)

What it scrapes:
  - Insider sale transactions (CEO/CFO/Director selling = potential distress signal)
  - Cluster selling (multiple insiders selling same period)
  - Large single-transaction sales

Signal types:
  - insider_trade_sell: significant insider sale
  - insider_trade_cluster: cluster selling event

Rate limit: 0.2 rps (government site — be respectful)
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from bs4 import BeautifulSoup

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_SEDI_BASE = "https://www.sedi.ca/sedi"
_SEDI_SEARCH = f"{_SEDI_BASE}/SVTSearchFilingsResults.do"


@register
class SEDIScraper(BaseScraper):
    source_id = "corporate_sedi"
    source_name = "SEDI Insider Trading"
    signal_types = ["insider_trade_sell", "insider_trade_cluster"]
    rate_limit_rps = 0.2
    concurrency = 1
    retry_attempts = 3
    timeout_seconds = 30.0
    ttl_seconds = 3600

    async def scrape(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []
        try:
            start_date = (datetime.now(tz=UTC) - timedelta(days=7)).strftime("%Y/%m/%d")
            end_date = datetime.now(tz=UTC).strftime("%Y/%m/%d")

            params = {
                "transactionFromDate": start_date,
                "transactionToDate": end_date,
                "transactionType": "D",  # Disposition = sale
                "searchType": "transaction",
                "language": "E",
            }
            response = await self.get(_SEDI_SEARCH, params=params)
            if response.status_code != 200:
                return results

            soup = BeautifulSoup(response.text, "html.parser")
            transactions = self._parse_transactions(soup)

            # Identify cluster selling: same company, multiple insiders, same week
            from collections import Counter

            company_counts = Counter(
                t["company_name"] for t in transactions if t.get("company_name")
            )

            for tx in transactions:
                company = tx.get("company_name")
                if not company:
                    continue

                is_cluster = company_counts[company] >= 3
                signal_type = "insider_trade_cluster" if is_cluster else "insider_trade_sell"

                # Only flag large sales (> $100k) or cluster events
                value = tx.get("value_cad", 0)
                if value < 100000 and not is_cluster:
                    continue

                results.append(
                    ScraperResult(
                        source_id=self.source_id,
                        signal_type=signal_type,
                        raw_company_name=company,
                        source_url=tx.get("url"),
                        signal_value={
                            "insider_name": tx.get("insider_name"),
                            "insider_role": tx.get("role"),
                            "transaction_date": tx.get("date"),
                            "security_type": tx.get("security_type"),
                            "quantity": tx.get("quantity"),
                            "price": tx.get("price"),
                            "value_cad": value,
                            "is_cluster": is_cluster,
                            "cluster_count": company_counts.get(company, 1),
                        },
                        signal_text=f"Insider sale: {tx.get('insider_name')} at {company} — ${value:,.0f}",
                        published_at=self._parse_date(tx.get("date")),
                        practice_area_hints=["securities", "governance"],
                        raw_payload=tx,
                    )
                )

            log.info("sedi_scrape_complete", total=len(results))
        except Exception as exc:
            log.error("sedi_scrape_error", error=str(exc), exc_info=True)
        return results

    def _parse_transactions(self, soup: BeautifulSoup) -> list[dict[str, Any]]:
        transactions = []
        try:
            rows = soup.find_all("tr")
            for row in rows[1:]:  # Skip header
                cells = row.find_all("td")
                if len(cells) < 7:
                    continue
                tx: dict[str, Any] = {
                    "insider_name": cells[0].get_text(strip=True),
                    "company_name": cells[1].get_text(strip=True),
                    "role": cells[2].get_text(strip=True),
                    "security_type": cells[3].get_text(strip=True),
                    "quantity": self._parse_number(cells[4].get_text(strip=True)),
                    "price": self._parse_number(cells[5].get_text(strip=True)),
                    "date": cells[6].get_text(strip=True),
                }
                tx["value_cad"] = (tx.get("quantity") or 0) * (tx.get("price") or 0)
                link = row.find("a")
                if link:
                    tx["url"] = f"{_SEDI_BASE}/{link.get('href', '')}"
                transactions.append(tx)
        except Exception as e:
            log.warning("sedi_parse_error", error=str(e))
        return transactions

    def _parse_number(self, s: str) -> float:
        try:
            return float(s.replace(",", "").replace("$", "").strip())
        except (ValueError, AttributeError):
            return 0.0
