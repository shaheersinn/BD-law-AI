"""
app/scrapers/geo/cfcj.py — Canadian Forum on Civil Justice cost of access data.
app/scrapers/geo/cipo.py — CIPO patent filings (IP signal).
app/scrapers/geo/procurement.py — Government procurement (contract disputes signal).
app/scrapers/geo/domain_intel.py — Domain registration changes (corporate activity signal).
app/scrapers/geo/municipal_property.py — Municipal property tax changes.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET  # nosec B405

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)


# ── CIPO Patents ───────────────────────────────────────────────────────────────
@register
class CIPOPatentScraper(BaseScraper):
    """
    CIPO (Canadian Intellectual Property Office) — patent filings & grants.

    Source: https://patents.google.com (filtered Canada)
            https://www.ic.gc.ca/opic-cipo/cpd/eng/search/quick.html

    Signal: heavy patent filing activity → IP litigation risk / licensing disputes.
    """

    source_id = "geo_cipo_patents"
    source_name = "CIPO Patent Database"
    CATEGORY = "geo"
    signal_types = ["geo_cipo_patent_filing", "geo_cipo_patent_grant"]
    rate_limit_rps = 0.1
    concurrency = 1
    ttl_seconds = 86400

    async def scrape(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []
        try:
            # CIPO open data — recent patent grants
            url = "https://open.canada.ca/data/en/dataset/11d5f11e-e0a2-4aa5-bb17-cf3a74e70e24/resource/45abc5c6-b00f-4b5b-a6b5-f28b0e5aa5d3/download"
            response = await self.get(url)
            if response.status_code == 200:
                import csv
                import io

                reader = csv.DictReader(io.StringIO(response.text))
                for row in list(reader)[:100]:
                    applicant = row.get("Applicant", "").strip()
                    if not applicant:
                        continue
                    results.append(
                        ScraperResult(
                            source_id=self.source_id,
                            signal_type="geo_cipo_patent_grant",
                            raw_company_name=applicant,
                            signal_value={
                                "patent_number": row.get("Patent Number", ""),
                                "title": row.get("Title", ""),
                                "grant_date": row.get("Grant Date", ""),
                                "applicant": applicant,
                            },
                            signal_text=f"Patent grant: {applicant} — {row.get('Title', '')[:100]}",
                            published_at=self._parse_date(row.get("Grant Date", "")),
                            practice_area_hints=["ip"],
                            raw_payload=dict(row),
                            confidence_score=0.85,
                        )
                    )
        except Exception as exc:
            log.error("cipo_error", error=str(exc))
        return results


# ── Government Procurement ─────────────────────────────────────────────────────
@register
class ProcurementScraper(BaseScraper):
    """
    Buyandsell.gc.ca — Government of Canada procurement contracts.

    Source: https://buyandsell.gc.ca/procurement-data/tender-notices/rss

    Signal: contract awards + cancellations → government legal counsel needs.
            Large contract cancellations → litigation signal.
    """

    source_id = "geo_procurement"
    source_name = "Government of Canada Procurement (Buyandsell)"
    CATEGORY = "geo"
    signal_types = ["geo_procurement_contract_award", "geo_procurement_amendment"]
    rate_limit_rps = 0.1
    concurrency = 1
    ttl_seconds = 43200

    async def scrape(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []
        try:
            resp = await self.get("https://buyandsell.gc.ca/procurement-data/contract-history/rss")
            if resp.status_code != 200:
                return results
            root = ET.fromstring(resp.text)  # nosec B314 — trusted government/news RSS source
            for item in root.iter("item"):
                title = (item.findtext("title") or "").strip()
                title_lower = title.lower()
                if not any(
                    k in title_lower
                    for k in ["legal", "counsel", "advisory", "professional services"]
                ):
                    continue
                results.append(
                    ScraperResult(
                        source_id=self.source_id,
                        signal_type="geo_procurement_contract_award",
                        source_url=(item.findtext("link") or "").strip(),
                        signal_value={"title": title},
                        signal_text=f"Procurement: {title}",
                        published_at=self._parse_date((item.findtext("pubDate") or "").strip()),
                        practice_area_hints=["administrative", "regulatory"],
                        raw_payload={"title": title},
                    )
                )
        except Exception as exc:
            log.error("procurement_error", error=str(exc))
        return results


# ── Domain Intelligence ────────────────────────────────────────────────────────
@register
class DomainIntelScraper(BaseScraper):
    """
    Domain registration changes — corporate activity signals.

    A sudden domain registration that matches a corporate name pattern
    can signal: M&A (new entity created), rebranding after litigation,
    or litigation targeting (dispute domain registration).

    Source: CIRA (Canadian Internet Registration Authority) open data
            https://www.cira.ca/resources/statistics/registration-data
    """

    source_id = "geo_domain_intel"
    source_name = "CIRA Domain Intelligence"
    CATEGORY = "geo"
    signal_types = ["geo_domain_registration"]
    rate_limit_rps = 0.05
    concurrency = 1
    ttl_seconds = 86400

    async def scrape(self) -> list[ScraperResult]:
        # CIRA publishes .ca domain stats — bulk file is monthly
        # In Phase 1 we register for the CIRA open data feed
        # Actual scraping is low-priority — returns empty until Phase 5
        log.info(
            "domain_intel_stub_mode",
            note="CIRA bulk .ca zone file requires registration. Will activate in Phase 5.",
        )
        return []


# ── Municipal Property Tax ─────────────────────────────────────────────────────
@register
class MunicipalPropertyScraper(BaseScraper):
    """
    Municipal property tax arrears — financial distress leading indicator.

    Source: Toronto Open Data, Vancouver Open Data, Calgary Open Data

    Properties in tax arrears → corporate financial distress signal
    (especially commercial real estate + industrial properties)
    """

    source_id = "geo_municipal_property"
    source_name = "Municipal Property Tax Arrears"
    CATEGORY = "geo"
    signal_types = ["geo_property_tax_arrears"]
    rate_limit_rps = 0.1
    concurrency = 1
    ttl_seconds = 86400

    _TORONTO_URL = "https://ckan0.cf.opendata.inter.prod-toronto.ca/api/3/action/datastore_search?resource_id=fc1de0e0-d54e-4c79-98fb-6f7b0a6aa3bf&limit=100"

    async def scrape(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []
        try:
            resp = await self.get(self._TORONTO_URL)
            if resp.status_code == 200:
                data = resp.json()
                for rec in data.get("result", {}).get("records", []):
                    owner = rec.get("owner_name", "").strip()
                    arrears = rec.get("arrears_amount", 0)
                    try:
                        arrears_float = float(str(arrears).replace(",", ""))
                    except (ValueError, TypeError):
                        arrears_float = 0.0
                    if arrears_float < 50000:
                        continue
                    if not owner:
                        continue
                    results.append(
                        ScraperResult(
                            source_id=self.source_id,
                            signal_type="geo_property_tax_arrears",
                            raw_company_name=owner
                            if not owner[0].isalpha() or owner.isupper()
                            else None,
                            signal_value={
                                "owner": owner,
                                "arrears_cad": arrears_float,
                                "ward": rec.get("ward", ""),
                                "property_class": rec.get("property_class", ""),
                            },
                            signal_text=f"Property tax arrears: {owner} — ${arrears_float:,.0f}",
                            practice_area_hints=["real_estate", "insolvency"],
                            raw_payload=rec,
                            confidence_score=0.7,
                        )
                    )
        except Exception as exc:
            log.error("municipal_property_error", error=str(exc))
        return results


# ── CFCJ Access to Justice ────────────────────────────────────────────────────
@register
class CFCJScraper(BaseScraper):
    """
    Canadian Forum on Civil Justice — access to justice cost surveys.

    Source: https://cfcj-fcjc.org/cost-of-justice/

    Macro signal: rising cost-of-justice → increased litigation demand
    in specific practice areas or provinces.
    """

    source_id = "geo_cfcj"
    source_name = "Canadian Forum on Civil Justice"
    CATEGORY = "geo"
    signal_types = ["geo_cfcj_access_to_justice"]
    rate_limit_rps = 0.05
    concurrency = 1
    ttl_seconds = 604800  # 1 week

    async def scrape(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []
        try:
            resp = await self.get("https://cfcj-fcjc.org/feed/")
            if resp.status_code != 200:
                return results
            root = ET.fromstring(resp.text)  # nosec B314 — trusted government/news RSS source
            for item in root.iter("item"):
                title = (item.findtext("title") or "").strip()
                results.append(
                    ScraperResult(
                        source_id=self.source_id,
                        signal_type="geo_cfcj_access_to_justice",
                        source_url=(item.findtext("link") or "").strip(),
                        signal_value={"title": title},
                        signal_text=f"CFCJ: {title}",
                        published_at=self._parse_date((item.findtext("pubDate") or "").strip()),
                        practice_area_hints=["litigation", "administrative"],
                        raw_payload={"title": title},
                    )
                )
        except Exception as exc:
            log.error("cfcj_error", error=str(exc))
        return results
