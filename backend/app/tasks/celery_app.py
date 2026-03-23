"""
app/tasks/celery_app.py — Celery application and task schedule configuration.

Key design decisions:
  - RedBeat scheduler: stores schedule in Redis, prevents duplicate task execution
    in multi-node deployments (critical for production scrapers)
  - Separate queues by task type: scrapers, features, scoring, agents
    This prevents slow scraper tasks from blocking fast scoring tasks
  - worker_prefetch_multiplier=1: fair scheduling (one task per worker at a time)
  - task_time_limit: hard kills tasks that run too long (prevents zombie processes)
  - task_acks_late=True: task acknowledged AFTER completion (safer for failures)

Queue architecture:
  - scrapers: all 90+ data collection tasks (long-running, IO-bound)
  - features: feature extraction pipeline (CPU-bound)
  - scoring: ML scoring pipeline (priority — partners need fresh scores)
  - agents: 85 ORACLE production agents (mixed)
  - default: everything else
"""

from __future__ import annotations

from celery import Celery
from celery.schedules import crontab
from kombu import Exchange, Queue

from app.config import get_settings

settings = get_settings()

# ── Celery Application ─────────────────────────────────────────────────────────

celery_app = Celery(
    "oracle",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.tasks._impl",  # All task implementations
    ],
)

# ── Core Configuration ─────────────────────────────────────────────────────────

celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Reliability
    task_acks_late=True,           # Acknowledge AFTER completion (safer on failure)
    task_reject_on_worker_lost=True,  # Requeue if worker dies mid-task
    worker_prefetch_multiplier=1,  # Fair scheduling — one task per worker

    # Timeouts (prevent zombie tasks)
    task_time_limit=settings.celery_task_time_limit,        # Hard kill (3600s)
    task_soft_time_limit=settings.celery_task_soft_time_limit,  # Raise SoftTimeLimitExceeded (3300s)

    # Memory management
    worker_max_tasks_per_child=1000,  # Restart worker after 1000 tasks (prevent memory leaks)
    worker_max_memory_per_child=512000,  # 512MB per worker process

    # Result backend
    result_expires=86400,          # Results expire after 24 hours
    result_compression="gzip",     # Compress results to save Redis memory

    # Concurrency
    worker_concurrency=settings.celery_worker_concurrency,

    # RedBeat scheduler (prevents duplicate execution in multi-node)
    beat_scheduler="redbeat.RedBeatScheduler",
    redbeat_redis_url=settings.redis_url,
    redbeat_lock_timeout=60,       # Lock timeout in seconds

    # Beat schedule key prefix
    beat_max_loop_interval=5,      # Check schedule every 5 seconds

    # Task routing — each queue type has different priority and concurrency
    task_default_queue="default",
    task_default_exchange="oracle",
    task_default_routing_key="default",
)

# ── Queue Definitions ──────────────────────────────────────────────────────────

default_exchange = Exchange("oracle", type="direct")

celery_app.conf.task_queues = (
    Queue("scrapers", default_exchange, routing_key="scrapers"),   # 90+ scrapers
    Queue("features", default_exchange, routing_key="features"),   # Feature extraction
    Queue("scoring",  default_exchange, routing_key="scoring"),    # ML scoring (priority)
    Queue("agents",   default_exchange, routing_key="agents"),     # 85 ORACLE agents
    Queue("default",  default_exchange, routing_key="default"),    # Everything else
)

# ── Task Routing ───────────────────────────────────────────────────────────────

celery_app.conf.task_routes = {
    # All scraper tasks → scrapers queue
    "app.tasks._impl.scrape_*": {"queue": "scrapers"},

    # Feature engineering → features queue
    "app.tasks._impl.extract_features*": {"queue": "features"},
    "app.tasks._impl.rebuild_feature_vectors": {"queue": "features"},

    # ML scoring → scoring queue (highest priority — partners see this)
    "app.tasks._impl.run_scoring*": {"queue": "scoring"},
    "app.tasks._impl.score_company*": {"queue": "scoring"},

    # Model training → features queue (CPU-intensive but not time-critical)
    "app.tasks._impl.retrain_*": {"queue": "features"},

    # ORACLE agents → agents queue
    "app.tasks._impl.agent_*": {"queue": "agents"},
    "app.tasks._impl.run_agent_*": {"queue": "agents"},
}

# ── Beat Schedule ──────────────────────────────────────────────────────────────
# All scheduled tasks. Times are UTC.
# Implemented in Phase 1+ — stubs defined here for scaffold.

