"""
app/scrapers/storage.py — Signal persistence layer.

Persists ScraperResult objects to:
  - PostgreSQL (signal_records table): structured fields
  - MongoDB (oracle_signals.raw_signals): raw_payload for NLP/analytics

Deduplication: source_id + source_url + DATE(scraped_at)
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import structlog

from app.scrapers.base import ScraperResult

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

log = structlog.get_logger(__name__)


async def persist_signals(
    results: list[ScraperResult],
    db: AsyncSession,
    mongo_db: Any | None = None,
) -> int:
    """
    Persist scraped signals to PostgreSQL signal_records + MongoDB.

    Returns:
        Number of newly saved records (0 if all duplicates or results empty)
    """
    if not results:
        return 0

    try:
        from app.models.company import SignalRecord  # noqa: PLC0415
    except ImportError:
        log.error("storage: cannot import SignalRecord — signal_records table unavailable")
        return 0

    from sqlalchemy import text  # noqa: PLC0415

    saved = 0

    for result in results:
        try:
            dedup = await db.execute(
                text("""
                    SELECT id FROM signal_records
                    WHERE source_id = :source_id
                      AND COALESCE(source_url, '') = COALESCE(:source_url, '')
                      AND DATE(scraped_at) = CURRENT_DATE
                    LIMIT 1
                """),
                {
                    "source_id": result.source_id,
                    "source_url": result.source_url or "",
                },
            )
            if dedup.scalar_one_or_none() is not None:
                continue

            signal_value_str: str | None = None
            if result.signal_value:
                try:
                    signal_value_str = json.dumps(result.signal_value)
                except (TypeError, ValueError):
                    signal_value_str = str(result.signal_value)

            practice_hints_str: str | None = None
            if result.practice_area_hints:
                try:
                    practice_hints_str = json.dumps(result.practice_area_hints)
                except (TypeError, ValueError):
                    practice_hints_str = str(result.practice_area_hints)

            record = SignalRecord(
                source_id=result.source_id,
                source_url=result.source_url,
                signal_type=result.signal_type,
                raw_company_name=result.raw_company_name,
                raw_company_id=result.raw_company_id,
                signal_value=signal_value_str,
                signal_text=result.signal_text,
                confidence_score=result.confidence_score,
                published_at=result.published_at,
                is_negative_label=result.is_negative_label,
                practice_area_hints=practice_hints_str,
                is_resolved=False,
                is_processed=False,
                company_id=None,
            )
            db.add(record)
            await db.flush()

            if mongo_db is not None and result.raw_payload:
                try:
                    raw_doc = {
                        "source_id": result.source_id,
                        "signal_type": result.signal_type,
                        "raw_company_name": result.raw_company_name,
                        "source_url": result.source_url,
                        "published_at": result.published_at,
                        "scraped_at": datetime.now(tz=UTC),
                        "raw_payload": result.raw_payload,
                        "practice_area_hints": result.practice_area_hints,
                    }
                    await mongo_db["raw_signals"].insert_one(raw_doc)
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

    if saved > 0:
        try:
            await db.commit()
        except Exception as commit_exc:
            log.error("signal_commit_failed", error=str(commit_exc))
            await db.rollback()
            return 0

    return saved
