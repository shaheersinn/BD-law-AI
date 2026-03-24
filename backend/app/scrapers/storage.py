"""
app/scrapers/storage.py — Signal persistence layer.

Persists ScraperResult objects to:
  - PostgreSQL (Signal model): structured fields for ML feature engineering
  - MongoDB (oracle_signals.raw_signals): raw_payload for NLP/analytics

Deduplication strategy:
  SHA256(source_id + source_url + published_at.date()) — prevents double-saves
  on re-runs within the same day.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import structlog

from app.scrapers.base import ScraperResult

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

log = structlog.get_logger(__name__)

# Fallback for environments where Signal model isn't available yet (early bootstrap)
_Signal: Any = None


def _get_signal_model() -> Any:
    global _Signal
    if _Signal is None:
        try:
            from app.models.signal import Signal  # noqa: PLC0415

            _Signal = Signal
        except ImportError:
            pass
    return _Signal


def _compute_content_hash(result: ScraperResult) -> str:
    """SHA256 dedup hash: source_id + source_url + date portion of published_at."""
    date_str = ""
    if result.published_at:
        date_str = result.published_at.date().isoformat()
    raw = f"{result.source_id}|{result.source_url or ''}|{date_str}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _practice_area_flags(hints: list[str]) -> int:
    """Convert practice_area_hints list → bitmask integer."""
    try:
        from app.models.signal import PRACTICE_AREA_BITS  # noqa: PLC0415
    except ImportError:
        return 0
    flags = 0
    for hint in hints:
        bit = PRACTICE_AREA_BITS.get(hint)
        if bit is not None:
            flags |= 1 << bit
    return flags


async def persist_signals(
    results: list[ScraperResult],
    db: AsyncSession,
    mongo_db: Any | None = None,
) -> int:
    """
    Persist scraped signals to PostgreSQL + MongoDB.

    Args:
        results:   list of ScraperResult from a scraper run
        db:        async SQLAlchemy session (PostgreSQL)
        mongo_db:  Motor AsyncIOMotorDatabase or None (MongoDB optional)

    Returns:
        Number of newly saved records (0 if all were duplicates or results was empty)
    """
    if not results:
        return 0

    Signal = _get_signal_model()
    saved = 0

    for result in results:
        try:
            content_hash = _compute_content_hash(result)

            # ── PostgreSQL persistence ─────────────────────────────────────────
            if Signal is not None:
                try:
                    from sqlalchemy import select  # noqa: PLC0415

                    existing = await db.execute(
                        select(Signal).where(Signal.content_hash == content_hash)
                    )
                    if existing.scalar_one_or_none() is not None:
                        continue  # duplicate

                    practice_flags = _practice_area_flags(result.practice_area_hints)
                    primary_area = (
                        result.practice_area_hints[0] if result.practice_area_hints else None
                    )

                    signal_obj = Signal(
                        scraper_name=result.source_id,
                        source_url=result.source_url,
                        signal_type=result.signal_type,
                        practice_area_flags=practice_flags,
                        primary_practice_area=primary_area,
                        title=None,
                        summary=result.signal_text,
                        raw_entity_name=result.raw_company_name,
                        content_hash=content_hash,
                        signal_strength=result.confidence_score,
                        source_reliability=0.8,
                        entity_resolved=False,
                        metadata=result.signal_value or None,
                        published_at=result.published_at,
                    )
                    db.add(signal_obj)
                    await db.flush()

                except Exception as pg_exc:
                    log.warning(
                        "signal_pg_save_failed",
                        source_id=result.source_id,
                        error=str(pg_exc),
                    )
                    continue

            # ── MongoDB persistence (raw_payload only) ─────────────────────────
            if mongo_db is not None and result.raw_payload:
                try:
                    raw_doc = {
                        "content_hash": content_hash,
                        "source_id": result.source_id,
                        "signal_type": result.signal_type,
                        "raw_company_name": result.raw_company_name,
                        "source_url": result.source_url,
                        "published_at": result.published_at,
                        "scraped_at": datetime.now(tz=UTC),
                        "raw_payload": result.raw_payload,
                        "practice_area_hints": result.practice_area_hints,
                    }
                    await mongo_db["raw_signals"].update_one(
                        {"content_hash": content_hash},
                        {"$setOnInsert": raw_doc},
                        upsert=True,
                    )
                except Exception as mongo_exc:
                    log.warning(
                        "signal_mongo_save_failed",
                        source_id=result.source_id,
                        error=str(mongo_exc),
                    )

            saved += 1

        except Exception as exc:
            log.error(
                "signal_persist_failed",
                source_id=result.source_id,
                error=str(exc),
                exc_info=True,
            )

    if Signal is not None:
        try:
            await db.commit()
        except Exception as commit_exc:
            log.error("signal_commit_failed", error=str(commit_exc))
            await db.rollback()
            return 0

    return saved
