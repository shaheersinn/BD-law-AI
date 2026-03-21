"""
app/scrapers/base.py — BaseScraper with retry, rate-limiting, and structured output.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import get_settings

log = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class RawSignal:
    """Normalised output from any scraper — maps to Trigger ORM model."""

    source: str
    trigger_type: str
    company_name: str
    title: str
    practice_area: str
    urgency: int               # 0-100
    filed_at: datetime
    description: str = ""
    url: str = ""
    base_weight: float = 0.75
    extra: dict = field(default_factory=dict)


class BaseScraper:
    """
    Base class for all scrapers.
    - Async httpx client with retry logic
    - Structured RawSignal output
    - Subclasses implement fetch_new()
    """

    source_name: str = "BASE"
    request_delay_seconds: float = 1.0   # polite crawling

    def __init__(self) -> None:
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=settings.scraper_timeout_seconds,
                headers={"User-Agent": settings.scraper_user_agent},
                follow_redirects=True,
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    @retry(
        retry=retry_if_exception_type(httpx.HTTPError),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def _get(self, url: str, **kwargs: Any) -> httpx.Response:
        await asyncio.sleep(self.request_delay_seconds)
        resp = await self.client.get(url, **kwargs)
        resp.raise_for_status()
        return resp

    async def fetch_new(self) -> list[RawSignal]:
        raise NotImplementedError

    async def __aenter__(self) -> "BaseScraper":
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()
