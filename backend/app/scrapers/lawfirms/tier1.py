"""
app/scrapers/lawfirms/tier1.py — Bay Street Tier 1 law firm blog scrapers.
Re-exports from law_blogs.firm_blogs where the actual scrapers live and self-register.
"""

# Importing firm_blogs triggers @register for all 15 Tier 1 firm scrapers
from app.scrapers.law_blogs.firm_blogs import (  # noqa: F401
    LawBlogBennettjonesScraper,
    LawBlogBlakesScraper,
    LawBlogBlgScraper,
    LawBlogCasselsScraper,
    LawBlogDentonsScraper,
    LawBlogDlapiperScraper,
    LawBlogFaskenScraper,
    LawBlogGoodmansScraper,
    LawBlogGowlingScraper,
    LawBlogMccarthyScraper,
    LawBlogMcmillanScraper,
    LawBlogNortonroseScraper,
    LawBlogOslerScraper,
    LawBlogStikemanScraper,
    LawBlogTorysScraper,
)
