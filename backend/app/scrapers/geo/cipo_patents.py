"""
app/scrapers/geo/cipo_patents.py — CIPO patent scraper re-export.

The primary implementation lives in geo_scrapers.py (CIPOPatentScraper, source_id=geo_cipo_patents).
"""

# Re-export from geo_scrapers.py — already registered there
from app.scrapers.geo.geo_scrapers import CIPOPatentScraper  # noqa: F401
