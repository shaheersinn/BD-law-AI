"""
app/scrapers/geo/opensky.py — OpenSky Network corporate flight tracking.

Source: https://opensky-network.org/api
  - /states/all — real-time aircraft states (anonymous: 400 req/day)
  - /flights/arrival — arrivals at an airport within a time range

Corporate jet travel patterns are M&A due diligence proxies:
  - Unusual flights between city pairs with known corporate HQs
  - Cluster of business jets at same destination within a week

Signal types:
  geo_flight_corporate_jet — business jet detected at Canadian hub airport
  geo_executive_travel     — repeated flights on same city pair (3+ in 7 days)

Rate: 0.1 rps (OpenSky anonymous limit: ~400 calls/day)
"""

from __future__ import annotations

import time
from datetime import UTC, datetime

import structlog

from app.config import get_settings
from app.scrapers.base import BaseScraper, ScraperResult
from app.scrapers.registry import register

log = structlog.get_logger(__name__)

_OPENSKY_ARRIVALS = "https://opensky-network.org/api/flights/arrival"

# Major Canadian business hub airports (ICAO codes)
_CANADIAN_HUBS: dict[str, str] = {
    "CYYZ": "Toronto Pearson",
    "CYVR": "Vancouver International",
    "CYYC": "Calgary International",
    "CYUL": "Montreal Trudeau",
    "CYOW": "Ottawa Macdonald-Cartier",
}

# ICAO type designators for common business jets
_BIZJET_TYPES: set[str] = {
    # Gulfstream
    "GL5T",
    "GL6T",
    "GL7T",
    "GLEX",
    "G150",
    "G280",
    "G350",
    "G450",
    "G550",
    "G650",
    # Bombardier
    "CL30",
    "CL35",
    "CL60",
    "BD70",
    "C56X",
    "C680",
    "C68A",
    "C700",
    "C750",
    # Dassault Falcon
    "F2TH",
    "FA7X",
    "FA8X",
    "F900",
    # Embraer
    "E35L",
    "E50P",
    "E55P",
}

# 2-hour window for arrival queries
_QUERY_WINDOW_SECONDS = 7200


@register
class OpenSkyScraper(BaseScraper):
    """
    OpenSky Network flight tracking scraper.

    Monitors private jet and corporate aircraft movements as a proxy for
    executive travel signals — M&A due diligence, emergency board meetings.
    """

    source_id = "geo_opensky"
    source_name = "OpenSky Network (Corporate Flight Tracking)"
    signal_types = ["geo_flight_corporate_jet", "geo_executive_travel"]
    CATEGORY = "geo"
    rate_limit_rps = 0.1
    concurrency = 1
    requires_auth = False  # Free anonymous tier available
    timeout_seconds = 30.0

    async def scrape(self) -> list[ScraperResult]:
        """Query arrivals at Canadian hub airports for business jet activity."""
        results: list[ScraperResult] = []
        now = int(time.time())
        begin = now - _QUERY_WINDOW_SECONDS

        settings = get_settings()
        auth = None
        opensky_user = getattr(settings, "opensky_username", "")
        opensky_pass = getattr(settings, "opensky_password", "")
        if opensky_user and opensky_pass:
            auth = (opensky_user, opensky_pass)

        for icao, airport_name in _CANADIAN_HUBS.items():
            try:
                arrivals = await self._fetch_arrivals(icao, begin, now, auth)
                for flight in arrivals:
                    parsed = self._parse_flight(flight, icao, airport_name)
                    if parsed:
                        results.append(parsed)
                await self._rate_limit_sleep()
            except Exception as exc:
                log.error("opensky_airport_error", airport=icao, error=str(exc))

        log.info("opensky_scrape_complete", results=len(results))
        return results

    async def _fetch_arrivals(
        self, airport: str, begin: int, end: int, auth: tuple[str, str] | None
    ) -> list[dict]:
        """Fetch arrivals at a given airport in the time window."""
        headers: dict[str, str] = {}
        if auth:
            import base64

            creds = base64.b64encode(f"{auth[0]}:{auth[1]}".encode()).decode()
            headers["Authorization"] = f"Basic {creds}"

        data = await self.get_json(
            _OPENSKY_ARRIVALS,
            params={"airport": airport, "begin": str(begin), "end": str(end)},
            headers=headers,
        )
        if not data or not isinstance(data, list):
            return []
        return data

    def _parse_flight(self, flight: dict, dest_icao: str, dest_name: str) -> ScraperResult | None:
        """Parse an OpenSky arrival record into a ScraperResult."""
        callsign = (flight.get("callsign") or "").strip()
        icao24 = flight.get("icao24", "")
        origin = flight.get("estDepartureAirport") or "Unknown"
        last_seen = flight.get("lastSeen")

        # We can't filter by aircraft type in the arrivals API, so
        # we report all arrivals and let downstream scoring weigh them.
        # Callsigns starting with common bizjet operator prefixes are higher signal.
        is_bizjet_callsign = any(
            callsign.startswith(prefix)
            for prefix in ("GLF", "CL60", "EJA", "NJA", "FLX", "XOJ", "VNR")
        )
        confidence = 0.7 if is_bizjet_callsign else 0.4

        return ScraperResult(
            source_id=self.source_id,
            signal_type="geo_flight_corporate_jet",
            source_url=f"https://opensky-network.org/aircraft-profile?icao24={icao24}",
            signal_value={
                "callsign": callsign,
                "icao24": icao24,
                "origin_airport": origin,
                "destination_airport": dest_icao,
                "destination_name": dest_name,
                "last_seen": last_seen,
                "is_bizjet_callsign": is_bizjet_callsign,
            },
            signal_text=(
                f"Flight {callsign or icao24} arrived at {dest_name} ({dest_icao}) from {origin}"
            ),
            published_at=self._parse_timestamp(last_seen),
            practice_area_hints=["m_and_a", "securities"],
            raw_payload=flight,
            confidence_score=confidence,
        )

    @staticmethod
    def _parse_timestamp(ts: int | None) -> datetime | None:
        """Convert Unix timestamp to UTC datetime."""
        if not ts:
            return None

        try:
            return datetime.fromtimestamp(ts, tz=UTC)
        except (OSError, ValueError):
            return None
