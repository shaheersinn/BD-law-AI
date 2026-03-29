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
        "app.tasks._impl",  # Phase 0-5 task implementations
        "app.tasks.scraper_tasks",  # Phase S1-S4 category scraper tasks
        "app.tasks.phase6_tasks",  # Phase 6 ML agents
        "app.tasks.phase9_tasks",  # Phase 9 Feedback Loop agents
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
    task_acks_late=True,  # Acknowledge AFTER completion (safer on failure)
    task_reject_on_worker_lost=True,  # Requeue if worker dies mid-task
    worker_prefetch_multiplier=1,  # Fair scheduling — one task per worker
    # Timeouts (prevent zombie tasks)
    task_time_limit=settings.celery_task_time_limit,  # Hard kill (3600s)
    task_soft_time_limit=settings.celery_task_soft_time_limit,  # Raise SoftTimeLimitExceeded (3300s)
    # Memory management
    worker_max_tasks_per_child=1000,  # Restart worker after 1000 tasks (prevent memory leaks)
    worker_max_memory_per_child=512000,  # 512MB per worker process
    # Result backend
    result_expires=86400,  # Results expire after 24 hours
    result_compression="gzip",  # Compress results to save Redis memory
    # Concurrency
    worker_concurrency=settings.celery_worker_concurrency,
    # RedBeat scheduler (prevents duplicate execution in multi-node)
    beat_scheduler="redbeat.RedBeatScheduler",
    redbeat_redis_url=settings.redis_url,
    redbeat_lock_timeout=60,  # Lock timeout in seconds
    # Beat schedule key prefix
    beat_max_loop_interval=5,  # Check schedule every 5 seconds
    # Task routing — each queue type has different priority and concurrency
    task_default_queue="default",
    task_default_exchange="oracle",
    task_default_routing_key="default",
)

# ── Queue Definitions ──────────────────────────────────────────────────────────

default_exchange = Exchange("oracle", type="direct")

celery_app.conf.task_queues = (
    Queue("scrapers", default_exchange, routing_key="scrapers"),  # 90+ scrapers
    Queue("features", default_exchange, routing_key="features"),  # Feature extraction
    Queue("scoring", default_exchange, routing_key="scoring"),  # ML scoring (priority)
    Queue("agents", default_exchange, routing_key="agents"),  # 85 ORACLE agents
    Queue("default", default_exchange, routing_key="default"),  # Everything else
)

# ── Task Routing ───────────────────────────────────────────────────────────────

celery_app.conf.task_routes = {
    # Phase S4: Real category scraper tasks → scrapers queue
    "scrapers.run_corporate": {"queue": "scrapers"},
    "scrapers.run_legal": {"queue": "scrapers"},
    "scrapers.run_regulatory": {"queue": "scrapers"},
    "scrapers.run_jobs": {"queue": "scrapers"},
    "scrapers.run_market": {"queue": "scrapers"},
    "scrapers.run_news": {"queue": "scrapers"},
    "scrapers.run_social": {"queue": "scrapers"},
    "scrapers.run_geo": {"queue": "scrapers"},
    "scrapers.run_law_blogs": {"queue": "scrapers"},
    "scrapers.health_check_all": {"queue": "default"},
    "scrapers.run_single": {"queue": "scrapers"},
    "scrapers.canary_check": {"queue": "default"},
    "scrapers.run_class_actions": {"queue": "scrapers"},
    "scrapers.scrape_consumer_precursors": {"queue": "scrapers"},
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
    # Ground truth agents → agents queue
    "app.tasks._impl.run_retrospective_labeler": {"queue": "agents"},
    "app.tasks._impl.run_negative_sampler": {"queue": "agents"},
    # LLM Training agents → agents queue
    "app.tasks._impl.run_pseudo_labeler": {"queue": "agents"},
    "app.tasks._impl.run_training_data_curator": {"queue": "agents"},
    # Phase 5: Live feed scrapers → scrapers queue
    "app.tasks._impl.scrape_sedar_live": {"queue": "scrapers"},
    "app.tasks._impl.scrape_osc_live": {"queue": "scrapers"},
    "app.tasks._impl.scrape_canlii_live": {"queue": "scrapers"},
    "app.tasks._impl.scrape_news_live": {"queue": "scrapers"},
    "app.tasks._impl.scrape_scc_live": {"queue": "scrapers"},
    "app.tasks._impl.scrape_edgar_live": {"queue": "scrapers"},
    # Phase 5: Live feed consumer → scoring queue (time-critical)
    "app.tasks._impl.process_live_feed_events": {"queue": "scoring"},
    # Phase 5: Velocity monitor + resurrector → agents queue
    "app.tasks._impl.monitor_signal_velocity": {"queue": "agents"},
    "app.tasks._impl.run_dead_signal_resurrector": {"queue": "agents"},
    "app.tasks._impl.trigger_linkedin_lookup": {"queue": "agents"},
    # Phase 9: Feedback Loop agents → agents queue
    "agents.compute_prediction_accuracy": {"queue": "agents"},
    "agents.run_drift_detector": {"queue": "agents"},
    "agents.run_confirmation_hunter": {"queue": "agents"},
    # Phase CA-3: Convergence Engine
    "ml.score_class_action_risk": {"queue": "scoring"},
}

