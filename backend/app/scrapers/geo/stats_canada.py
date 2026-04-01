"""
app/scrapers/geo/stats_canada.py — Statistics Canada scraper re-export.

The primary implementation lives in statscan.py (StatsCanScraper, source_id=geo_statscan).
This stub provides an alternate import path; loading the module registers the scraper.
"""

from __future__ import annotations

import importlib

importlib.import_module("app.scrapers.geo.statscan")
