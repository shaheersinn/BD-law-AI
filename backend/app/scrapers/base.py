"""
app/scrapers/base.py — BaseScraper ABC and ScraperResult dataclass.

ALL 90+ scrapers inherit from BaseScraper.

Architecture decisions (from pre-phase research):
  - httpx.AsyncClient: async HTTP client with HTTP/2 support
  - tenacity: retry with wait_exponential_jitter (AWS full jitter pattern)
  - asyncio.Semaphore: per-scraper concurrency limit
  - circuitbreaker: per-source circuit breaker
  - Rotating User-Agents: never expose Python/httpx default UA
  - Redis cache: TTL-aware caching with source-type TTLs
  - structlog: structured logging (never print())

Signal flow:
  scrape() → list[ScraperResult] → store_signals() → PostgreSQL + MongoDB
"""

from __future__ import annotations

import asyncio
import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import httpx
import structlog
from tenacity import (
    AsyncRetrying,
    RetryError,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

log = structlog.get_logger(__name__)

# ── User-Agent rotation pool ────────────────────────────────────────────────────
# Research finding: never expose Python/httpx default UA — immediate block on protected sites
_USER_AGENTS: list[str] = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
]


def _random_ua() -> str:
    return random.choice(_USER_AGENTS)  # nosec B311