# ── Beat Schedule ──────────────────────────────────────────────────────────────
# All scheduled tasks. Times are UTC.
# Implemented in Phase 1+ — stubs defined here for scaffold.

celery_app.conf.beat_schedule = {
    # ── Phase S4: Category Scraper Tasks (real implementations) ─────────────────
    # Regulatory — daily 6am Toronto (11:00 UTC)
    "run-regulatory-scrapers": {
        "task": "scrapers.run_regulatory",
        "schedule": crontab(hour=11, minute=0),
        "options": {"queue": "scrapers"},
    },
    # Social — twice daily (morning + evening)
    "run-social-scrapers-morning": {
        "task": "scrapers.run_social",
        "schedule": crontab(hour=12, minute=30),
        "options": {"queue": "scrapers"},
    },
    "run-social-scrapers-evening": {
        "task": "scrapers.run_social",
        "schedule": crontab(hour=0, minute=30),
        "options": {"queue": "scrapers"},
    },
    # Geo — daily 8am Toronto (13:00 UTC)
    "run-geo-scrapers-daily": {
        "task": "scrapers.run_geo",
        "schedule": crontab(hour=13, minute=0),
        "options": {"queue": "scrapers"},
    },
    # Corporate filings — daily 9am Toronto (14:00 UTC)
    "run-corporate-scrapers-daily": {
        "task": "scrapers.run_corporate",
        "schedule": crontab(hour=14, minute=0),
        "options": {"queue": "scrapers"},
    },
    # Legal — daily 10am Toronto (15:00 UTC)
    "run-legal-scrapers-daily": {
        "task": "scrapers.run_legal",
        "schedule": crontab(hour=15, minute=0),
        "options": {"queue": "scrapers"},
    },
    # Market data — every 4 hours during market hours (9:30, 13:30, 17:30 Toronto)
    "run-market-scrapers-market-hours": {
        "task": "scrapers.run_market",
        "schedule": crontab(hour="14,18,22", minute=30),
        "options": {"queue": "scrapers"},
    },
    # News — every 6 hours
    "run-news-scrapers": {
        "task": "scrapers.run_news",
        "schedule": crontab(hour="*/6", minute=15),
        "options": {"queue": "scrapers"},
    },
    # Jobs — daily 6am UTC
    "run-jobs-scrapers-daily": {
        "task": "scrapers.run_jobs",
        "schedule": crontab(hour=6, minute=0),
        "options": {"queue": "scrapers"},
    },
    # Law blogs — every 6 hours
    "run-law-blog-scrapers": {
        "task": "scrapers.run_law_blogs",
        "schedule": crontab(hour="*/6", minute=45),
        "options": {"queue": "scrapers"},
    },
    # Scraper health check — every 30 minutes
    "scraper-health-check": {
        "task": "scrapers.health_check_all",
        "schedule": crontab(minute="*/30"),
        "options": {"queue": "default"},
    },
    # ── Phase 1: Scrapers (legacy stubs) ─────────────────────────────────────
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
    # ── Phase 1B: Canary System (Agent 008) ───────────────────────────────────
    # Synthetic end-to-end pipeline verification — every 30 minutes
    "scraper-canary": {
        "task": "scrapers.canary_check",
        "schedule": crontab(minute="*/30"),
        "options": {"queue": "default"},
    },
    # ── Phase 3: Ground Truth ──────────────────────────────────────────────────
    # Agent 016: Retrospective Labeler — daily at 2am UTC
    "run-retrospective-labeler": {
        "task": "app.tasks._impl.run_retrospective_labeler",
        "schedule": crontab(minute=0, hour=2),
        "options": {"queue": "agents"},
    },
    # Agent 017: Negative Sampler — daily at 3am UTC
    "run-negative-sampler": {
        "task": "app.tasks._impl.run_negative_sampler",
        "schedule": crontab(minute=0, hour=3),
        "options": {"queue": "agents"},
    },
    # ── Phase 4: LLM Training ─────────────────────────────────────────────────
    # Agent 018: Pseudo-Labeler — daily at 4am UTC (after ground truth)
    "run-pseudo-labeler": {
        "task": "app.tasks._impl.run_pseudo_labeler",
        "schedule": crontab(minute=0, hour=4),
        "options": {"queue": "agents"},
    },
    # Agent 019: Training Data Curator — daily at 5am UTC (after pseudo-labeler)
    "run-training-data-curator": {
        "task": "app.tasks._impl.run_training_data_curator",
        "schedule": crontab(minute=0, hour=5),
        "options": {"queue": "agents"},
    },
    # ── Phase 5: Live Feed Scrapers ────────────────────────────────────────────
    # SEDAR+ material change reports — every 5 minutes
    "scrape-sedar-live": {
        "task": "app.tasks._impl.scrape_sedar_live",
        "schedule": crontab(minute="*/5"),
        "options": {"queue": "scrapers"},
    },
    # OSC enforcement actions — every 10 minutes
    "scrape-osc-live": {
        "task": "app.tasks._impl.scrape_osc_live",
        "schedule": crontab(minute="*/10"),
        "options": {"queue": "scrapers"},
    },
    # CanLII new decisions — every 15 minutes
    "scrape-canlii-live": {
        "task": "app.tasks._impl.scrape_canlii_live",
        "schedule": crontab(minute="*/15"),
        "options": {"queue": "scrapers"},
    },
    # Globe, FP, Reuters RSS — every 5 minutes
    "scrape-news-live": {
        "task": "app.tasks._impl.scrape_news_live",
        "schedule": crontab(minute="*/5"),
        "options": {"queue": "scrapers"},
    },
    # SCC decisions — every 30 minutes
    "scrape-scc-live": {
        "task": "app.tasks._impl.scrape_scc_live",
        "schedule": crontab(minute="*/30"),
        "options": {"queue": "scrapers"},
    },
    # EDGAR 8-K filings — every 5 minutes
    "scrape-edgar-live": {
        "task": "app.tasks._impl.scrape_edgar_live",
        "schedule": crontab(minute="*/5"),
        "options": {"queue": "scrapers"},
    },
    # ── Phase 5: Live Feed Consumer (Agent 020) ────────────────────────────────
    # Consumes oracle:live:signals stream and triggers priority scoring
    "process-live-feed-events": {
        "task": "app.tasks._impl.process_live_feed_events",
        "schedule": crontab(minute="*"),  # Every minute
        "options": {"queue": "scoring"},
    },
    # ── Phase 5: Velocity Monitor (Agent 021) ─────────────────────────────────
    # Computes 48-hour rolling signal velocity for all active companies
    "monitor-signal-velocity": {
        "task": "app.tasks._impl.monitor_signal_velocity",
        "schedule": crontab(minute="*/5"),
        "options": {"queue": "agents"},
    },
    # ── Phase 5: Dead Signal Resurrector (Agent 022) ───────────────────────────
    # Checks for silent scrapers and triggers immediate re-runs
    "run-dead-signal-resurrector": {
        "task": "app.tasks._impl.run_dead_signal_resurrector",
        "schedule": crontab(minute="*/30"),
        "options": {"queue": "agents"},
    },
    # ── Phase CA-1: Class Action Scrapers ─────────────────────────────────────
    "scrape-class-actions": {
        "task": "scrapers.run_class_actions",
        "schedule": crontab(hour="*/6", minute=30),
        "options": {"queue": "scrapers"},
    },
    # ── Phase CA-2: Consumer Precursor Scrapers ───────────────────────────────
    # Recalls, complaints, and privacy breaches — 3× daily at 8:45, 14:45, 20:45 UTC
    "scrape-consumer-precursors": {
        "task": "scrapers.scrape_consumer_precursors",
        "schedule": crontab(hour="8,14,20", minute=45),
        "options": {"queue": "scrapers"},
    },
    # ── Phase 9: Prediction Accuracy Tracker (Agent 030) ──────────────────────
    # Computes was_correct + lead_days for all pending mandate confirmations
    "compute-prediction-accuracy": {
        "task": "agents.compute_prediction_accuracy",
        "schedule": crontab(day_of_week="sunday", hour=1, minute=0),
        "options": {"queue": "agents"},
    },
    # ── Phase 9: Drift Detector (Agent 031) ───────────────────────────────────
    # Detects model accuracy degradation per practice area using KS test
    "run-drift-detector": {
        "task": "agents.run_drift_detector",
        "schedule": crontab(day_of_week="sunday", hour=2, minute=0),
        "options": {"queue": "agents"},
    },
    # ── Phase 9: Mandate Confirmation Hunter (Agent 032) ──────────────────────
    # Auto-detects mandate confirmations from live signals (canlii, law firms, SEDAR)
    "run-confirmation-hunter": {
        "task": "agents.run_confirmation_hunter",
        "schedule": crontab(hour=6, minute=30),
        "options": {"queue": "agents"},
    },
    # ── Phase CA-3: Class Action Signal Convergence Engine ────────────────────────
    "score_class_action_risk": {
        "task": "ml.score_class_action_risk",
        "schedule": crontab(hour=3, minute=0),
        "options": {"queue": "scoring"},
    },
}
