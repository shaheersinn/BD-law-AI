"""
app/scrapers/geo/stats_canada.py — Statistics Canada scraper re-export.

The primary implementation lives in statscan.py (StatsCanScraper, source_id=geo_statscan).
This stub provides a separate source_id entry for additional StatsCan data tables.
"""

# Re-export from statscan.py — triggers registration
from app.scrapers.geo.statscan import StatsCanScraper  # noqa: F401
