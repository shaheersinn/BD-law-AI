"""
app/scrapers/lawfirms/tier1.py — Bay Street Tier 1 law firm blog scrapers.
Importing firm_blogs triggers @register for all 15 Tier 1 firm scrapers.
"""

from __future__ import annotations

import importlib

importlib.import_module("app.scrapers.law_blogs.firm_blogs")
