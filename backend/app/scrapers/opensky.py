"""
app/scrapers/opensky.py — Corporate jet tracker via OpenSky Network REST API.
Free account at opensky-network.org gives 400 API credits/day.
Schedule: daily at 3am, or on-demand for watch-list tail numbers.
"""

import logging
from datetime import UTC, datetime, timedelta

import httpx

from app.config import get_settings
from app.scrapers.base import BaseScraper

log = logging.getLogger(__name__)
settings = get_settings()

OPENSKY_BASE = "https://opensky-network.org/api"

# Bay Street proximity airports (ICAO codes)
BAY_STREET_AIRPORTS = set(settings.jet_bay_street_airports)

# Airports considered "deal hub" — adds to confidence
DEAL_HUB_AIRPORTS = {
    "KJFK",
    "KEWR",
    "KLGA",  # New York
    "EGLL",
    "EGLC",
    "EGKK",  # London
    "LFPG",
    "LFPO",  # Paris
    "EHAM",  # Amsterdam
    "CYTZ",
    "CYYZ",  # Toronto
    "CYVR",  # Vancouver
}


class OpenSkyScraper(BaseScraper):
    """
    Fetches flight history for a list of tail numbers (aircraft ICAO24 codes).
    Maps Bay Street trip patterns to mandate signals.
    """

    source_name = "OPENSKY"
    request_delay_seconds = 1.5

    def __init__(self) -> None:
        super().__init__()
        self._auth: tuple[str, str] | None = None
        if settings.opensky_username and settings.opensky_password:
            self._auth = (settings.opensky_username, settings.opensky_password)

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            auth = self._auth
            self._client = httpx.AsyncClient(
                timeout=settings.scraper_timeout_seconds,
                headers={"User-Agent": settings.scraper_user_agent},
                auth=auth,
                follow_redirects=True,
            )
        return self._client

    async def get_flights_for_aircraft(
        self,
        icao24: str,
        days_back: int = 14,
    ) -> list[dict]:
        """
        Fetch flight history for one aircraft ICAO24 address.
        Returns list of {departure_airport, arrival_airport, departed_at, arrived_at}.
        """
        end_ts = int(datetime.now(UTC).timestamp())
        start_ts = int((datetime.now(UTC) - timedelta(days=days_back)).timestamp())

        url = f"{OPENSKY_BASE}/flights/aircraft"
        params = {
            "icao24": icao24.lower(),
            "begin": start_ts,
            "end": end_ts,
        }

        try:
            resp = await self._get(url, params=params)
            data = resp.json()
            if not isinstance(data, list):
                return []

            flights = []
            for flight in data:
                dep = flight.get("estDepartureAirport") or ""
                arr = flight.get("estArrivalAirport") or ""
                depart_ts = flight.get("firstSeen", 0)

                flights.append(
                    {
                        "departure_airport": dep.upper(),
                        "arrival_airport": arr.upper(),
                        "departed_at": datetime.fromtimestamp(depart_ts, tz=UTC),
                    }
                )
            return flights

        except Exception as e:
            log.debug("OpenSky error for %s: %s", icao24, e)
            return []

    def analyse_flights(
        self,
        company: str,
        tail_number: str,
        executive: str,
        flights: list[dict],
        relationship_warmth: int = 0,
    ) -> dict | None:
        """
        Analyse flight history for Bay Street / deal-hub patterns.
        Returns a dict ready for JetTrack creation, or None if no signal.
        """
        bay_street_trips = [
            f
            for f in flights
            if f["arrival_airport"] in BAY_STREET_AIRPORTS
            or f["departure_airport"] in BAY_STREET_AIRPORTS
        ]

        [
            f
            for f in flights
            if f["arrival_airport"] in DEAL_HUB_AIRPORTS
            or f["departure_airport"] in DEAL_HUB_AIRPORTS
        ]

        # Pattern: 2+ Bay Street trips within 14 days
        if len(bay_street_trips) >= 2:
            latest = max(bay_street_trips, key=lambda f: f["departed_at"])
            dest = latest["arrival_airport"]
            dest_name = _airport_name(dest)
            count = len(bay_street_trips)

            # Confidence: 2 trips = 72%, 3+ trips = 88%, deal hub = +5%
            confidence = min(72 + (count - 2) * 8, 91)
            if any(f["arrival_airport"] in DEAL_HUB_AIRPORTS for f in bay_street_trips):
                confidence = min(confidence + 5, 96)

            signal_text = (
                f"{count}× Bay Street / deal hub trip{'s' if count > 1 else ''}"
                f" in {14} days — last: {dest_name}"
            )

            return {
                "company": company,
                "tail_number": tail_number,
                "executive": executive,
                "origin_icao": latest["departure_airport"],
                "origin_name": _airport_name(latest["departure_airport"]),
                "dest_icao": dest,
                "dest_name": dest_name,
                "departed_at": latest["departed_at"],
                "signal_text": signal_text,
                "predicted_mandate": "Corporate / M&A",
                "confidence": confidence,
                "relationship_warmth": relationship_warmth,
                "bay_street_trip_count": count,
                "is_flagged": True,
            }

        return None

    async def fetch_new(self) -> list:
        """Stub — Celery task injects the watchlist."""
        return []


def _airport_name(icao: str) -> str:
    names = {
        "CYTZ": "Toronto Billy Bishop",
        "CYYZ": "Toronto Pearson",
        "KJFK": "New York JFK",
        "KEWR": "New York Newark",
        "KLGA": "New York LaGuardia",
        "EGLL": "London Heathrow",
        "EGLC": "London City",
        "CYVR": "Vancouver YVR",
        "LFPG": "Paris CDG",
        "EHAM": "Amsterdam Schiphol",
    }
    return names.get(icao, icao)
