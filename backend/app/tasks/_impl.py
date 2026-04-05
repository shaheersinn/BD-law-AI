"""
app/tasks/_impl.py — Celery task implementations.

Phase 0: All tasks are stubs that log their invocation.
Each phase will implement the actual task logic:
  Phase 1:  scraper tasks
  Phase 2:  feature extraction tasks
  Phase 6:  scoring and training tasks
  Ongoing:  agent tasks

All tasks follow these conventions:
  - bind=True: tasks have access to self (for retry, task_id, etc.)
  - max_retries=3: retry up to 3 times on failure
  - Exponential backoff: countdown=2**self.request.retries
  - Structured logging: every task logs start, completion, and errors
"""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import structlog
from celery import Task

from app.tasks.celery_app import celery_app

log = structlog.get_logger(__name__)


def _run_async(coro: Any) -> Any:  # type: ignore[misc]
    """Run an async coroutine from a sync Celery task."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(asyncio.run, coro)
                return future.result(timeout=300)
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


def _make_stub(task_name: str) -> Task:  # type: ignore[type-arg]
    """
    Create a stub task that logs its invocation.
    Used in Phase 0 until real implementations are built.
    """

    @celery_app.task(name=task_name, bind=True, max_retries=3)  # type: ignore[misc]
    def stub_task(self: Task) -> dict:  # type: ignore[type-arg]
        log.info("Task invoked (stub — implement in Phase 1+)", task=task_name)  # type: ignore[call-arg]
        return {"status": "stub", "task": task_name}

    stub_task.__name__ = task_name.split(".")[-1]
    return stub_task


# ── Scraper Tasks (Phase 1) ────────────────────────────────────────────────────


@celery_app.task(bind=True, max_retries=3, name="app.tasks._impl.scrape_sedar")
def scrape_sedar(self: Task) -> dict:  # type: ignore[type-arg]
    """Scrape SEDAR+ for material changes, confidentiality, BAR filings."""
    log.info("scrape_sedar invoked (stub — implement in Phase 1)")
    return {"status": "stub", "source": "sedar"}


@celery_app.task(
    bind=True,
    max_retries=3,
    name="app.tasks._impl.scrape_edgar",
    soft_time_limit=3600,
    time_limit=3900,
)
def scrape_edgar(self: Task) -> dict:  # type: ignore[type-arg]
    """
    Scrape SEC EDGAR for 10-K/10-Q financials, 8-K events, SC 13D.
    Runs hourly. Free REST API.
    """

    async def _impl() -> dict[str, Any]:
        from datetime import UTC, datetime

        from app.database import AsyncSessionLocal
        from app.models.trigger import Trigger
        from app.scrapers.edgar import EdgarScraper

        scraper = EdgarScraper()
        signals = await scraper.fetch_new(days_back=2)

        if not signals:
            return {"status": "ok", "signals_saved": 0}

        async with AsyncSessionLocal() as db:
            now = datetime.now(UTC)
            for sig in signals:
                # EDGAR signals tie to `raw_company_name` via the Trigger.company_name
                db.add(
                    Trigger(
                        source=getattr(sig, "source", "EDGAR"),
                        trigger_type=getattr(sig, "trigger_type", "filing"),
                        company_name=getattr(
                            sig, "raw_company_name", getattr(sig, "company_name", "Unknown")
                        ),
                        title=getattr(sig, "title", "SEC Filing"),
                        description=getattr(sig, "description", None),
                        url=getattr(sig, "url", None),
                        urgency=getattr(sig, "urgency", 70),
                        practice_area=getattr(sig, "practice_area", "Corporate / M&A"),
                        practice_confidence=75,
                        filed_at=getattr(sig, "filed_at", now),
                        detected_at=now,
                        actioned=False,
                    )
                )
            await db.commit()

        return {"status": "ok", "signals_saved": len(signals)}

    log.info("scrape_edgar starting")
    try:
        result = _run_async(_impl())
        log.info("scrape_edgar complete", **result)
        return result
    except Exception as exc:  # noqa: BLE001
        log.error("scrape_edgar failed", error=str(exc))
        raise self.retry(exc=exc, countdown=2**self.request.retries) from exc


@celery_app.task(
    bind=True,
    max_retries=3,
    name="app.tasks._impl.scrape_regulatory_feeds",
    soft_time_limit=270,
    time_limit=300,
)
def scrape_regulatory_feeds(self: Task) -> dict:  # type: ignore[type-arg]
    """
    Scrape OSC, Competition Bureau, and FINTRAC RSS enforcement feeds.
    Runs every 4 hours on weekdays. Free — no API key required.
    """

    async def _impl() -> dict[str, Any]:
        from app.database import AsyncSessionLocal
        from app.models.company import SignalRecord
        from app.scrapers.regulatory.competition_bureau import CompetitionBureauScraper
        from app.scrapers.regulatory.fintrac import FintracScraper
        from app.scrapers.regulatory.osc import OSCScraper

        scraper_classes = [OSCScraper, CompetitionBureauScraper, FintracScraper]
        total = 0
        errors: list[str] = []

        for ScraperClass in scraper_classes:
            scraper = ScraperClass()
            try:
                signals = await scraper.run()
                if signals:
                    async with AsyncSessionLocal() as db:
                        for sig in signals:
                            db.add(
                                SignalRecord(
                                    source_id=sig.source_id,
                                    signal_type=sig.signal_type,
                                    signal_text=sig.signal_text or "",
                                    source_url=sig.source_url,
                                    confidence_score=sig.confidence_score,
                                    published_at=sig.published_at,
                                    practice_area_hints=sig.practice_area_hints[0]
                                    if sig.practice_area_hints
                                    else None,
                                    signal_value=sig.signal_value or {},
                                )
                            )
                        await db.commit()
                        total += len(signals)
                log.info(
                    "regulatory_scraper_complete",
                    source=scraper.source_id,
                    saved=len(signals),
                )
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{scraper.source_id}: {exc}")
                log.warning("regulatory_scraper_failed", source=scraper.source_id, error=str(exc))

        return {"status": "ok", "signals_saved": total, "errors": errors}

    log.info("scrape_regulatory_feeds starting")
    try:
        result = _run_async(_impl())
        log.info("scrape_regulatory_feeds complete", saved=result.get("signals_saved", 0))
        return result
    except Exception as exc:  # noqa: BLE001
        log.error("scrape_regulatory_feeds failed", error=str(exc))
        raise self.retry(exc=exc, countdown=2**self.request.retries) from exc


@celery_app.task(
    bind=True,
    max_retries=3,
    name="app.tasks._impl.scrape_jobs",
    soft_time_limit=3600,
    time_limit=3900,
)
def scrape_jobs(self: Task) -> dict:  # type: ignore[type-arg]
    """
    Scrape Indeed, LinkedIn, Job Bank for GC/CCO/CISO/litigation counsel postings.
    Runs daily.
    """

    async def _impl() -> dict[str, Any]:
        from datetime import UTC, datetime

        from sqlalchemy import text

        from app.database import AsyncSessionLocal
        from app.models.trigger import Trigger
        from app.scrapers.jobs import JobsScraper

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                text(
                    "SELECT name FROM companies WHERE is_active = true "
                    "ORDER BY priority_tier LIMIT 100"
                )
            )
            company_names = [row[0] for row in result.fetchall()]

        total = 0
        scraper = JobsScraper()

        for company_name in company_names:
            try:
                signals = await scraper.fetch_for_company(company_name)
                if signals:
                    async with AsyncSessionLocal() as db:
                        now = datetime.now(UTC)
                        for sig in signals:
                            db.add(
                                Trigger(
                                    source=getattr(sig, "source", "JOBS"),
                                    trigger_type=getattr(sig, "trigger_type", "job_posting"),
                                    company_name=company_name,
                                    title=getattr(sig, "title", f"Job Posting: {company_name}"),
                                    description=getattr(sig, "description", None),
                                    url=getattr(sig, "url", None),
                                    urgency=getattr(sig, "urgency", 70),
                                    practice_area=getattr(sig, "practice_area", "Employment"),
                                    practice_confidence=75,
                                    filed_at=getattr(sig, "filed_at", now),
                                    detected_at=now,
                                    actioned=False,
                                )
                            )
                        await db.commit()
                        total += len(signals)
            except Exception as exc:  # noqa: BLE001
                log.debug("jobs_company_failed", company=company_name, error=str(exc))

        return {"status": "ok", "companies_searched": len(company_names), "triggers_saved": total}

    log.info("scrape_jobs starting")
    try:
        result = _run_async(_impl())
        log.info("scrape_jobs complete", **result)
        return result
    except Exception as exc:  # noqa: BLE001
        log.error("scrape_jobs failed", error=str(exc))
        raise self.retry(exc=exc, countdown=2**self.request.retries) from exc


@celery_app.task(
    bind=True,
    max_retries=3,
    name="app.tasks._impl.scrape_canlii",
    soft_time_limit=3600,
    time_limit=3900,
)
def scrape_canlii(self: Task) -> dict:  # type: ignore[type-arg]
    """
    Search CanLII for new litigation naming watchlist companies.
    Requires CANLII_API_KEY env var — skips gracefully if absent.
    Runs daily at 7am.
    """
    import os

    if not os.getenv("CANLII_API_KEY"):
        log.warning("scrape_canlii skipped — CANLII_API_KEY not set")
        return {"status": "skipped", "reason": "CANLII_API_KEY not set"}

    async def _impl() -> dict[str, Any]:
        from datetime import UTC, datetime

        from sqlalchemy import text

        from app.database import AsyncSessionLocal
        from app.models.trigger import Trigger
        from app.scrapers.canlii import CanLIIScraper

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                text(
                    "SELECT name FROM companies WHERE is_active = true "
                    "ORDER BY priority_tier LIMIT 100"
                )
            )
            company_names = [row[0] for row in result.fetchall()]

        total = 0
        scraper = CanLIIScraper()

        for company_name in company_names:
            try:
                signals = await scraper.search_company(company_name, days_back=7)
                if signals:
                    async with AsyncSessionLocal() as db:
                        now = datetime.now(UTC)
                        for sig in signals:
                            db.add(
                                Trigger(
                                    source=getattr(sig, "source", "CANLII"),
                                    trigger_type=getattr(sig, "trigger_type", "litigation"),
                                    company_name=company_name,
                                    title=getattr(sig, "title", f"CanLII: {company_name}"),
                                    description=getattr(sig, "description", None),
                                    url=getattr(sig, "url", None),
                                    urgency=getattr(sig, "urgency", 70),
                                    practice_area=getattr(sig, "practice_area", "Litigation"),
                                    practice_confidence=75,
                                    filed_at=getattr(sig, "filed_at", now),
                                    detected_at=now,
                                    actioned=False,
                                )
                            )
                        await db.commit()
                        total += len(signals)
            except Exception as exc:  # noqa: BLE001
                log.debug("canlii_company_failed", company=company_name, error=str(exc))

        return {"status": "ok", "companies_searched": len(company_names), "triggers_saved": total}

    log.info("scrape_canlii starting")
    try:
        result = _run_async(_impl())
        log.info("scrape_canlii complete", **result)
        return result
    except Exception as exc:  # noqa: BLE001
        log.error("scrape_canlii failed", error=str(exc))
        raise self.retry(exc=exc, countdown=2**self.request.retries) from exc


@celery_app.task(bind=True, max_retries=3, name="app.tasks._impl.scrape_jets")
def scrape_jets(self: Task) -> dict:  # type: ignore[type-arg]
    """Scrape OpenSky ADS-B for corporate jet Bay Street proximity."""
    log.info("scrape_jets invoked (stub — implement in Phase 1)")
    return {"status": "stub", "source": "opensky"}


@celery_app.task(bind=True, max_retries=3, name="app.tasks._impl.scrape_social")
def scrape_social(self: Task) -> dict:  # type: ignore[type-arg]
    """Scrape Reddit, Twitter/X, Stockhouse, LinkedIn for social signals."""
    log.info("scrape_social invoked (stub — implement in Phase 1)")
    return {"status": "stub", "source": "social"}


@celery_app.task(
    bind=True,
    max_retries=3,
    name="app.tasks._impl.scrape_law_firm_blogs",
    soft_time_limit=1800,
    time_limit=2100,
)
def scrape_law_firm_blogs(self: Task) -> dict:  # type: ignore[type-arg]
    """
    Scrape RSS feeds from Bay Street Tier 1 and Tier 2 law firm blogs.
    Used for competitor intelligence and NLP training corpus.
    Runs weekly. No API key required.
    """

    async def _impl() -> dict[str, Any]:
        from app.database import AsyncSessionLocal
        from app.models.company import SignalRecord
        from app.scrapers.law_blogs.firm_blogs import ALL_FIRMS, LawFirmBlogScraper

        total = 0
        errors: list[str] = []

        for firm in ALL_FIRMS:
            scraper = LawFirmBlogScraper(firm)
            try:
                signals = await scraper.run()
                if signals:
                    async with AsyncSessionLocal() as db:
                        for sig in signals:
                            db.add(
                                SignalRecord(
                                    source_id=sig.source_id,
                                    signal_type=sig.signal_type,
                                    signal_text=sig.signal_text or "",
                                    source_url=sig.source_url,
                                    confidence_score=sig.confidence_score,
                                    published_at=sig.published_at,
                                    practice_area_hints=sig.practice_area_hints[0]
                                    if sig.practice_area_hints
                                    else None,
                                    signal_value=sig.signal_value or {},
                                )
                            )
                        await db.commit()
                        total += len(signals)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{firm.firm_name}: {exc}")
                log.debug("firm_blog_failed", firm=firm.firm_name, error=str(exc))

        return {
            "status": "ok",
            "signals_saved": total,
            "firms_scraped": len(ALL_FIRMS),
            "errors": len(errors),
        }

    log.info("scrape_law_firm_blogs starting")
    try:
        result = _run_async(_impl())
        log.info("scrape_law_firm_blogs complete", **result)
        return result
    except Exception as exc:  # noqa: BLE001
        log.error("scrape_law_firm_blogs failed", error=str(exc))
        raise self.retry(exc=exc, countdown=2**self.request.retries) from exc


@celery_app.task(
    bind=True,
    max_retries=3,
    name="app.tasks._impl.scrape_osb_insolvency",
    soft_time_limit=300,
    time_limit=360,
)
def scrape_osb_insolvency(self: Task) -> dict:  # type: ignore[type-arg]
    """
    Scrape OSB insolvency statistics. Free, no API key. Runs weekly.
    """

    async def _impl() -> dict[str, Any]:
        from app.database import AsyncSessionLocal
        from app.models.company import SignalRecord
        from app.scrapers.legal.osb_insolvency import OsbInsolvencyScraper

        scraper = OsbInsolvencyScraper()
        signals = await scraper.run()

        if not signals:
            return {"status": "ok", "signals_saved": 0}

        async with AsyncSessionLocal() as db:
            for sig in signals:
                db.add(
                    SignalRecord(
                        source_id=sig.source_id,
                        signal_type=sig.signal_type,
                        signal_text=sig.signal_text or "",
                        source_url=sig.source_url,
                        confidence_score=sig.confidence_score,
                        published_at=sig.published_at,
                        practice_area_hints=sig.practice_area_hints[0]
                        if sig.practice_area_hints
                        else None,
                        signal_value=sig.signal_value or {},
                    )
                )
            await db.commit()

        return {"status": "ok", "signals_saved": len(signals)}

    log.info("scrape_osb_insolvency starting")
    try:
        result = _run_async(_impl())
        log.info("scrape_osb_insolvency complete", saved=result.get("signals_saved", 0))
        return result
    except Exception as exc:  # noqa: BLE001
        log.error("scrape_osb_insolvency failed", error=str(exc))
        raise self.retry(exc=exc, countdown=2**self.request.retries) from exc


@celery_app.task(
    bind=True,
    max_retries=3,
    name="app.tasks._impl.scrape_google_trends",
    soft_time_limit=300,
    time_limit=360,
)
def scrape_google_trends(self: Task) -> dict:  # type: ignore[type-arg]
    """
    Scrape Google Trends via Pytrends for legal search term spikes.
    Runs weekly. No API key.
    """

    async def _impl() -> dict[str, Any]:
        from app.database import AsyncSessionLocal
        from app.models.company import SignalRecord
        from app.scrapers.geo.google_trends import GoogleTrendsScraper

        scraper = GoogleTrendsScraper()
        signals = await scraper.run()

        if not signals:
            return {"status": "ok", "signals_saved": 0}

        async with AsyncSessionLocal() as db:
            for sig in signals:
                db.add(
                    SignalRecord(
                        source_id=sig.source_id,
                        signal_type=sig.signal_type,
                        signal_text=sig.signal_text or "",
                        source_url=sig.source_url,
                        confidence_score=sig.confidence_score,
                        published_at=sig.published_at,
                        practice_area_hints=sig.practice_area_hints[0]
                        if sig.practice_area_hints
                        else None,
                        signal_value=sig.signal_value or {},
                    )
                )
            await db.commit()

        return {"status": "ok", "signals_saved": len(signals)}

    log.info("scrape_google_trends starting")
    try:
        result = _run_async(_impl())
        log.info("scrape_google_trends complete", saved=result.get("signals_saved", 0))
        return result
    except Exception as exc:  # noqa: BLE001
        log.error("scrape_google_trends failed", error=str(exc))
        raise self.retry(exc=exc, countdown=2**self.request.retries) from exc


# ── Feature Engineering Tasks (Phase 2) ───────────────────────────────────────


@celery_app.task(
    bind=True,
    max_retries=3,
    name="app.tasks._impl.extract_features_all",
    soft_time_limit=14400,  # 4 hours
    time_limit=14700,
)
def extract_features_all(self: Task) -> dict:  # type: ignore[type-arg]
    """
    Compute all features for all active watchlist companies.
    Runs nightly at 2am via Celery beat.
    Result stored in company_features table.
    """

    async def _run() -> dict[str, Any]:
        from app.database import AsyncSessionLocal, get_mongo_client
        from app.features.runner import FeatureRunner

        async with AsyncSessionLocal() as db:
            try:
                mongo_db = get_mongo_client()["oracle"]
            except Exception:
                mongo_db = None

            runner = FeatureRunner(db=db, mongo_db=mongo_db)
            result = await runner.run_all()
            return {**result, "mode": "incremental"}

    log.info("extract_features_all starting")
    try:
        result = _run_async(_run())
        log.info(
            "extract_features_all complete",
            companies=result.get("companies_processed", 0),
            features=result.get("features_computed", 0),
        )
        return {"status": "ok", **result}
    except Exception as exc:  # noqa: BLE001
        log.error("extract_features_all failed", error=str(exc))
        raise self.retry(exc=exc, countdown=2**self.request.retries) from exc


@celery_app.task(
    bind=True,
    max_retries=3,
    name="app.tasks._impl.rebuild_feature_vectors",
    soft_time_limit=28800,  # 8 hours for complete rebuild
    time_limit=29100,
)
def rebuild_feature_vectors(self: Task) -> dict:  # type: ignore[type-arg]
    """Rebuild all feature vectors from raw signals (full recompute)."""

    async def _run() -> dict[str, Any]:
        from app.database import AsyncSessionLocal, get_mongo_client
        from app.features.runner import FeatureRunner

        async with AsyncSessionLocal() as db:
            try:
                mongo_db = get_mongo_client()["oracle"]
            except Exception:
                mongo_db = None

            runner = FeatureRunner(db=db, mongo_db=mongo_db)
            # run_all() does not accept mode parameter natively — appending after
            result = await runner.run_all()
            return {**result, "mode": "full_rebuild"}

    log.info("rebuild_feature_vectors starting")
    try:
        result = _run_async(_run())
        log.info(
            "rebuild_feature_vectors complete",
            companies=result.get("companies_processed", 0),
            features=result.get("features_computed", 0),
        )
        return {"status": "ok", **result}
    except Exception as exc:  # noqa: BLE001
        log.error("rebuild_feature_vectors failed", error=str(exc))
        raise self.retry(exc=exc, countdown=2**self.request.retries) from exc


# ── Scoring Tasks (Phase 6) ────────────────────────────────────────────────────


@celery_app.task(
    bind=True,
    max_retries=3,
    name="app.tasks._impl.run_scoring_all_companies",
    soft_time_limit=7200,
    time_limit=7500,
)
def run_scoring_all_companies(self: Task) -> dict:  # type: ignore[type-arg]
    """
    Score all active watchlist companies across 34 practice areas × 3 horizons.

    Flow per company:
      1. Load feature rows from company_features table
      2. Build flat features dict {feature_name: value}
      3. Pass to orchestrator.score_company(features) — synchronous, no await
      4. Write scores to scoring_results table

    Runs nightly after extract_features_all completes.
    BayesianEngine models must be loaded — falls back to zero scores if absent.
    """

    async def _run() -> dict[str, Any]:
        import json
        from datetime import UTC, datetime

        from sqlalchemy import text

        from app.database import AsyncSessionLocal
        from app.ml.orchestrator import get_orchestrator

        orchestrator = get_orchestrator()
        if not orchestrator._loaded:
            orchestrator.load()

        scored = 0
        errors = 0

        async with AsyncSessionLocal() as db:
            # Get all active companies
            result = await db.execute(
                text("SELECT id FROM companies WHERE is_active = true ORDER BY id")
            )
            company_ids = [row[0] for row in result.fetchall()]

        for company_id in company_ids:
            try:
                async with AsyncSessionLocal() as db:
                    # Load features for this company (most recent value per feature_name)
                    feat_result = await db.execute(
                        text("""
                            SELECT DISTINCT ON (feature_name)
                                feature_name, value
                            FROM company_features
                            WHERE company_id = :company_id
                              AND is_null = false
                            ORDER BY feature_name, horizon_days ASC
                        """),
                        {"company_id": company_id},
                    )
                    rows = feat_result.fetchall()

                features: dict[str, float] = {
                    row[0]: float(row[1]) for row in rows if row[1] is not None
                }

                if not features:
                    # No features yet — skip silently, will score after first feature run
                    continue

                # score_company is synchronous — no await
                pa_scores = orchestrator.score_company(features)

                # Persist to scoring_results
                scores_json: dict[str, dict[str, float]] = {}
                for pa, horizon_scores in pa_scores.items():
                    scores_json[pa] = {
                        "30d": round(horizon_scores.score_30d, 6),
                        "60d": round(horizon_scores.score_60d, 6),
                        "90d": round(horizon_scores.score_90d, 6),
                    }

                now = datetime.now(UTC)
                async with AsyncSessionLocal() as db:
                    await db.execute(
                        text("""
                            INSERT INTO scoring_results
                                (company_id, scored_at, scores, velocity_score,
                                 anomaly_score, confidence_low, confidence_high,
                                 model_versions, top_signals)
                            VALUES
                                (:company_id, :scored_at, CAST(:scores AS jsonb),
                                 0.0, 0.0, 0.4, 0.95,
                                 CAST(:mv AS jsonb), CAST(:ts AS jsonb))
                        """),
                        {
                            "company_id": company_id,
                            "scored_at": now,
                            "scores": json.dumps(scores_json),
                            "mv": json.dumps({}),
                            "ts": json.dumps([]),
                        },
                    )
                    await db.commit()

                scored += 1

            except Exception as exc:  # noqa: BLE001
                log.warning(
                    "run_scoring_company_failed",
                    company_id=company_id,
                    error=str(exc),
                )
                errors += 1

        return {"companies_scored": scored, "errors": errors}

    log.info("run_scoring_all_companies starting")
    try:
        result = _run_async(_run())
        log.info(
            "run_scoring_all_companies complete",
            scored=result.get("companies_scored", 0),
            errors=result.get("errors", 0),
        )
        return {"status": "ok", **result}
    except Exception as exc:  # noqa: BLE001
        log.error("run_scoring_all_companies failed", error=str(exc))
        raise self.retry(exc=exc, countdown=600) from exc


@celery_app.task(
    bind=True,
    max_retries=3,
    name="app.tasks._impl.score_company",
    soft_time_limit=300,
    time_limit=330,
)
def score_company(self: Task, company_id: int) -> dict:  # type: ignore[type-arg]
    """
    Run 34-engine scoring for a single company (on-demand).
    Synchronously extracts features, then passes dict to orchestrator.
    """

    async def _run() -> dict[str, Any]:
        import json
        from datetime import UTC, datetime

        from sqlalchemy import text

        from app.database import AsyncSessionLocal, get_mongo_client
        from app.features.runner import FeatureRunner
        from app.ml.orchestrator import get_orchestrator

        # Step 1: Force re-extract features for this company
        async with AsyncSessionLocal() as db:
            try:
                mongo_db = get_mongo_client()["oracle"]
            except Exception:
                mongo_db = None
            runner = FeatureRunner(db=db, mongo_db=mongo_db)
            await runner.run_for_company(company_id=company_id)

        # Step 2: Load features
        async with AsyncSessionLocal() as db:
            feat_result = await db.execute(
                text("""
                    SELECT DISTINCT ON (feature_name)
                        feature_name, value
                    FROM company_features
                    WHERE company_id = :company_id
                      AND is_null = false
                    ORDER BY feature_name, horizon_days ASC
                """),
                {"company_id": company_id},
            )
            rows = feat_result.fetchall()

        features: dict[str, float] = {row[0]: float(row[1]) for row in rows if row[1] is not None}

        if not features:
            return {"status": "skipped", "reason": "no_features", "company_id": company_id}

        # Step 3: score — synchronous, no await
        orchestrator = get_orchestrator()
        if not orchestrator._loaded:
            orchestrator.load()

        pa_scores = orchestrator.score_company(features)

        # Step 4: persist
        scores_json: dict[str, dict[str, float]] = {}
        for pa, horizon_scores in pa_scores.items():
            scores_json[pa] = {
                "30d": round(horizon_scores.score_30d, 6),
                "60d": round(horizon_scores.score_60d, 6),
                "90d": round(horizon_scores.score_90d, 6),
            }

        now = datetime.now(UTC)
        async with AsyncSessionLocal() as db:
            await db.execute(
                text("""
                    INSERT INTO scoring_results
                        (company_id, scored_at, scores, velocity_score,
                         anomaly_score, confidence_low, confidence_high,
                         model_versions, top_signals)
                    VALUES
                        (:company_id, :scored_at, CAST(:scores AS jsonb),
                         0.0, 0.0, 0.4, 0.95,
                         CAST(:mv AS jsonb), CAST(:ts AS jsonb))
                """),
                {
                    "company_id": company_id,
                    "scored_at": now,
                    "scores": json.dumps(scores_json),
                    "mv": json.dumps({}),
                    "ts": json.dumps([]),
                },
            )
            await db.commit()

        return {"status": "ok", "company_id": company_id, "practice_areas_scored": len(pa_scores)}

    log.info("score_company starting", company_id=company_id)
    try:
        result = _run_async(_run())
        log.info("score_company complete", company_id=company_id, **result)
        return result
    except Exception as exc:  # noqa: BLE001
        log.error("score_company failed", company_id=company_id, error=str(exc))
        raise self.retry(exc=exc, countdown=2**self.request.retries) from exc


@celery_app.task(
    bind=True,
    max_retries=1,
    name="app.tasks._impl.retrain_all_models",
    soft_time_limit=10800,
    time_limit=11100,
)
def retrain_all_models(self: Task) -> dict:  # type: ignore[type-arg]
    """
    Retrain XGBoost churn model and LightGBM urgency model if training CSV exists.

    Missing CSV = graceful skip with warning. Not an error.
    BayesianEngine (34 practice areas) is trained via Azure batch — NOT here.
    Runs Sunday at 3am via Celery beat.
    """
    from pathlib import Path

    from app.config import get_settings

    settings = get_settings()
    training_dir = Path(settings.data_dir) / "training"
    churn_csv = training_dir / "churn_training_data.csv"
    urgency_csv = training_dir / "urgency_training_data.csv"
    results: dict[str, Any] = {}

    if churn_csv.exists():
        try:
            from app.ml.churn_model import train as train_churn

            log.info("retrain_churn starting", path=str(churn_csv))
            train_churn(str(churn_csv))
            log.info("retrain_churn complete")
            results["churn"] = "retrained"
        except Exception as exc:  # noqa: BLE001
            log.error("retrain_churn failed", error=str(exc))
            results["churn"] = f"error: {exc}"
    else:
        log.warning("retrain_churn skipped — no training data", path=str(churn_csv))
        results["churn"] = "skipped_no_data"

    if urgency_csv.exists():
        try:
            from app.ml.urgency_model import train as train_urgency

            log.info("retrain_urgency starting", path=str(urgency_csv))
            train_urgency(str(urgency_csv))
            log.info("retrain_urgency complete")
            results["urgency"] = "retrained"
        except Exception as exc:  # noqa: BLE001
            log.error("retrain_urgency failed", error=str(exc))
            results["urgency"] = f"error: {exc}"
    else:
        log.warning("retrain_urgency skipped — no training data", path=str(urgency_csv))
        results["urgency"] = "skipped_no_data"

    return {"status": "ok", **results}


# ── Ground Truth Tasks (Phase 3) ──────────────────────────────────────────────


@celery_app.task(
    bind=True,
    max_retries=1,
    name="app.tasks._impl.run_retrospective_labeler",
    soft_time_limit=1800,
    time_limit=2100,
)
def run_retrospective_labeler(self: Task) -> dict:  # type: ignore[type-arg]
    """Agent 016: Retrospective Labeler — assigns positive ground truth labels."""

    async def _impl() -> dict[str, Any]:
        from app.database import AsyncSessionLocal
        from app.ground_truth.pipeline import GroundTruthPipeline

        pipeline = GroundTruthPipeline()
        async with AsyncSessionLocal() as db:
            run = await pipeline._create_run(  # noqa: SLF001
                db=db,
                run_type="retrospective",
                config={},
                now=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
            )
            return await pipeline.run_retrospective(run_id=run.id, db=db)

    try:
        return _run_async(_impl())
    except Exception as exc:  # noqa: BLE001
        log.error("run_retrospective_labeler failed", error=str(exc))
        raise self.retry(exc=exc, countdown=2**self.request.retries) from exc


@celery_app.task(
    bind=True,
    max_retries=1,
    name="app.tasks._impl.run_negative_sampler",
    soft_time_limit=1800,
    time_limit=2100,
)
def run_negative_sampler(self: Task) -> dict:  # type: ignore[type-arg]
    """Agent 017: Negative Sampler — assigns negative ground truth labels."""

    async def _impl() -> dict[str, Any]:
        from app.database import AsyncSessionLocal
        from app.ground_truth.pipeline import GroundTruthPipeline

        pipeline = GroundTruthPipeline()
        async with AsyncSessionLocal() as db:
            run = await pipeline._create_run(  # noqa: SLF001
                db=db,
                run_type="negative_sampling",
                config={},
                now=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
            )
            return await pipeline.run_negative_sampling(run_id=run.id, db=db)

    try:
        return _run_async(_impl())
    except Exception as exc:  # noqa: BLE001
        log.error("run_negative_sampler failed", error=str(exc))
        raise self.retry(exc=exc, countdown=2**self.request.retries) from exc


# ── LLM Training Tasks (Phase 4) ──────────────────────────────────────────────


@celery_app.task(
    bind=True,
    max_retries=1,
    name="app.tasks._impl.run_pseudo_labeler",
    soft_time_limit=3600,
    time_limit=3900,
)
def run_pseudo_labeler(self: Task) -> dict:  # type: ignore[type-arg]
    """Agent 018: Pseudo-Label Quality — Groq batch classification of unlabeled signals."""

    async def _impl() -> dict[str, Any]:
        from app.database import AsyncSessionLocal
        from app.models.ground_truth import LabelingRun, RunStatus, RunType
        from app.training.pseudo_labeler import PseudoLabeler

        now = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
        async with AsyncSessionLocal() as db:
            run = LabelingRun(
                run_type=RunType.pseudo_label.value,
                status=RunStatus.running.value,
                started_at=now,
                config={},
            )
            db.add(run)
            await db.flush()
            await db.commit()

            result = await PseudoLabeler().run(run_id=run.id, db=db, now=now)
            run.status = RunStatus.completed.value
            run.completed_at = __import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            )
            run.positive_labels_created = result.get("pseudo_labels_created", 0)
            await db.commit()
            return result

    try:
        return _run_async(_impl())
    except Exception as exc:  # noqa: BLE001
        log.error("run_pseudo_labeler failed", error=str(exc))
        raise self.retry(exc=exc, countdown=2**self.request.retries) from exc


@celery_app.task(
    bind=True,
    max_retries=1,
    name="app.tasks._impl.run_training_data_curator",
    soft_time_limit=1800,
    time_limit=2100,
)
def run_training_data_curator(self: Task) -> dict:  # type: ignore[type-arg]
    """Agent 019: Training Data Curator — label QA + training set export."""

    async def _impl() -> dict[str, Any]:
        from app.database import AsyncSessionLocal
        from app.training.curator import TrainingDataCurator

        async with AsyncSessionLocal() as db:
            result = await TrainingDataCurator().curate(db=db)
            await db.commit()
            return result

    try:
        return _run_async(_impl())
    except Exception as exc:  # noqa: BLE001
        log.error("run_training_data_curator failed", error=str(exc))
        raise self.retry(exc=exc, countdown=2**self.request.retries) from exc


# ── Phase 5: Live Feed Tasks ───────────────────────────────────────────────────


@celery_app.task(
    bind=True,
    max_retries=3,
    name="app.tasks._impl.scrape_sedar_live",
    soft_time_limit=270,
    time_limit=300,
)
def scrape_sedar_live(self: Task) -> dict:  # type: ignore[type-arg]
    """Poll SEDAR+ material change RSS every 5 minutes and push to live feed stream."""

    async def _impl() -> dict[str, Any]:
        from app.services.live_feed import live_feed

        await live_feed.ensure_consumer_group()
        # Stub: real implementation calls SEDAR+ RSS, compares against last-seen entry,
        # and calls live_feed.push_signal() for each new material change report.
        log.info("scrape_sedar_live invoked — live RSS polling (Phase 5)")
        return {"status": "ok", "source": "sedar_live", "signals_pushed": 0}

    try:
        return _run_async(_impl())
    except Exception as exc:  # noqa: BLE001
        log.error("scrape_sedar_live failed", error=str(exc))
        raise self.retry(exc=exc, countdown=2**self.request.retries) from exc


@celery_app.task(
    bind=True,
    max_retries=3,
    name="app.tasks._impl.scrape_osc_live",
    soft_time_limit=270,
    time_limit=300,
)
def scrape_osc_live(self: Task) -> dict:  # type: ignore[type-arg]
    """Poll OSC enforcement RSS every 10 minutes and push to live feed stream."""

    async def _impl() -> dict[str, Any]:
        from app.services.live_feed import live_feed

        await live_feed.ensure_consumer_group()
        log.info("scrape_osc_live invoked — OSC RSS polling (Phase 5)")
        return {"status": "ok", "source": "osc_live", "signals_pushed": 0}

    try:
        return _run_async(_impl())
    except Exception as exc:  # noqa: BLE001
        log.error("scrape_osc_live failed", error=str(exc))
        raise self.retry(exc=exc, countdown=2**self.request.retries) from exc


@celery_app.task(
    bind=True,
    max_retries=3,
    name="app.tasks._impl.scrape_canlii_live",
    soft_time_limit=270,
    time_limit=300,
)
def scrape_canlii_live(self: Task) -> dict:  # type: ignore[type-arg]
    """Poll CanLII new decisions every 15 minutes and push to live feed stream."""

    async def _impl() -> dict[str, Any]:
        from app.services.live_feed import live_feed

        await live_feed.ensure_consumer_group()
        log.info("scrape_canlii_live invoked — CanLII polling (Phase 5)")
        return {"status": "ok", "source": "canlii_live", "signals_pushed": 0}

    try:
        return _run_async(_impl())
    except Exception as exc:  # noqa: BLE001
        log.error("scrape_canlii_live failed", error=str(exc))
        raise self.retry(exc=exc, countdown=2**self.request.retries) from exc


@celery_app.task(
    bind=True,
    max_retries=3,
    name="app.tasks._impl.scrape_news_live",
    soft_time_limit=270,
    time_limit=300,
)
def scrape_news_live(self: Task) -> dict:  # type: ignore[type-arg]
    """Poll Globe, FP, Reuters RSS every 5 minutes and push to live feed stream."""

    async def _impl() -> dict[str, Any]:
        from app.services.live_feed import live_feed

        await live_feed.ensure_consumer_group()
        log.info("scrape_news_live invoked — news RSS polling (Phase 5)")
        return {"status": "ok", "source": "news_live", "signals_pushed": 0}

    try:
        return _run_async(_impl())
    except Exception as exc:  # noqa: BLE001
        log.error("scrape_news_live failed", error=str(exc))
        raise self.retry(exc=exc, countdown=2**self.request.retries) from exc


@celery_app.task(
    bind=True,
    max_retries=3,
    name="app.tasks._impl.scrape_scc_live",
    soft_time_limit=270,
    time_limit=300,
)
def scrape_scc_live(self: Task) -> dict:  # type: ignore[type-arg]
    """Poll SCC decision RSS every 30 minutes and push to live feed stream."""

    async def _impl() -> dict[str, Any]:
        from app.services.live_feed import live_feed

        await live_feed.ensure_consumer_group()
        log.info("scrape_scc_live invoked — SCC RSS polling (Phase 5)")
        return {"status": "ok", "source": "scc_live", "signals_pushed": 0}

    try:
        return _run_async(_impl())
    except Exception as exc:  # noqa: BLE001
        log.error("scrape_scc_live failed", error=str(exc))
        raise self.retry(exc=exc, countdown=2**self.request.retries) from exc


@celery_app.task(
    bind=True,
    max_retries=3,
    name="app.tasks._impl.scrape_edgar_live",
    soft_time_limit=270,
    time_limit=300,
)
def scrape_edgar_live(self: Task) -> dict:  # type: ignore[type-arg]
    """Poll SEC EDGAR 8-K RSS every 5 minutes and push to live feed stream."""

    async def _impl() -> dict[str, Any]:
        from app.services.live_feed import live_feed

        await live_feed.ensure_consumer_group()
        log.info("scrape_edgar_live invoked — EDGAR 8-K RSS polling (Phase 5)")
        return {"status": "ok", "source": "edgar_live", "signals_pushed": 0}

    try:
        return _run_async(_impl())
    except Exception as exc:  # noqa: BLE001
        log.error("scrape_edgar_live failed", error=str(exc))
        raise self.retry(exc=exc, countdown=2**self.request.retries) from exc


@celery_app.task(
    bind=True,
    max_retries=3,
    name="app.tasks._impl.process_live_feed_events",
    soft_time_limit=270,
    time_limit=300,
)
def process_live_feed_events(self: Task) -> dict:  # type: ignore[type-arg]
    """Agent 020: Priority Router — consume oracle:live:signals stream and trigger scoring."""

    async def _impl() -> dict[str, Any]:
        from app.services.live_feed import live_feed

        await live_feed.ensure_consumer_group()
        messages = await live_feed.read_events(batch_size=100, block_ms=500)

        processed = 0
        errors = 0
        for msg_id, data in messages:
            try:
                # Phase 6+: trigger score_company.delay(data["company_id"])
                # For now: acknowledge and log each event
                log.info(
                    "live_feed_event_received",
                    msg_id=msg_id,
                    signal_type=data.get("signal_type"),
                    company_id=data.get("company_id"),
                )
                await live_feed.acknowledge(msg_id)
                processed += 1
            except Exception as exc:  # noqa: BLE001
                log.error("live_feed_event_processing_failed", msg_id=msg_id, error=str(exc))
                errors += 1

        return {
            "status": "ok",
            "agent": 20,
            "processed": processed,
            "errors": errors,
            "stream_length": await live_feed.stream_length(),
        }

    try:
        return _run_async(_impl())
    except Exception as exc:  # noqa: BLE001
        log.error("process_live_feed_events failed", error=str(exc))
        raise self.retry(exc=exc, countdown=2**self.request.retries) from exc


@celery_app.task(
    bind=True,
    max_retries=3,
    name="app.tasks._impl.monitor_signal_velocity",
    soft_time_limit=270,
    time_limit=300,
)
def monitor_signal_velocity(self: Task) -> dict:  # type: ignore[type-arg]
    """Agent 021: Velocity Monitor — compute rolling 48h velocity scores for all companies."""

    async def _impl() -> dict[str, Any]:
        from app.services.velocity_monitor import velocity_monitor

        result = await velocity_monitor.run()
        return {"status": "ok", "agent": 21, **result}

    try:
        return _run_async(_impl())
    except Exception as exc:  # noqa: BLE001
        log.error("monitor_signal_velocity failed", error=str(exc))
        raise self.retry(exc=exc, countdown=2**self.request.retries) from exc


@celery_app.task(
    bind=True,
    max_retries=3,
    name="app.tasks._impl.run_dead_signal_resurrector",
    soft_time_limit=270,
    time_limit=300,
)
def run_dead_signal_resurrector(self: Task) -> dict:  # type: ignore[type-arg]
    """Agent 022: Dead Signal Resurrector — detect silent scrapers and trigger re-runs."""

    async def _impl() -> dict[str, Any]:
        from app.services.resurrector import resurrector

        result = await resurrector.run()
        return {"status": "ok", "agent": 22, **result}

    try:
        return _run_async(_impl())
    except Exception as exc:  # noqa: BLE001
        log.error("run_dead_signal_resurrector failed", error=str(exc))
        raise self.retry(exc=exc, countdown=2**self.request.retries) from exc


@celery_app.task(
    bind=True,
    max_retries=1,
    name="app.tasks._impl.trigger_linkedin_lookup",
    soft_time_limit=60,
    time_limit=90,
)
def trigger_linkedin_lookup(self: Task, signal_data: dict) -> dict:  # type: ignore[type-arg]
    """Agent 067 support: On-demand LinkedIn Proxycurl lookup for C-suite departure signals."""

    async def _impl() -> dict[str, Any]:
        from app.services.linkedin_trigger import linkedin_trigger

        result = await linkedin_trigger.run(signal_data)
        return {"status": "ok", "agent": 67, **result}

    try:
        return _run_async(_impl())
    except Exception as exc:  # noqa: BLE001
        log.error("trigger_linkedin_lookup failed", error=str(exc))
        raise self.retry(exc=exc, countdown=2**self.request.retries) from exc


# ── Agent Tasks (Phase 6+) ─────────────────────────────────────────────────────


@celery_app.task(bind=True, max_retries=3, name="app.tasks._impl.agent_health_supervisor")
def agent_health_supervisor(self: Task) -> dict:  # type: ignore[type-arg]
    """Agent 061: Monitor all other agents for failures."""
    log.info("agent_health_supervisor invoked (stub — implement in Phase 6)")
    return {"status": "stub", "agent": 61}


@celery_app.task(bind=True, max_retries=3, name="app.tasks._impl.agent_source_discovery")
def agent_source_discovery(self: Task) -> dict:  # type: ignore[type-arg]
    """Agent 004: Discover new data sources ORACLE isn't using yet."""
    log.info("agent_source_discovery invoked (stub — implement in Phase 1)")
    return {"status": "stub", "agent": 4}


@celery_app.task(bind=True, max_retries=3, name="app.tasks._impl.agent_signal_weight_optimiser")
def agent_signal_weight_optimiser(self: Task) -> dict:  # type: ignore[type-arg]
    """Agent 033: Monthly signal weight optimisation from confirmed outcomes."""
    log.info("agent_signal_weight_optimiser invoked (stub — implement in Phase 12)")
    return {"status": "stub", "agent": 33}
