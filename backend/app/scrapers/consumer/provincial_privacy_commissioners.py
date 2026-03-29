"""
app/scrapers/consumer/provincial_privacy_commissioners.py — Provincial privacy commissioners.

Sources:
  - Ontario IPC:  https://www.ipc.on.ca/decisions-and-resolutions/
  - BC OIPC:      https://www.oipc.bc.ca/decisions/
  - Alberta OIPC: https://www.oipc.ab.ca/decisions/

What it scrapes:
  - Privacy breach decisions and investigation reports from Ontario, BC, and Alberta
  - Commissioner orders against private sector organizations
  - Mediated resolutions involving data breaches

Signal types:
  - privacy_provincial_finding: Provincial privacy commissioner decision

Practice areas: privacy_cybersecurity, class_actions

Why: Provincial findings often pre-date or accompany OPC findings.
     Commissioner orders (not just findings) are the highest-value signal —
     they confirm a breach that is actionable under provincial private right of action.
"""

from __future__ import annotations

from dataclasses import dataclass

import structlog

from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_PRACTICE_AREAS = ["privacy_cybersecurity", "class_actions"]


@dataclass
class _CommissionerConfig:
    name: str
    decisions_url: str
    base_url: str
    province: str


_COMMISSIONERS = [
    _CommissionerConfig(
        name="Ontario IPC",
        decisions_url="https://www.ipc.on.ca/decisions-and-resolutions/",
        base_url="https://www.ipc.on.ca",
        province="ON",
    ),
    _CommissionerConfig(
        name="BC OIPC",
        decisions_url="https://www.oipc.bc.ca/decisions/",
        base_url="https://www.oipc.bc.ca",
        province="BC",
    ),
    _CommissionerConfig(
        name="Alberta OIPC",
        decisions_url="https://www.oipc.ab.ca/decisions/",
        base_url="https://www.oipc.ab.ca",
        province="AB",
    ),
]


@register
class ProvincialPrivacyCommissionersScraper(BaseScraper):
    source_id = "consumer_provincial_privacy_commissioners"
    source_name = "Provincial Privacy Commissioners (ON/BC/AB)"
    CATEGORY = "consumer"
    signal_types = ["privacy_provincial_finding"]
    rate_limit_rps = 0.1
    concurrency = 1
    ttl_seconds = 21600  # 6-hour cache

    async def scrape(self) -> list[ScraperResult]:
        results: list[ScraperResult] = []
        for commissioner in _COMMISSIONERS:
            try:
                commissioner_results = await self._scrape_commissioner(commissioner)
                results.extend(commissioner_results)
            except Exception as exc:
                log.error(
                    "provincial_privacy_commissioner_error",
                    commissioner=commissioner.name,
                    error=str(exc),
                )
        return results

    async def _scrape_commissioner(
        self, config: _CommissionerConfig
    ) -> list[ScraperResult]:
        results: list[ScraperResult] = []
        try:
            soup = await self.get_soup(config.decisions_url)
            if soup is None:
                log.warning("provincial_privacy_no_soup", commissioner=config.name)
                return results

            # Decision pages vary by jurisdiction but all have lists of decisions
            for item in soup.select("article, .decision, li, tr, .result-item"):
                title_el = item.find(["h2", "h3", "h4", "a", "td"])
                if not title_el:
                    continue
                title = self.safe_text(title_el)
                if not title or len(title) < 10:
                    continue

                # Filter for privacy-related decisions only
                if not self._is_privacy_decision(title):
                    continue

                link_el = item.find("a", href=True)
                url = ""
                if link_el:
                    href = link_el.get("href", "")
                    url = href if href.startswith("http") else f"{config.base_url}{href}"

                date_el = item.find(["time", ".date", "td"])
                date_str = self.safe_text(date_el) if date_el else ""

                description_el = item.find("p")
                description = self.safe_text(description_el) if description_el else ""

                organization = self._extract_organization(title, description)
                decision_type = self._classify_decision(title, description)
                is_order = "order" in title.lower() or "order" in decision_type

                results.append(
                    ScraperResult(
                        source_id=self.source_id,
                        signal_type="privacy_provincial_finding",
                        raw_company_name=organization,
                        source_url=url or config.decisions_url,
                        signal_value={
                            "title": title,
                            "commissioner": config.name,
                            "province": config.province,
                            "organization": organization,
                            "decision_type": decision_type,
                            "is_order": is_order,
                            "date": date_str,
                            "description": description[:500],
                        },
                        signal_text=f"{config.name} Decision: {title}",
                        # Orders are higher-confidence class action signals
                        confidence_score=0.9 if is_order else 0.75,
                        published_at=self._parse_date(date_str),
                        practice_area_hints=_PRACTICE_AREAS,
                        raw_payload={
                            "title": title,
                            "url": url,
                            "commissioner": config.name,
                            "province": config.province,
                        },
                    )
                )
                await self._rate_limit_sleep()

        except Exception as exc:
            log.error(
                "provincial_privacy_scrape_error",
                commissioner=config.name,
                error=str(exc),
            )

        return results

    @staticmethod
    def _is_privacy_decision(title: str) -> bool:
        text = title.lower()
        return any(
            k in text
            for k in [
                "privacy", "personal information", "pipeda", "phipa", "foippa",
                "breach", "disclosure", "collection", "consent", "access",
                "order", "investigation", "finding", "decision",
            ]
        )

    @staticmethod
    def _classify_decision(title: str, description: str) -> str:
        text = f"{title} {description}".lower()
        if "order" in text:
            return "order"
        if "breach" in text or "incident" in text:
            return "breach_investigation"
        if "access" in text and "request" in text:
            return "access_request"
        if "complaint" in text:
            return "complaint_investigation"
        return "general_finding"

    @staticmethod
    def _extract_organization(title: str, description: str) -> str | None:
        combined = f"{title} {description}"
        lower = combined.lower()

        # Pattern: "Decision re: [Organization]" or "Order against [Organization]"
        for sep in [" re: ", " against ", " involving ", " v. ", " vs. "]:
            if sep in lower:
                idx = lower.index(sep)
                candidate = combined[idx + len(sep) : idx + len(sep) + 80]
                candidate = candidate.split(".")[0].split(",")[0].strip()
                if 3 < len(candidate) < 80:
                    return candidate

        # Pattern: "Organization Name — Finding"
        if "—" in combined:
            parts = combined.split("—")
            if len(parts) >= 2:
                candidate = parts[0].strip()
                if 3 < len(candidate) < 80:
                    return candidate

        return None
