"""app/scrapers/legal/osb_insolvency.py — OSB insolvency statistics."""
from __future__ import annotations
import io
from app.scrapers.base import BaseScraper, SignalData
from app.scrapers.registry import register

@register
class OsbInsolvencyScraper(BaseScraper):
    source_id = "legal_osb_insolvency"
    source_name = "OSB Insolvency Statistics"
    CATEGORY = "legal"
    signal_types = ["insolvency_statistic"]
    SOURCE_URL = "https://www.ic.gc.ca/eic/site/bsf-osb.nsf/eng/br04551.html"
    rate_limit_rps = 0.5
    concurrency = 1
    SOURCE_RELIABILITY = 0.90

    _EXCEL_URL = (
        "https://www.ic.gc.ca/eic/site/bsf-osb.nsf/vwapj/"
        "OSB_Insolvency_Statistics_Business.xlsx/$FILE/"
        "OSB_Insolvency_Statistics_Business.xlsx"
    )

    async def scrape(self) -> list[SignalData]:
        signals: list[SignalData] = []
        try:
            import openpyxl
            response = await self.get(self._EXCEL_URL)
            if not response:
                return signals
            wb = openpyxl.load_workbook(
                io.BytesIO(response.content), read_only=True, data_only=True
            )
            ws = wb.active
            rows = list(ws.iter_rows(values_only=True))
            for row in rows[5:30]:
                if not row or not row[0]:
                    continue
                sector = str(row[0])
                count = row[-1] if row[-1] else 0
                if not sector or sector.strip() in ("", "Sector", "Industry"):
                    continue
                strength = min(0.90, 0.50 + (int(count or 0) / 100) * 0.40)
                signals.append(SignalData(
                    source_id=self.source_id,
                    signal_type="insolvency_statistic",
                    raw_company_name=sector,
                    signal_text=f"OSB insolvency: {sector} — {count} filings",
                    source_url=self.SOURCE_URL,
                    practice_area_hints=["insolvency_restructuring", "banking_finance"],
                    confidence_score=float(strength),
                    signal_value={"sector": sector, "count": count, "source": "OSB"},
                ))
        except Exception as exc:
            self.log.error("OSB: error parsing Excel: %s", exc)
        return signals
