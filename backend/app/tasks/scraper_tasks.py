"""
app/tasks/scraper_tasks.py — Phase 1 Celery scraper task implementations.

Architecture:
  - One Celery task per scraper category (not per scraper)
  - Each category task fans out to individual scrapers
  - Results persisted via storage.persist_signals()
  - Health updated via ScraperHealth model
  - All tasks route to the 'scrapers' queue

Task naming: run_{category}_scrapers

Beat schedule (defined in celery_app.py):
  corporate    every 6 hours
  legal        every 12 hours
  regulatory   every 6 hours
  jobs         every 4 hours
  market       every 1 hour
  news         every 30 minutes
  social       every 30 minutes
  geo          every 24 hours
  law_blogs    every 6 hours
"""

from __future__ import annotations

import asyncio
import time
from datetime import UTC
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
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, coro)
                return future.result(timeout=300)
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


async def _run_category(category_prefix: str) -> dict[str, Any]:
    """
    Run all scrapers in a category and persist results.
    Returns summary dict with counts per scraper.
    """
    scrapers = ScraperRegistry.by_category(category_prefix)
    if not scrapers:
        log.warning("no_scrapers_for_category", category=category_prefix)
        return {"category": category_prefix, "scrapers": 0, "signals": 0}

    summary: dict[str, Any] = {
        "category": category_prefix,
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
                    "scraper_task_ok",
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
                    "scraper_task_error", source=scraper.source_id, error=str(exc), exc_info=True
                )

    return summary


# ── Corporate Scrapers ─────────────────────────────────────────────────────────
@celery_app.task(
    name="scrapers.run_corporate",
    queue="scrapers",
    max_retries=2,
    soft_time_limit=1200,
    time_limit=1500,
    bind=True,
)
def run_corporate_scrapers(self: Any) -> dict[str, Any]:
    """Run all corporate filing scrapers (SEDAR+, EDGAR, SEDI, etc.)."""
    log.info("task_start", task="run_corporate_scrapers")
    result: dict[str, Any] = _run_async(_run_category("corporate"))  # type: ignore[assignment]
    log.info("task_complete", task="run_corporate_scrapers", **result)
    return result


# ── Legal Scrapers ─────────────────────────────────────────────────────────────
@celery_app.task(
    name="scrapers.run_legal",
    queue="scrapers",
    max_retries=2,
    soft_time_limit=1800,
    time_limit=2100,
    bind=True,
)
def run_legal_scrapers(self: Any) -> dict[str, Any]:
    """Run all legal/court scrapers (CanLII, OSB, SCC, Competition Tribunal, etc.)."""
    log.info("task_start", task="run_legal_scrapers")
    result: dict[str, Any] = _run_async(_run_category("legal"))  # type: ignore[assignment]
    log.info("task_complete", task="run_legal_scrapers", **result)
    return result


# ── Regulatory Scrapers ────────────────────────────────────────────────────────
@celery_app.task(
    name="scrapers.run_regulatory",
    queue="scrapers",
    max_retries=2,
    soft_time_limit=1200,
    time_limit=1500,
    bind=True,
)
def run_regulatory_scrapers(self: Any) -> dict[str, Any]:
    """Run all regulatory scrapers (OSC, FINTRAC, OPC, OSFI, etc.)."""
    log.info("task_start", task="run_regulatory_scrapers")
    result: dict[str, Any] = _run_async(_run_category("regulatory"))  # type: ignore[assignment]
    log.info("task_complete", task="run_regulatory_scrapers", **result)
    return result


# ── Jobs Scrapers ──────────────────────────────────────────────────────────────
@celery_app.task(
    name="scrapers.run_jobs",
    queue="scrapers",
    max_retries=2,
    soft_time_limit=900,
    time_limit=1200,
    bind=True,
)
def run_jobs_scrapers(self: Any) -> dict[str, Any]:
    """Run all job posting scrapers (Indeed, Job Bank, LinkedIn, etc.)."""
    log.info("task_start", task="run_jobs_scrapers")
    result: dict[str, Any] = _run_async(_run_category("jobs"))  # type: ignore[assignment]
    log.info("task_complete", task="run_jobs_scrapers", **result)
    return result


# ── Market Scrapers ────────────────────────────────────────────────────────────
@celery_app.task(
    name="scrapers.run_market",
    queue="scrapers",
    max_retries=3,
    soft_time_limit=600,
    time_limit=900,
    bind=True,
)
def run_market_scrapers(self: Any) -> dict[str, Any]:
    """Run all market data scrapers (Alpha Vantage, Yahoo Finance, TMX, etc.)."""
    log.info("task_start", task="run_market_scrapers")
    result: dict[str, Any] = _run_async(_run_category("market"))  # type: ignore[assignment]
    log.info("task_complete", task="run_market_scrapers", **result)
    return result


# ── News Scrapers ──────────────────────────────────────────────────────────────
@celery_app.task(
    name="scrapers.run_news",
    queue="scrapers",
    max_retries=2,
    soft_time_limit=600,
    time_limit=900,
    bind=True,
)
def run_news_scrapers(self: Any) -> dict[str, Any]:
    """Run all news scrapers (Globe, FP, BNN, CBC, Reuters, etc.)."""
    log.info("task_start", task="run_news_scrapers")
    result: dict[str, Any] = _run_async(_run_category("news"))  # type: ignore[assignment]
    log.info("task_complete", task="run_news_scrapers", **result)
    return result


