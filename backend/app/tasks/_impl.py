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

import logging

from celery import Task

from app.tasks.celery_app import celery_app

log = logging.getLogger(__name__)


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


@celery_app.task(bind=True, max_retries=3, name="app.tasks._impl.scrape_edgar")
def scrape_edgar(self: Task) -> dict:  # type: ignore[type-arg]
    """Scrape SEC EDGAR for 10-K/10-Q financials, 8-K events, SC 13D."""
    log.info("scrape_edgar invoked (stub — implement in Phase 1)")
    return {"status": "stub", "source": "edgar"}


@celery_app.task(bind=True, max_retries=3, name="app.tasks._impl.scrape_regulatory_feeds")
def scrape_regulatory_feeds(self: Task) -> dict:  # type: ignore[type-arg]
    """Scrape OSC, OSFI, Competition Bureau, FINTRAC, OPC, ECCC RSS feeds."""
    log.info("scrape_regulatory_feeds invoked (stub — implement in Phase 1)")
    return {"status": "stub", "source": "regulatory"}


@celery_app.task(bind=True, max_retries=3, name="app.tasks._impl.scrape_jobs")
def scrape_jobs(self: Task) -> dict:  # type: ignore[type-arg]
    """Scrape Indeed, LinkedIn, Job Bank for GC/CCO/CISO/litigation counsel postings."""
    log.info("scrape_jobs invoked (stub — implement in Phase 1)")
    return {"status": "stub", "source": "jobs"}


@celery_app.task(bind=True, max_retries=3, name="app.tasks._impl.scrape_canlii")
def scrape_canlii(self: Task) -> dict:  # type: ignore[type-arg]
    """Scrape CanLII API for new litigation by watchlist companies."""
    log.info("scrape_canlii invoked (stub — implement in Phase 1)")
    return {"status": "stub", "source": "canlii"}


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


@celery_app.task(bind=True, max_retries=3, name="app.tasks._impl.scrape_law_firm_blogs")
def scrape_law_firm_blogs(self: Task) -> dict:  # type: ignore[type-arg]
    """Scrape 27 Canadian law firm blogs for legal intelligence."""
    log.info("scrape_law_firm_blogs invoked (stub — implement in Phase 1)")
    return {"status": "stub", "source": "law_firm_blogs"}


@celery_app.task(bind=True, max_retries=3, name="app.tasks._impl.scrape_osb_insolvency")
def scrape_osb_insolvency(self: Task) -> dict:  # type: ignore[type-arg]
    """Download OSB insolvency Excel files and build FSA stress index."""
    log.info("scrape_osb_insolvency invoked (stub — implement in Phase 1)")
    return {"status": "stub", "source": "osb"}


@celery_app.task(bind=True, max_retries=3, name="app.tasks._impl.scrape_google_trends")
def scrape_google_trends(self: Task) -> dict:  # type: ignore[type-arg]
    """Scrape Google Trends via Pytrends for legal search term spikes."""
    log.info("scrape_google_trends invoked (stub — implement in Phase 1)")
    return {"status": "stub", "source": "google_trends"}


# ── Feature Engineering Tasks (Phase 2) ───────────────────────────────────────


@celery_app.task(bind=True, max_retries=3, name="app.tasks._impl.extract_features_all")
def extract_features_all(self: Task) -> dict:  # type: ignore[type-arg]
    """Extract continuous feature vectors for all watchlist companies."""
    log.info("extract_features_all invoked (stub — implement in Phase 2)")
    return {"status": "stub", "phase": "feature_engineering"}


@celery_app.task(bind=True, max_retries=3, name="app.tasks._impl.rebuild_feature_vectors")
def rebuild_feature_vectors(self: Task) -> dict:  # type: ignore[type-arg]
    """Rebuild all feature vectors from raw signals (full recompute)."""
    log.info("rebuild_feature_vectors invoked (stub — implement in Phase 2)")
    return {"status": "stub", "phase": "feature_engineering"}


# ── Scoring Tasks (Phase 6) ────────────────────────────────────────────────────


@celery_app.task(bind=True, max_retries=3, name="app.tasks._impl.run_scoring_all_companies")
def run_scoring_all_companies(self: Task) -> dict:  # type: ignore[type-arg]
    """Run 34-engine scoring for all watchlist companies."""
    log.info("run_scoring_all_companies invoked (stub — implement in Phase 6)")
    return {"status": "stub", "phase": "scoring"}


@celery_app.task(bind=True, max_retries=3, name="app.tasks._impl.score_company")
def score_company(self: Task, company_id: str) -> dict:  # type: ignore[type-arg]
    """Run 34-engine scoring for a single company (on-demand)."""
    log.info("score_company invoked (stub — implement in Phase 6)", company_id=company_id)  # type: ignore[call-arg]
    return {"status": "stub", "company_id": company_id}


@celery_app.task(bind=True, max_retries=1, name="app.tasks._impl.retrain_all_models")
def retrain_all_models(self: Task) -> dict:  # type: ignore[type-arg]
    """Weekly retraining of all ML models on accumulated label data."""
    log.info("retrain_all_models invoked (stub — implement in Phase 6)")
    return {"status": "stub", "phase": "training"}


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
