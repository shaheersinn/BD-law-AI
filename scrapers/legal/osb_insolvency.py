"""app/scrapers/legal/osb_insolvency.py — OSB insolvency statistics (postal code level)."""
from __future__ import annotations
import io
from app.scrapers.base import BaseScraper, SignalData

class OsbInsolvencyScraper(BaseScraper):
    NAME = "osb_insolvency_stats"
    CATEGORY = "legal"
    SOURCE_URL = "https://www.ic.gc.ca/eic/site/bsf-osb.nsf/eng/br04551.html"
    RATE_LIMIT_RPS = 0.5
    MAX_CONCURRENT = 1
    SOURCE_RELIABILITY = 0.90

    # OSB open data Excel file URL
    _EXCEL_URL = "https://www.ic.gc.ca/eic/site/bsf-osb.nsf/vwapj/OSB_Insolvency_Statistics_Business.xlsx/$FILE/OSB_Insolvency_Statistics_Business.xlsx"

    async def run(self) -> list[SignalData]:
        """Download OSB insolvency Excel and extract recent business insolvencies."""
        signals: list[SignalData] = []
        try:
            import openpyxl
            response = await self.get(self._EXCEL_URL)
            if not response:
                return signals
            wb = openpyxl.load_workbook(io.BytesIO(response.content), read_only=True, data_only=True)
            ws = wb.active
            rows = list(ws.iter_rows(values_only=True))
            # Extract recent sector-level insolvency counts
            for row in rows[5:30]:  # Skip header rows
                if not row or not row[0]:
                    continue
                sector = str(row[0])
                count = row[-1] if row[-1] else 0
                if not sector or sector.strip() in ("", "Sector", "Industry"):
                    continue
                strength = min(0.90, 0.50 + (int(count or 0) / 100) * 0.40)
                signals.append(SignalData(
                    scraper_name=self.NAME, signal_type="insolvency_statistic",
                    raw_entity_name=sector,
                    title=f"OSB insolvency: {sector} — {count} filings",
                    summary=f"Business insolvency statistics: {sector}, count: {count}",
                    source_url=self.SOURCE_URL,
                    practice_areas=["insolvency_restructuring", "banking_finance"],
                    signal_strength=float(strength),
                    metadata={"sector": sector, "count": count, "source": "OSB"},
                ))
        except Exception as exc:
            self.log.error("OSB: error parsing Excel: %s", exc)
        return signals
