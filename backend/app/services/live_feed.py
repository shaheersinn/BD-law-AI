"""
app/services/live_feed.py — Priority Signal Router via Redis Streams.

Phase 5: Live Feeds — priority signals delivered in < 60 seconds.

Architecture:
  - Stream key:    oracle:live:signals
  - Consumer group: scoring_consumers
  - Consumer name: oracle-worker-{hostname}
  - Max stream length: ~86,400 events (24-hour rolling retention, approximate)

Any live scraper pushes events here instead of waiting for the next Celery batch.
The scoring consumer (Agent 020) reads events and triggers priority re-scoring.

Usage (publisher — inside a live scraper task):
    from app.services.live_feed import live_feed
    await live_feed.push_signal({
        "scraper_name": "sedar_live",
        "signal_type": "material_change",
        "company_id": "123",
        "source_url": "https://...",
        "published_at": "2026-03-24T10:00:00Z",
    })

Usage (consumer — Agent 020 process_live_feed_events task):
    await live_feed.ensure_consumer_group()
    messages = await live_feed.read_events(batch_size=50, block_ms=1000)
    for msg_id, data in messages:
        await process(data)
        await live_feed.acknowledge(msg_id)
"""

from __future__ import annotations

import json
import socket
from datetime import UTC, datetime
from typing import Any

import structlog
import redis.asyncio as aioredis
from redis.asyncio import Redis

from app.config import get_settings

log = structlog.get_logger(__name__)
settings = get_settings()

# ── Stream constants ───────────────────────────────────────────────────────────
STREAM_KEY = "oracle:live:signals"
CONSUMER_GROUP = "scoring_consumers"
CONSUMER_NAME = f"oracle-worker-{socket.gethostname()}"
STREAM_MAXLEN = 86_400  # ~24 hours of events at 1 event/second (approximate trim)


