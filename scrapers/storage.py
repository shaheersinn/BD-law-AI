"""
app/scrapers/storage.py — Signal persistence layer.

Saves ScraperResult objects to:
  - PostgreSQL (signal_records table — structured metadata)
  - MongoDB (raw_signals collection — full payload + text)

Called by Celery tasks after scraper.run() returns.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from typing import Any
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from app.scrapers.base import ScraperResult
from app.scrapers.entity_resolver import EntityResolver
from app.models.company import SignalRecord

log = structlog.get_logger(__name__)


async def persist_signals(
    results: list[ScraperResult],
    db: AsyncSession,
    mongo_db: Any,
    redis_client: Any = None,
) -> int:
    """
    Persist scraped signals to PostgreSQL + MongoDB.

    Returns count of records saved.
    """
    if not results:
        return 0

    resolver = EntityResolver(db, redis_client)
    saved = 0

    for result in results:
        try:
            # ── Resolve company ──────────────────────────────────────────────
            company_id, confidence = await resolver.resolve(
                name=result.raw_company_name,
            )

            # ── Save to MongoDB (raw payload) ────────────────────────────────
            mongo_doc_id: str | None = None
            if mongo_db is not None:
                try:
                    mongo_doc = {
                        "source_id": result.source_id,
                        "signal_type": result.signal_type,
                        "raw_company_name": result.raw_company_name,
                        "raw_company_id": result.raw_company_id,
                        "source_url": result.source_url,
                        "signal_value": result.signal_value,
                        "signal_text": result.signal_text,
                        "raw_payload": result.raw_payload,
                        "practice_area_hints": result.practice_area_hints,
                        "company_id": company_id,
                        "confidence_score": confidence,
                        "scraped_at": datetime.now(tz=timezone.utc),
                        "published_at": result.published_at,
                    }
                    mongo_result = await mongo_db.raw_signals.insert_one(mongo_doc)
                    mongo_doc_id = str(mongo_result.inserted_id)
                except Exception as mongo_exc:
                    log.error("mongo_insert_failed", error=str(mongo_exc), source=result.source_id)

            # ── Save to PostgreSQL (structured metadata) ─────────────────────
            signal = SignalRecord(
                company_id=company_id,
                source_id=result.source_id,
                source_url=result.source_url,
                signal_type=result.signal_type,
                raw_company_name=result.raw_company_name,
                raw_company_id=result.raw_company_id,
                signal_value=json.dumps(result.signal_value) if result.signal_value else None,
                signal_text=result.signal_text,
                mongo_doc_id=mongo_doc_id,
                confidence_score=min(confidence, result.confidence_score),
                is_resolved=company_id is not None,
                is_processed=False,
                is_negative_label=result.is_negative_label,
                published_at=result.published_at,
                practice_area_hints=json.dumps(result.practice_area_hints) if result.practice_area_hints else None,
            )
            db.add(signal)
            saved += 1

        except Exception as exc:
            log.error("signal_persist_failed", source=result.source_id, error=str(exc), exc_info=True)
            continue

    try:
        await db.commit()
    except Exception as commit_exc:
        await db.rollback()
        log.error("signal_commit_failed", error=str(commit_exc), exc_info=True)
        return 0

    log.info("signals_persisted", saved=saved, total=len(results))
    return saved
