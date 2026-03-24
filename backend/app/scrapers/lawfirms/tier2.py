"""
app/scrapers/lawfirms/tier2.py — Tier 2 specialty law firm blog scrapers.
Re-exports from law_blogs.firm_blogs where the actual scrapers live and self-register.
"""

# Importing firm_blogs triggers @register for all 12 Tier 2 firm scrapers
from app.scrapers.law_blogs.firm_blogs import (  # noqa: F401
    LawBlogBordenelliot2Scraper,
    LawBlogBordenelliotScraper,
    LawBlogDaviesScraper,
    LawBlogFrasermilnerScraper,
    LawBlogGoldmansloanScraper,
    LawBlogLangfordScraper,
    LawBlogLaxolearyScraper,
    LawBlogLencznerslaghtScraper,
    LawBlogLernersScraper,
    LawBlogMillerthomsonScraper,
    LawBlogOgilvyScraper,
    LawBlogThorntongroutScraper,
)
