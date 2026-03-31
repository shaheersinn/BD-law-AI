"""
app/scrapers/geo/municipal_permits.py — Municipal building permits scraper.

Sources:
  - Toronto Open Data CKAN API (building permits cleared)
  - Vancouver Open Data (Socrata-style API — issued building permits)

Signal types:
  geo_permit_major_construction — permit value > $10M (real estate/construction signal)
  geo_permit_demolition         — demolition permit (distress signal)
  geo_permit_issued             — significant permit ($1M–$10M)

Rate: 0.3 rps (open data portals, respectful)
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

# Toronto Open Data CKAN API
_TORONTO_CKAN_API = "https://ckan0.cf.opendata.inter.prod-toronto.ca/api/3/action/datastore_search"
_TORONTO_RESOURCE_ID = "7ac3e86d-1b9b-43aa-8c2e-4e72f4d2ca8c"

# Vancouver Open Data (OData / records endpoint)
_VANCOUVER_API = (
    "https://opendata.vancouver.ca/api/explore/v2.1/catalog/datasets/"
    "issued-building-permits/records"
)

_MIN_PERMIT_VALUE = 1_000_000  # Skip permits under $1M
_MAJOR_THRESHOLD = 10_000_000  # $10M+ = major construction signal


@register
class MunicipalPermitsScraper(BaseScraper):
    """
    Municipal building permits scraper.

    Scrapes major Canadian city open data portals for building permits —
    signals construction activity, real estate disputes, zoning conflicts.
    """

    source_id = "geo_municipal"
    source_name = "Municipal Building Permits (Toronto/Vancouver/Calgary)"
    signal_types = [
        "geo_permit_major_construction",
        "geo_permit_demolition",
        "geo_permit_issued",
    ]
    CATEGORY = "geo"
    rate_limit_rps = 0.3
    concurrency = 1
    requires_auth = False
    timeout_seconds = 45.0

    async def scrape(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []

        # Toronto CKAN API
        try:
            results.extend(await self._scrape_toronto())
        except Exception as exc:
            log.error("municipal_toronto_error", error=str(exc))

        await self._rate_limit_sleep()

        # Vancouver Open Data
        try:
            results.extend(await self._scrape_vancouver())
        except Exception as exc:
            log.error("municipal_vancouver_error", error=str(exc))

        return results

    async def _scrape_toronto(self) -> list[ScraperResult]:
        """Toronto Open Data CKAN API — building permits cleared."""
        cutoff = (datetime.now(tz=UTC) - timedelta(days=30)).strftime("%Y-%m-%d")

        data = await self.get_json(
            _TORONTO_CKAN_API,
            params={
                "resource_id": _TORONTO_RESOURCE_ID,
                "limit": 100,
                "filters": json.dumps({"STATUS": "Issued"}),
                "sort": "ISSUED_DATE desc",
            },
        )
        if not data or not data.get("success"):
            log.warning("toronto_permits_no_data")
            return []

        records = data.get("result", {}).get("records", [])
        results: list[ScraperResult] = []
        for rec in records:
            parsed = self._parse_toronto_permit(rec, cutoff)
            if parsed:
                results.append(parsed)

        log.info("toronto_permits_parsed", count=len(results), total=len(records))
        return results

    def _parse_toronto_permit(self, rec: dict, cutoff: str) -> ScraperResult | None:
        """Parse a single Toronto building permit record."""
        issued_date = rec.get("ISSUED_DATE", "")
        if issued_date and issued_date < cutoff:
            return None

        value = float(rec.get("ESTIMATED_CONST_COST", 0) or 0)
        if value < _MIN_PERMIT_VALUE:
            return None

        company = (rec.get("APPLICANT") or rec.get("OWNER") or "").strip()
        permit_type = (rec.get("PERMIT_TYPE") or "").strip()

        if "demolition" in permit_type.lower():
            signal_type = "geo_permit_demolition"
        elif value >= _MAJOR_THRESHOLD:
            signal_type = "geo_permit_major_construction"
        else:
            signal_type = "geo_permit_issued"

        return ScraperResult(
            source_id=self.source_id,
            signal_type=signal_type,
            raw_company_name=company or None,
            source_url="https://open.toronto.ca/dataset/building-permits-cleared/",
            signal_value={
                "city": "Toronto",
                "permit_value": value,
                "permit_type": permit_type,
                "applicant": company,
                "address": rec.get("STREET_NAME", ""),
            },
            signal_text=(
                f"Building permit: {company or 'Unknown'} — ${value:,.0f} "
                f"({permit_type}) in Toronto"
            ),
            published_at=self._parse_date(issued_date),
            practice_area_hints=["real_estate", "construction", "environmental"],
            raw_payload=rec,
            confidence_score=0.6,
        )

    async def _scrape_vancouver(self) -> list[ScraperResult]:
        """Vancouver Open Data — issued building permits."""
        cutoff = (datetime.now(tz=UTC) - timedelta(days=30)).strftime("%Y-%m-%d")

        data = await self.get_json(
            _VANCOUVER_API,
            params={
                "limit": 100,
                "order_by": "issuedate desc",
                "where": f"issuedate >= '{cutoff}'",
            },
        )
        if not data:
            log.warning("vancouver_permits_no_data")
            return []

        records = data.get("results", [])
        results: list[ScraperResult] = []
        for rec in records:
            parsed = self._parse_vancouver_permit(rec)
            if parsed:
                results.append(parsed)

        log.info("vancouver_permits_parsed", count=len(results), total=len(records))
        return results

    def _parse_vancouver_permit(self, rec: dict) -> ScraperResult | None:
        """Parse a single Vancouver building permit record."""
        value = float(rec.get("projectvalue", 0) or 0)
        if value < _MIN_PERMIT_VALUE:
            return None

        applicant = (rec.get("applicant") or "").strip()
        type_of_work = (rec.get("typeofwork") or "").strip()

        if "demolition" in type_of_work.lower():
            signal_type = "geo_permit_demolition"
        elif value >= _MAJOR_THRESHOLD:
            signal_type = "geo_permit_major_construction"
        else:
            signal_type = "geo_permit_issued"

        return ScraperResult(
            source_id=self.source_id,
            signal_type=signal_type,
            raw_company_name=applicant or None,
            source_url="https://opendata.vancouver.ca/explore/dataset/issued-building-permits/",
            signal_value={
                "city": "Vancouver",
                "permit_value": value,
                "type_of_work": type_of_work,
                "applicant": applicant,
                "address": rec.get("address", ""),
                "category": rec.get("permitcategory", ""),
            },
            signal_text=(
                f"Building permit: {applicant or 'Unknown'} — ${value:,.0f} "
                f"({type_of_work}) in Vancouver"
            ),
            published_at=self._parse_date(rec.get("issuedate")),
            practice_area_hints=["real_estate", "construction", "environmental"],
            raw_payload=rec,
            confidence_score=0.6,
        )