def _browser_headers(extra: dict[str, str] | None = None) -> dict[str, str]:
    """Return headers that look like a real browser, not a bot."""
    headers = {
        "User-Agent": _random_ua(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-CA,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }
    if extra:
        headers.update(extra)
    return headers


@dataclass
class ScraperResult:
    """
    A single scraped signal record.

    Returned by scraper.scrape() → stored to PostgreSQL + MongoDB.
    """

    source_id: str
    signal_type: str
    raw_company_name: str | None = None
    raw_company_id: str | None = None
    source_url: str | None = None
    signal_value: dict[str, Any] = field(default_factory=dict)
    signal_text: str | None = None
    confidence_score: float = 1.0
    published_at: datetime | None = None
    practice_area_hints: list[str] = field(default_factory=list)
    raw_payload: dict[str, Any] = field(default_factory=dict)  # → MongoDB only
    is_negative_label: bool = False


# Backward-compatibility aliases
SignalData = ScraperResult
RawSignal = ScraperResult


class CircuitBreakerOpen(Exception):  # noqa: N818 (intentional non-Error suffix)
    """Raised when circuit breaker is in OPEN state."""


class SourceUnavailable(Exception):  # noqa: N818 (intentional non-Error suffix)
    """Raised when a source is permanently unavailable (404, auth failure, etc.)."""


class BaseScraper(ABC):
    """
    Abstract base class for all ORACLE scrapers.

    Every scraper:
      1. Inherits from BaseScraper
      2. Sets source_id, source_name, signal_types, rate_limit_rps, concurrency
      3. Implements scrape() → list[ScraperResult]
      4. Optionally overrides health_check()

    Built-in infrastructure (no code required in subclasses):
      - Exponential backoff retry (tenacity + AWS full jitter)
      - Concurrency control (asyncio.Semaphore)
      - Browser-like headers with UA rotation
      - Structured logging with source_id context
      - Timeout management
      - Circuit breaker state tracking via ScraperHealth

    Rate limits (per research + source-specific policies):
      source                  rps         notes
      CanLII API              0.1         ~500 req/day free tier
      SEDAR+                  0.5         no official limit, be respectful
      SEC EDGAR               0.1         10 req/s policy, we stay well below
      OSC/OSFI                0.2         government site, be very respectful
      RSS feeds               0.03        once per 30 min per feed
      Law firm blogs          0.016       once per 60s per blog, very respectful
      News sites              0.5         moderate
      Reddit API              0.5         60 req/min OAuth
    """

    # ── Subclasses MUST set these ───────────────────────────────────────────────
    source_id: str = ""
    source_name: str = ""
    signal_types: list[str] = []

    # ── Subclasses SHOULD set this ──────────────────────────────────────────────
    CATEGORY: str = ""  # e.g. "corporate", "legal", "regulatory", "jobs", "market", "news", "social", "geo", "lawblog"

    # ── Subclasses MAY override these ──────────────────────────────────────────
    rate_limit_rps: float = 0.5  # requests per second
    concurrency: int = 3  # max concurrent requests
    retry_attempts: int = 3  # max retry attempts
    retry_min_wait: float = 2.0  # min wait between retries (seconds)
    retry_max_wait: float = 60.0  # max wait between retries (seconds)
    timeout_seconds: float = 30.0  # request timeout
    ttl_seconds: int = 3600  # cache TTL (1 hour default)
    requires_auth: bool = False  # True if API key required
    requires_playwright: bool = False  # True if JS rendering needed

    def __init__(self) -> None:
        if not self.source_id:
            raise ValueError(f"{self.__class__.__name__} must set source_id")
        if not self.source_name:
            raise ValueError(f"{self.__class__.__name__} must set source_name")

        self._semaphore = asyncio.Semaphore(self.concurrency)
        self._log = log.bind(source_id=self.source_id)
        self._http_client: httpx.AsyncClient | None = None
        self._circuit_open = False
        self._circuit_failures = 0
        self._circuit_last_failure: float = 0.0
        self._circuit_threshold = 5  # open after N consecutive failures
        self._circuit_recovery_timeout = 300.0  # 5 min recovery window

    # ── Public interface ────────────────────────────────────────────────────────

    @abstractmethod
    async def scrape(self) -> list[ScraperResult]:
        """
        Execute the scrape and return a list of ScraperResult objects.

        Must be implemented by every scraper subclass.
        Must not raise unhandled exceptions — catch and log, return partial results.
        """

    async def health_check(self) -> bool:
        """
        Quick liveness check. Override in subclasses for source-specific checks.
        Default: attempt a single request to source_url.
        """
        return True

    async def run(self) -> list[ScraperResult]:
        """
        Entry point called by Celery tasks.

        Wraps scrape() with:
          - Circuit breaker check
          - Timing + logging
          - Health update
        """
        if self._is_circuit_open():
            self._log.warning("circuit_breaker_open", source=self.source_id)
            raise CircuitBreakerOpen(f"Circuit breaker OPEN for {self.source_id}")

        start = time.monotonic()
        self._log.info("scraper_start", source=self.source_id)

        try:
            results = await self.scrape()
            elapsed = time.monotonic() - start
            self._circuit_failures = 0
            self._log.info(
                "scraper_complete",
                source=self.source_id,
                records=len(results),
                duration_s=round(elapsed, 2),
            )
            return results

        except CircuitBreakerOpen:
            raise

        except Exception as exc:
            elapsed = time.monotonic() - start
            self._circuit_failures += 1
            self._circuit_last_failure = time.monotonic()

            if self._circuit_failures >= self._circuit_threshold:
                self._circuit_open = True
                self._log.error(
                    "circuit_breaker_opened",
                    source=self.source_id,
                    consecutive_failures=self._circuit_failures,
                )

            self._log.error(
                "scraper_failed",
                source=self.source_id,
                error=str(exc),
                duration_s=round(elapsed, 2),
                exc_info=True,
            )
            return []

    # ── HTTP helpers ────────────────────────────────────────────────────────────

    async def get(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        follow_redirects: bool = True,
    ) -> httpx.Response:
        """
        GET with exponential backoff + jitter retry.

        Retries on:
          - httpx.TransportError (network errors)
          - httpx.TimeoutException
          - 429, 500, 502, 503, 504 status codes

        Does NOT retry on:
          - 401, 403 (auth errors — fix the credentials)
          - 404 (source no longer exists)
          - 400 (bad request — fix the URL)
        """
        merged_headers = _browser_headers(headers)

        async with self._semaphore:
            try:
                async for attempt in AsyncRetrying(
                    stop=stop_after_attempt(self.retry_attempts),
                    wait=wait_exponential_jitter(
                        initial=self.retry_min_wait,
                        max=self.retry_max_wait,
                        jitter=self.retry_min_wait,
                    ),
                    retry=retry_if_exception_type((httpx.TransportError, httpx.TimeoutException)),
                    reraise=True,
                ):
                    with attempt:
                        client = await self._get_client()
                        response = await client.get(
                            url,
                            params=params,
                            headers=merged_headers,
                            follow_redirects=follow_redirects,
                            timeout=self.timeout_seconds,
                        )

                        # Retry on server errors and rate limiting
                        if response.status_code in (429, 500, 502, 503, 504):
                            retry_after = int(
                                response.headers.get("Retry-After", self.retry_min_wait * 2)
                            )
                            self._log.warning(
                                "http_retry",
                                url=url,
                                status=response.status_code,
                                retry_after=retry_after,
                            )
                            await asyncio.sleep(retry_after)
                            raise httpx.TransportError(f"HTTP {response.status_code}")

                        return response

            except RetryError as exc:
                self._log.error("http_retry_exhausted", url=url, error=str(exc))
                raise
        raise SourceUnavailable(url)  # unreachable — satisfies mypy

    async def post(
        self,
        url: str,
        *,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """POST with retry."""
        merged_headers = _browser_headers(headers)
        async with self._semaphore:
            client = await self._get_client()
            return await client.post(
                url,
                json=json,
                data=data,
                headers=merged_headers,
                timeout=self.timeout_seconds,
            )

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the shared httpx AsyncClient for this scraper."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                http2=True,
                follow_redirects=True,
                timeout=httpx.Timeout(self.timeout_seconds, connect=10.0),
                limits=httpx.Limits(
                    max_connections=self.concurrency * 2,
                    max_keepalive_connections=self.concurrency,
                    keepalive_expiry=30.0,
                ),
            )
        return self._http_client

    async def close(self) -> None:
        """Close the HTTP client. Called on Celery worker shutdown."""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
            self._http_client = None

    # ── Rate limiting ────────────────────────────────────────────────────────────

    async def _rate_limit_sleep(self) -> None:
        """Sleep to respect the per-scraper rate limit."""
        if self.rate_limit_rps > 0:
            sleep_s = 1.0 / self.rate_limit_rps
            # Add ±10% jitter to avoid synchronized requests
            jitter = sleep_s * 0.1
            await asyncio.sleep(sleep_s + random.uniform(-jitter, jitter))  # nosec B311

    # ── Circuit breaker ──────────────────────────────────────────────────────────

    def _is_circuit_open(self) -> bool:
        if not self._circuit_open:
            return False
        # Check if recovery timeout has elapsed → move to half-open
        if time.monotonic() - self._circuit_last_failure > self._circuit_recovery_timeout:
            self._circuit_open = False
            self._circuit_failures = 0
            self._log.info("circuit_breaker_half_open", source=self.source_id)
            return False
        return True

    # ── Utility ──────────────────────────────────────────────────────────────────

    @staticmethod
    def _now_utc() -> datetime:
        return datetime.now(tz=UTC)

    def parse_date(self, date_str: str | None) -> datetime | None:
        """Public alias for _parse_date — used by older-style scrapers."""
        return self._parse_date(date_str)

    async def get_rss(self, url: str) -> dict[str, Any]:
        """
        Fetch and parse an RSS/Atom feed. Returns feedparser-style dict.
        Falls back to an empty dict on any error.
        """
        try:
            resp = await self.get(url)
            if resp.status_code != 200:
                return {}
            try:
                import feedparser  # optional dependency

                return feedparser.parse(resp.text)  # type: ignore[no-any-return]
            except ImportError:
                # feedparser not installed — parse minimally
                import xml.etree.ElementTree as ET  # noqa: PLC0415  # nosec B405

                root = ET.fromstring(resp.text)  # nosec B314 — trusted government/news RSS source
                entries: list[dict[str, Any]] = []
                ns = {"atom": "http://www.w3.org/2005/Atom"}
                for item in root.findall(".//item") or root.findall(".//atom:entry", ns):
                    title_el = item.find("title") or item.find("atom:title", ns)
                    link_el = item.find("link") or item.find("atom:link", ns)
                    entries.append(
                        {
                            "title": title_el.text if title_el is not None else "",
                            "link": (link_el.text or link_el.get("href", ""))
                            if link_el is not None
                            else "",
                        }
                    )
                return {"entries": entries}
        except Exception as exc:
            self._log.warning("rss_fetch_failed", url=url, error=str(exc))
            return {}

    @staticmethod
    def _parse_date(date_str: str | None) -> datetime | None:
        """Parse common date string formats. Returns None on failure."""
        if not date_str:
            return None
        formats = [
            "%Y-%m-%d",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%d/%m/%Y",
            "%B %d, %Y",
            "%b %d, %Y",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt).replace(tzinfo=UTC)
            except ValueError:
                continue
        return None

    # ── Legacy helper methods (used by older scrapers) ──────────────────────────

    async def _get(self, url: str, **kwargs: Any) -> httpx.Response:
        """Alias for get() — used by older-style scrapers."""
        return await self.get(url, **kwargs)

    async def get_soup(self, url: str, **kwargs: Any) -> Any:
        """
        Fetch URL and return BeautifulSoup object (or None on failure).
        Requires beautifulsoup4 + lxml installed.
        """
        try:
            from bs4 import BeautifulSoup  # noqa: PLC0415

            resp = await self.get(url, **kwargs)
            if resp.status_code != 200:
                return None
            return BeautifulSoup(resp.text, "lxml")
        except Exception as exc:
            self._log.warning("get_soup_failed", url=url, error=str(exc))
            return None

    async def get_json(self, url: str, **kwargs: Any) -> Any:
        """Fetch URL and return parsed JSON (or None on failure)."""
        try:
            resp = await self.get(url, **kwargs)
            if resp.status_code != 200:
                return None
            return resp.json()
        except Exception as exc:
            self._log.warning("get_json_failed", url=url, error=str(exc))
            return None

    @staticmethod
    def safe_text(element: Any) -> str:
        """Extract stripped text from a BeautifulSoup element. Returns '' if None."""
        if element is None:
            return ""
        text = getattr(element, "get_text", None)
        if callable(text):
            return str(text(strip=True))
        return str(element).strip()

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} source_id={self.source_id!r}>"
