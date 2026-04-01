"""app/scrapers/filings/iaac.py — Impact Assessment Agency of Canada."""

from __future__ import annotations

from app.scrapers.base import BaseScraper, SignalData


class IaacScraper(BaseScraper):
    source_id = "filings_iaac"
    source_name = "IAAC Assessments"
    CATEGORY = "corporate"
    signal_types = ["impact_assessment"]
    SOURCE_URL = "https://iaac-aeic.gc.ca"
    rate_limit_rps = 1.0
    concurrency = 2
    SOURCE_RELIABILITY = 0.9

    async def scrape(self) -> list[SignalData]:
        signals: list[SignalData] = []
        # IAAC open data API
        url = "https://iaac-aeic.gc.ca/050/evaluations/proj/api/projects"
        data = await self.get_json(url)
        if data is None:
            return signals
        projects = data if isinstance(data, list) else data.get("projects", [])
        for project in projects[:50]:
            name = project.get("projectName", project.get("name", ""))
            status = project.get("currentPhase", project.get("status", ""))
            sector = project.get("sector", "")
            province = project.get("province", "")
            if not name:
                continue
            practice_areas = ["environmental_indigenous_energy", "mining_natural_resources"]
            if "indigenous" in name.lower() or "first nation" in name.lower():
                practice_areas.insert(0, "administrative_public_law")
            signals.append(
                SignalData(
                    source_id=self.source_id,
                    signal_type="impact_assessment",
                    raw_company_name=name,
                    signal_text=f"Federal impact assessment: {name}, sector: {sector}, province: {province}, status: {status}",
                    source_url=self.SOURCE_URL,
                    practice_area_hints=practice_areas,
                    confidence_score=0.65,
                    signal_value={
                        "status": status,
                        "sector": sector,
                        "province": province,
                        "title": f"IAAC assessment: {name} ({status})",
                    },
                )
            )
        return signals
