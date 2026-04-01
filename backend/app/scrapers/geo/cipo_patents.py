"""
app/scrapers/geo/cipo_patents.py — CIPO patent scraper re-export.

The primary implementation lives in geo_scrapers.py (CIPOPatentScraper, source_id=geo_cipo_patents).
"""

from __future__ import annotations

import importlib

importlib.import_module("app.scrapers.geo.geo_scrapers")