celery_app.conf.beat_schedule = {

    # ── Phase 1: Scrapers ──────────────────────────────────────────────────────

    # SEDAR+ — every 2 hours during business hours (Toronto time = UTC-5)
    "scrape-sedar": {
        "task": "app.tasks._impl.scrape_sedar",
        "schedule": crontab(minute=0, hour="6,8,10,12,14,16,18,20"),
        "options": {"queue": "scrapers"},
    },

    # SEC EDGAR — every hour
    "scrape-edgar": {
        "task": "app.tasks._impl.scrape_edgar",
        "schedule": crontab(minute=15),
        "options": {"queue": "scrapers"},
    },

    # Regulatory RSS feeds — every 4 hours
    "scrape-regulatory": {
        "task": "app.tasks._impl.scrape_regulatory_feeds",
        "schedule": crontab(minute=0, hour="*/4"),
        "options": {"queue": "scrapers"},
    },

    # Job postings — daily at 6am UTC
    "scrape-jobs": {
        "task": "app.tasks._impl.scrape_jobs",
        "schedule": crontab(minute=0, hour=6),
        "options": {"queue": "scrapers"},
    },

    # CanLII — daily at 7am UTC
    "scrape-canlii": {
        "task": "app.tasks._impl.scrape_canlii",
        "schedule": crontab(minute=0, hour=7),
        "options": {"queue": "scrapers"},
    },

    # OpenSky ADS-B jets — daily at 3am UTC
    "scrape-jets": {
        "task": "app.tasks._impl.scrape_jets",
        "schedule": crontab(minute=0, hour=3),
        "options": {"queue": "scrapers"},
    },

    # Social media — every 6 hours
    "scrape-social": {
        "task": "app.tasks._impl.scrape_social",
        "schedule": crontab(minute=30, hour="*/6"),
        "options": {"queue": "scrapers"},
    },

    # Law firm blogs — every 6 hours
    "scrape-law-firm-blogs": {
        "task": "app.tasks._impl.scrape_law_firm_blogs",
        "schedule": crontab(minute=0, hour="*/6"),
        "options": {"queue": "scrapers"},
    },

    # OSB insolvency stats — weekly on Monday at 8am
    "scrape-osb": {
        "task": "app.tasks._impl.scrape_osb_insolvency",
        "schedule": crontab(minute=0, hour=8, day_of_week=1),
        "options": {"queue": "scrapers"},
    },

    # Google Trends — every 6 hours
    "scrape-trends": {
        "task": "app.tasks._impl.scrape_google_trends",
        "schedule": crontab(minute=0, hour="*/6"),
        "options": {"queue": "scrapers"},
    },

    # ── Phase 2: Feature Engineering ──────────────────────────────────────────

    # Extract features after each scraper cycle
    "extract-features": {
        "task": "app.tasks._impl.extract_features_all",
        "schedule": crontab(minute=30, hour="*/2"),
        "options": {"queue": "features"},
    },

    # ── Phase 6: ML Scoring ────────────────────────────────────────────────────

    # Daily full scoring run at 2am UTC
    "run-scoring": {
        "task": "app.tasks._impl.run_scoring_all_companies",
        "schedule": crontab(minute=0, hour=2),
        "options": {"queue": "scoring"},
    },

    # Weekly model retraining — Sunday at 3am UTC
    "retrain-models": {
        "task": "app.tasks._impl.retrain_all_models",
        "schedule": crontab(minute=0, hour=3, day_of_week=0),  # Sunday
        "options": {"queue": "features"},
    },

    # ── ORACLE Agents ──────────────────────────────────────────────────────────

    # Agent Health Supervisor (Agent 061) — every 5 minutes
    "agent-health-supervisor": {
        "task": "app.tasks._impl.agent_health_supervisor",
        "schedule": crontab(minute="*/5"),
        "options": {"queue": "agents"},
    },

    # Source Discovery Agent (Agent 004) — weekly
    "agent-source-discovery": {
        "task": "app.tasks._impl.agent_source_discovery",
        "schedule": crontab(minute=0, hour=10, day_of_week=1),  # Monday 10am
        "options": {"queue": "agents"},
    },

    # Signal Weight Optimiser (Agent 033) — monthly on 1st at 4am
    "agent-signal-weight-optimiser": {
        "task": "app.tasks._impl.agent_signal_weight_optimiser",
        "schedule": crontab(minute=0, hour=4, day_of_month=1),
        "options": {"queue": "agents"},
    },
}
