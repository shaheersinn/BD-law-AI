"""
app/scrapers/geo/procurement.py — Government procurement scraper re-export.

The primary implementation lives in geo_scrapers.py (ProcurementScraper, source_id=geo_procurement).
"""

# Re-export from geo_scrapers.py — already registered there
from app.scrapers.geo.geo_scrapers import ProcurementScraper  # noqa: F401