class LiveFeedRouter:
    """
    Redis Streams wrapper for the ORACLE priority signal bus.

    All high-priority live scrapers push signals here.
    The scoring consumer (Agent 020) reads and triggers re-scoring.

    Thread-safety: not thread-safe — use one instance per async context.
    Singleton pattern: import the module-level `live_feed` instance.
    """

    def __init__(self) -> None:
        self._client: Redis | None = None  # type: ignore[type-arg]

    def _get_client(self) -> Redis:  # type: ignore[type-arg]
        if self._client is None:
            self._client = aioredis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=10,
                socket_timeout=5,
                socket_connect_timeout=5,
            )
        return self._client

    async def push_signal(self, signal: dict[str, Any]) -> str | None:
        """
        Push a priority signal onto the Redis Stream.

        Fails silently (returns None) when live_feeds_enabled=False or on Redis error.
        This allows callers to push without checking the feature flag themselves.

        Args:
            signal: Flat dict. Values that are dicts/lists are JSON-serialized.
                    Recommended fields: scraper_name, signal_type, company_id,
                    source_url, published_at, practice_area.

        Returns:
            Message ID string (e.g. "1711234567890-0") on success, None otherwise.
        """
        if not settings.live_feeds_enabled:
            return None

        try:
            client = self._get_client()

            # Stamp with push time if caller did not provide it
            if "pushed_at" not in signal:
                signal = {**signal, "pushed_at": datetime.now(UTC).isoformat()}

            # Redis Streams require flat string field values
            fields: dict[str, str] = {}
            for k, v in signal.items():
                if isinstance(v, (dict, list)):
                    fields[k] = json.dumps(v)
                elif v is None:
                    fields[k] = ""
                else:
                    fields[k] = str(v)

            msg_id: str = await client.xadd(  # type: ignore[assignment]
                STREAM_KEY,
                fields,
                maxlen=STREAM_MAXLEN,
                approximate=True,
            )
            log.debug(
                "live_feed_pushed",
                msg_id=msg_id,
                signal_type=signal.get("signal_type"),
                company_id=signal.get("company_id"),
            )
            return msg_id

        except Exception as exc:
            log.warning("live_feed_push_failed", error=str(exc))
            return None

    async def ensure_consumer_group(self) -> None:
        """
        Create the consumer group idempotently.

        Uses mkstream=True so the stream is created if it does not exist yet.
        Silently ignores BUSYGROUP error (group already exists — normal on restart).
        """
        if not settings.live_feeds_enabled:
            return

        try:
            client = self._get_client()
            try:
                await client.xgroup_create(  # type: ignore[misc]
                    STREAM_KEY,
                    CONSUMER_GROUP,
                    id="0",
                    mkstream=True,
                )
                log.info("live_feed_consumer_group_created", group=CONSUMER_GROUP)
            except aioredis.ResponseError as exc:
                if "BUSYGROUP" in str(exc):
                    pass  # Group already exists — expected on worker restart
                else:
                    raise

        except Exception as exc:
            log.error("live_feed_group_create_failed", error=str(exc))

    async def read_events(
        self,
        batch_size: int = 50,
        block_ms: int = 1000,
        consumer_name: str | None = None,
    ) -> list[tuple[str, dict[str, Any]]]:
        """
        Read up to batch_size unprocessed events from the consumer group.

        Uses ">" as message ID to read only newly-delivered (not pending) messages.
        Blocks for block_ms milliseconds if no events are available.

        Args:
            batch_size: Max messages to read in one call.
            block_ms:   Milliseconds to block waiting for new messages.
            consumer_name: Override default consumer name (used in tests).

        Returns:
            List of (msg_id, data_dict) tuples. Empty list if no messages or on error.
        """
        if not settings.live_feeds_enabled:
            return []

        try:
            client = self._get_client()
            cname = consumer_name or CONSUMER_NAME

            response = await client.xreadgroup(  # type: ignore[misc]
                CONSUMER_GROUP,
                cname,
                {STREAM_KEY: ">"},
                count=batch_size,
                block=block_ms,
            )

            if not response:
                return []

            results: list[tuple[str, dict[str, Any]]] = []
            for _stream_key, messages in response:
                for msg_id, raw_data in messages:
                    # Attempt to deserialize JSON-encoded values back to native types
                    parsed: dict[str, Any] = {}
                    for k, v in raw_data.items():
                        try:
                            parsed[k] = json.loads(v)
                        except (json.JSONDecodeError, TypeError, ValueError):
                            parsed[k] = v
                    results.append((msg_id, parsed))

            return results

        except Exception as exc:
            log.warning("live_feed_read_failed", error=str(exc))
            return []

    async def acknowledge(self, msg_id: str) -> bool:
        """
        Acknowledge a processed message, removing it from the Pending Entry List.

        Must be called after successfully processing each event to prevent
        redelivery on next worker restart.

        Returns:
            True if acknowledged, False on error or feature disabled.
        """
        if not settings.live_feeds_enabled:
            return False

        try:
            client = self._get_client()
            result: int = await client.xack(STREAM_KEY, CONSUMER_GROUP, msg_id)  # type: ignore[assignment]
            return result > 0
        except Exception as exc:
            log.warning("live_feed_ack_failed", msg_id=msg_id, error=str(exc))
            return False

    async def stream_length(self) -> int:
        """Return the current number of entries in the stream (0 on error)."""
        try:
            client = self._get_client()
            length: int = await client.xlen(STREAM_KEY)  # type: ignore[assignment]
            return length
        except Exception as exc:
            log.warning("live_feed_xlen_failed", error=str(exc))
            return 0

    async def pending_count(self) -> int:
        """
        Return the number of delivered-but-unacknowledged messages in the group.

        Useful for monitoring lag in the scoring consumer.
        """
        try:
            client = self._get_client()
            info = await client.xpending(STREAM_KEY, CONSUMER_GROUP)  # type: ignore[misc]
            # xpending returns: [count, min_id, max_id, consumers] or a dict
            if isinstance(info, (list, tuple)) and info:
                return int(info[0])
            if isinstance(info, dict):
                return int(info.get("pending", 0))
            return 0
        except Exception as exc:
            log.warning("live_feed_pending_failed", error=str(exc))
            return 0

    async def close(self) -> None:
        """Close the Redis connection. Call on application shutdown."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None


# ── Module-level singleton ─────────────────────────────────────────────────────
# Import this in other modules:
#   from app.services.live_feed import live_feed
live_feed = LiveFeedRouter()
