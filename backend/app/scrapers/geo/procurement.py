"""
app/scrapers/geo/procurement.py — Government procurement scraper re-export.

The primary implementation lives in geo_scrapers.py (ProcurementScraper, source_id=geo_procurement).
"""

from __future__ import annotations

import importlib

importlib.import_module("app.scrapers.geo.geo_scrapers")
