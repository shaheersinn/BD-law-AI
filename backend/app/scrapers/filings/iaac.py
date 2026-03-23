"""app/scrapers/filings/iaac.py — Impact Assessment Agency of Canada."""
from __future__ import annotations
from app.scrapers.base import BaseScraper, SignalData

class IaacScraper(BaseScraper):
    NAME = "iaac_assessments"
    CATEGORY = "filings"
    SOURCE_URL = "https://iaac-aeic.gc.ca"
    RATE_LIMIT_RPS = 1.0
    MAX_CONCURRENT = 2
    SOURCE_RELIABILITY = 0.9

    async def run(self) -> list[SignalData]:
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
            signals.append(SignalData(
                scraper_name=self.NAME,
                signal_type="impact_assessment",
                raw_entity_name=name,
                title=f"IAAC assessment: {name} ({status})",
                summary=f"Federal impact assessment: {name}, sector: {sector}, province: {province}, status: {status}",
                source_url=self.SOURCE_URL,
                practice_areas=practice_areas,
                signal_strength=0.65,
                metadata={"status": status, "sector": sector, "province": province},
            ))
        return signals