# ── Social Scrapers ────────────────────────────────────────────────────────────
@celery_app.task(
    name="scrapers.run_social",
    queue="scrapers",
    max_retries=2,
    soft_time_limit=600,
    time_limit=900,
    bind=True,
)
def run_social_scrapers(self: Any) -> dict[str, Any]:
    """Run all social scrapers (Reddit, Twitter, Stockhouse, HIBP, etc.)."""
    log.info("task_start", task="run_social_scrapers")
    result: dict[str, Any] = _run_async(_run_category("social"))  # type: ignore[assignment]
    log.info("task_complete", task="run_social_scrapers", **result)
    return result


# ── Geo Scrapers ───────────────────────────────────────────────────────────────
@celery_app.task(
    name="scrapers.run_geo",
    queue="scrapers",
    max_retries=2,
    soft_time_limit=900,
    time_limit=1200,
    bind=True,
)
def run_geo_scrapers(self: Any) -> dict[str, Any]:
    """Run all geographic/macro scrapers (Google Trends, StatsCan, CIPO, etc.)."""
    log.info("task_start", task="run_geo_scrapers")
    result: dict[str, Any] = _run_async(_run_category("geo"))  # type: ignore[assignment]
    log.info("task_complete", task="run_geo_scrapers", **result)
    return result


# ── Law Blog Scrapers ──────────────────────────────────────────────────────────
@celery_app.task(
    name="scrapers.run_law_blogs",
    queue="scrapers",
    max_retries=2,
    soft_time_limit=1800,
    time_limit=2100,
    bind=True,
)
def run_law_blog_scrapers(self: Any) -> dict[str, Any]:
    """Run all 27 law firm blog scrapers + trend detector."""
    log.info("task_start", task="run_law_blog_scrapers")
    result: dict[str, Any] = _run_async(_run_category("lawblog"))  # type: ignore[assignment]
    log.info("task_complete", task="run_law_blog_scrapers", **result)
    return result


# ── Health Check ───────────────────────────────────────────────────────────────
@celery_app.task(
    name="scrapers.health_check_all",
    queue="default",
    max_retries=1,
    soft_time_limit=300,
    time_limit=360,
)
def health_check_all_scrapers() -> dict[str, Any]:
    """Run health checks on all registered scrapers and update ScraperHealth table."""

    async def _check_all() -> dict[str, Any]:
        scrapers = ScraperRegistry.all_scrapers()
        healthy = 0
        unhealthy = 0
        results = []
        async with AsyncSessionLocal():
            for scraper in scrapers:
                try:
                    is_healthy = await asyncio.wait_for(scraper.health_check(), timeout=15.0)
                    if is_healthy:
                        healthy += 1
                    else:
                        unhealthy += 1
                    results.append(
                        {
                            "source_id": scraper.source_id,
                            "healthy": is_healthy,
                        }
                    )
                except Exception as exc:
                    unhealthy += 1
                    results.append(
                        {
                            "source_id": scraper.source_id,
                            "healthy": False,
                            "error": str(exc)[:100],
                        }
                    )
                finally:
                    await scraper.close()
        return {
            "total": len(scrapers),
            "healthy": healthy,
            "unhealthy": unhealthy,
            "details": results,
        }

    return _run_async(_check_all())  # type: ignore[no-any-return]


# ── Single scraper trigger (on-demand) ────────────────────────────────────────
@celery_app.task(
    name="scrapers.run_single",
    queue="scrapers",
    max_retries=2,
    soft_time_limit=600,
    time_limit=900,
)
def run_single_scraper(source_id: str) -> dict[str, Any]:
    """Run a single scraper by source_id. Used for on-demand scraping."""

    async def _run() -> dict[str, Any]:
        scraper = ScraperRegistry.get(source_id)
        async with AsyncSessionLocal() as db:
            motor = get_motor_client()
            mongo_db = motor["oracle_signals"] if motor else None
            results = await scraper.run()
            saved = await persist_signals(results, db, mongo_db)
        await scraper.close()
        return {"source_id": source_id, "scraped": len(results), "saved": saved}

    return _run_async(_run())  # type: ignore[no-any-return]


# ── Canary System ─────────────────────────────────────────────────────────────


@celery_app.task(
    name="scrapers.canary_check",
    queue="default",
    max_retries=1,
    soft_time_limit=120,
    time_limit=150,
)
def run_canary_check() -> dict[str, Any]:
    """
    Synthetic end-to-end pipeline verification (Agent 008 — Canary).

    Creates a synthetic ScraperResult, validates it with quality_validator,
    and attempts to persist it. If any step fails, logs a CRITICAL alert.

    Scheduled every 30 minutes via RedBeat.
    """

    async def _canary() -> dict[str, Any]:
        from datetime import datetime  # noqa: PLC0415

        from app.scrapers.base import ScraperResult  # noqa: PLC0415
        from app.scrapers.quality_validator import validate_signal  # noqa: PLC0415

        canary = ScraperResult(
            source_id="canary",
            signal_type="canary_heartbeat",
            signal_text=f"CANARY-{datetime.now(tz=UTC).isoformat()}",
            confidence_score=1.0,
            practice_area_hints=["litigation"],
            signal_value={"canary": True, "ts": datetime.now(tz=UTC).isoformat()},
            is_negative_label=False,
        )

        # Step 1: Validate synthetic signal
        vr = validate_signal(canary)
        if not vr.valid:
            log.critical("canary_validation_failed", errors=vr.errors)
            return {"status": "FAIL", "stage": "validation", "errors": vr.errors}

        # Step 2: Persist (dedup means it may not save every time — that's OK)
        async with AsyncSessionLocal() as db:
            motor = get_motor_client()
            mongo_db = motor["oracle_signals"] if motor else None
            saved = await persist_signals([canary], db, mongo_db)

        log.info("canary_ok", saved=saved, validated=True)
        return {"status": "OK", "saved": saved, "validated": True}

    return _run_async(_canary())  # type: ignore[no-any-return]
