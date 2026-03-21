"""
app/tasks/celery_app.py — Celery application with all scheduled intelligence tasks.

Beat schedule:
  - SEDAR scrape        every 2h during business hours
  - EDGAR scrape        every 1h
  - Enforcement scrape  every 4h
  - Jobs scrape         daily 6am
  - CanLII scrape       daily 7am
  - Convergence score   daily 2am
  - Churn score update  nightly 1am
  - Model retrain       every Sunday 3am
"""

import asyncio
import logging
from datetime import datetime, timezone

from celery import Celery
from celery.schedules import crontab

from app.config import get_settings

log = logging.getLogger(__name__)
settings = get_settings()


def _run(coro):
    """Run an async coroutine from a sync Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


celery_app = Celery(
    "bd_for_law",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="America/Toronto",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    beat_schedule={
        # ── Scrapers ──────────────────────────────────────────────────────
        "sedar-scrape": {
            "task": "app.tasks.celery_app.scrape_sedar",
            "schedule": crontab(minute=0, hour="8-18/2"),
        },
        "edgar-scrape": {
            "task": "app.tasks.celery_app.scrape_edgar",
            "schedule": crontab(minute=15),
        },
        "enforcement-scrape": {
            "task": "app.tasks.celery_app.scrape_enforcement",
            "schedule": crontab(minute=0, hour="*/4"),
        },
        "jobs-scrape": {
            "task": "app.tasks.celery_app.scrape_jobs",
            "schedule": crontab(hour=6, minute=0),
        },
        "canlii-scrape": {
            "task": "app.tasks.celery_app.scrape_canlii",
            "schedule": crontab(hour=7, minute=0),
        },
        "jets-scrape": {
            "task": "app.tasks.celery_app.scrape_jets",
            "schedule": crontab(hour=3, minute=0),
        },
        # ── Scoring ───────────────────────────────────────────────────────
        "convergence-score": {
            "task": "app.tasks.celery_app.run_convergence_scoring",
            "schedule": crontab(hour=2, minute=0),
        },
        "churn-score": {
            "task": "app.tasks.celery_app.update_churn_scores",
            "schedule": crontab(hour=1, minute=0),
        },
        # ── Model retraining ──────────────────────────────────────────────
        "model-retrain": {
            "task": "app.tasks.celery_app.retrain_models",
            "schedule": crontab(day_of_week=0, hour=3, minute=0),
        },
    },
)


# ── Scraper tasks ──────────────────────────────────────────────────────────────

@celery_app.task(name="app.tasks.celery_app.scrape_sedar", bind=True, max_retries=3)
def scrape_sedar(self):
    """Scrape SEDAR+ for new filing-type triggers."""
    from app.tasks._impl import run_sedar_scrape
    try:
        count = _run(run_sedar_scrape())
        log.info("SEDAR: persisted %d new triggers", count)
        return {"count": count}
    except Exception as exc:
        log.error("SEDAR scrape failed: %s", exc)
        raise self.retry(exc=exc, countdown=120)


@celery_app.task(name="app.tasks.celery_app.scrape_edgar", bind=True, max_retries=3)
def scrape_edgar(self):
    from app.tasks._impl import run_edgar_scrape
    try:
        count = _run(run_edgar_scrape())
        return {"count": count}
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(name="app.tasks.celery_app.scrape_enforcement", bind=True, max_retries=3)
def scrape_enforcement(self):
    from app.tasks._impl import run_enforcement_scrape
    try:
        count = _run(run_enforcement_scrape())
        return {"count": count}
    except Exception as exc:
        raise self.retry(exc=exc, countdown=240)


@celery_app.task(name="app.tasks.celery_app.scrape_jobs", bind=True, max_retries=2)
def scrape_jobs(self):
    from app.tasks._impl import run_jobs_scrape
    try:
        count = _run(run_jobs_scrape())
        return {"count": count}
    except Exception as exc:
        raise self.retry(exc=exc, countdown=300)


@celery_app.task(name="app.tasks.celery_app.scrape_canlii", bind=True, max_retries=2)
def scrape_canlii(self):
    from app.tasks._impl import run_canlii_scrape
    try:
        count = _run(run_canlii_scrape())
        return {"count": count}
    except Exception as exc:
        raise self.retry(exc=exc, countdown=300)


@celery_app.task(name="app.tasks.celery_app.scrape_jets", bind=True, max_retries=2)
def scrape_jets(self):
    from app.tasks._impl import run_jet_scrape
    try:
        count = _run(run_jet_scrape())
        return {"count": count}
    except Exception as exc:
        raise self.retry(exc=exc, countdown=300)


# ── Scoring tasks ──────────────────────────────────────────────────────────────

@celery_app.task(name="app.tasks.celery_app.run_convergence_scoring")
def run_convergence_scoring():
    """Score every watched company and fire alerts when thresholds are crossed."""
    from app.tasks._impl import run_scoring
    result = _run(run_scoring())
    log.info("Convergence scoring complete: %s", result)
    return result


@celery_app.task(name="app.tasks.celery_app.update_churn_scores")
def update_churn_scores():
    """Recompute churn scores for all active clients."""
    from app.tasks._impl import run_churn_update
    result = _run(run_churn_update())
    log.info("Churn update complete: %s", result)
    return result


# ── Model retraining ───────────────────────────────────────────────────────────

@celery_app.task(name="app.tasks.celery_app.retrain_models")
def retrain_models():
    """Retrain urgency + PA classifier models from accumulated labels."""
    from app.tasks._impl import run_model_retrain
    result = _run(run_model_retrain())
    log.info("Model retrain complete: %s", result)
    return result
