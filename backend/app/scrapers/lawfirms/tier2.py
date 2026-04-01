"""
app/scrapers/lawfirms/tier2.py — Tier 2 specialty law firm blog scrapers.
Importing firm_blogs triggers @register for all 12 Tier 2 firm scrapers.
"""

from __future__ import annotations

import importlib

importlib.import_module("app.scrapers.law_blogs.firm_blogs")
