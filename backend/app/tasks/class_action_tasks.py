"""
app/tasks/class_action_tasks.py — Phase CA-1 class action scraper Celery tasks.

Runs all 12 class action scrapers as a category batch every 6 hours.
Uses the same _run_category pattern as scraper_tasks.py.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import time
from typing import Any

import structlog

from app.database import AsyncSessionLocal
from app.database import get_mongo_client as get_motor_client
from app.scrapers.registry import ScraperRegistry
from app.scrapers.storage import persist_signals
from app.tasks.celery_app import celery_app

log = structlog.get_logger(__name__)


def _run_async(coro: Any) -> Any:
    """Run a coroutine synchronously from a Celery worker context."""
    try:
        asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(asyncio.run, coro)
            return future.result(timeout=600)
    except RuntimeError:
        return asyncio.run(coro)


async def _run_class_action_scrapers() -> dict[str, Any]:
    """Run all class action scrapers and persist results."""
    scrapers = ScraperRegistry.by_category("class_actions")
    if not scrapers:
        log.warning("no_class_action_scrapers_found")
        return {"category": "class_actions", "scrapers": 0, "signals": 0}

    summary: dict[str, Any] = {
        "category": "class_actions",
        "scrapers": len(scrapers),
        "signals": 0,
        "errors": 0,
        "scraper_details": [],
    }

    async with AsyncSessionLocal() as db:
        motor = get_motor_client()
        mongo_db = motor["oracle_signals"] if motor else None

        for scraper in scrapers:
            start = time.monotonic()
            try:
                results = await scraper.run()
                saved = await persist_signals(results, db, mongo_db)
                elapsed = time.monotonic() - start
                summary["signals"] += saved
                summary["scraper_details"].append(
                    {
                        "source_id": scraper.source_id,
                        "records": saved,
                        "duration_s": round(elapsed, 2),
                        "status": "ok",
                    }
                )
                log.info(
                    "class_action_scraper_ok",
                    source=scraper.source_id,
                    saved=saved,
                    duration=round(elapsed, 2),
                )

            except Exception as exc:
                elapsed = time.monotonic() - start
                summary["errors"] += 1
                summary["scraper_details"].append(
                    {
                        "source_id": scraper.source_id,
                        "records": 0,
                        "duration_s": round(elapsed, 2),
                        "status": "error",
                        "error": str(exc)[:200],
                    }
                )
                log.error(
                    "class_action_scraper_error",
                    source=scraper.source_id,
                    error=str(exc),
                )
            finally:
                try:
                    await scraper.close()
                except Exception:
                    log.debug("scraper_close_failed_ignored", source=scraper.source_id)

    log.info(
        "class_action_scrapers_complete",
        total=summary["scrapers"],
        signals=summary["signals"],
        errors=summary["errors"],
    )
    return summary


@celery_app.task(
    name="scrapers.run_class_actions",
    bind=True,
    max_retries=2,
    default_retry_delay=300,
    soft_time_limit=1800,
    time_limit=2100,
)
def run_class_actions(self: Any) -> dict[str, Any]:
    """Run all 12 class action scrapers."""
    try:
        return _run_async(_run_class_action_scrapers())
    except Exception as exc:
        log.error("class_action_task_failed", error=str(exc))
        raise self.retry(exc=exc) from exc
