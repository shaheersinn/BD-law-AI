# ORACLE — BD for Law
## Project Knowledge Base for Claude Code Sub-Agents

> This file is the mandatory first read for every Claude Code sub-agent.
> context-manager reads this before briefing any other agent.
> Updated at end of every phase by api-documenter.

---

## What This Project Is

ORACLE is a standalone, production-grade ML intelligence platform that predicts which
companies will need legal counsel — across 34 practice areas — within 30/60/90 days.
Built for BigLaw BD teams. Zero external LLM dependency in production.

**ML models score. LLMs never score. Claude only writes code.**

---

## Current Phase Status

| Phase | Status | Completed |
|-------|--------|-----------|
| 0 — Scaffold | ✅ COMPLETE | March 2026 |
| 1 — Scrapers (90+) | ✅ COMPLETE | March 2026 |
| 1B — Scraper Audit | ✅ COMPLETE | March 2026 |
| 1C — Scraper Performance | ✅ COMPLETE | March 2026 |
| 2 — Feature Engineering | ✅ COMPLETE | March 2026 |
| 3 — Ground Truth | ✅ COMPLETE | March 2026 |
| 4 — LLM Training (Groq only) | ✅ COMPLETE | March 2026 |
| 5 — Live Feeds | ✅ COMPLETE | March 2026 |
| 6 — ML Training + 10 Enhancements | ✅ COMPLETE | March 2026 |
| 7 — Scoring API | ✅ COMPLETE | March 2026 |
| 8A — Functional Frontend | ✅ COMPLETE | March 2026 |
| 8B — Production UI (ConstructLex) | ✅ COMPLETE | March 2026 |
| 9 — Feedback Loop | ⏳ NEXT | — |
| 10 — Testing & Hardening | ⏳ PENDING | — |
| 11 — Deployment | ⏳ PENDING | — |
| 12 — Post-Launch Optimization | ✅ COMPLETE | March 2026 |

---

## Technology Stack

```
Backend:    FastAPI 0.115 / Python 3.12
ORM:        SQLAlchemy 2.0 async (asyncpg driver)
Cache:      Redis 7 (hiredis)
Queue:      Celery 5.4 + RedBeat scheduler
DB-1:       PostgreSQL 15 (structured data)
DB-2:       MongoDB Atlas / Motor (social signals, corporate graph)
ML:         XGBoost, LightGBM, scikit-learn, PyTorch (transformers)
Frontend:   React 18 + Vite + Recharts + D3.js
Deploy:     DigitalOcean App Platform (tor1), Vercel (frontend)
Training:   Azure credits (batch ML jobs), Groq API (Phase 4 only)
Storage:    DigitalOcean Spaces (model artifacts)
CI/CD:      GitHub Actions
```

---

## Project Structure

```
oracle-bd/
├── backend/
│   ├── app/
│   │   ├── config.py          ← Pydantic-settings v2. All env vars. get_settings() cached.
│   │   ├── database.py        ← Async SQLAlchemy (asyncpg) + Motor MongoDB
│   │   ├── main.py            ← FastAPI app. Lifespan. All middleware. Health endpoints.
│   │   ├── auth/              ← JWT auth. bcrypt 12. 4 roles. Account lockout.
│   │   ├── cache/             ← Redis client. Rate limiting. Signal-type TTLs.
│   │   ├── middleware/        ← Error handler. Request logging. Rate limiter.
│   │   ├── models/            ← SQLAlchemy ORM models (Phase 1+)
│   │   ├── scrapers/          ← 90+ scrapers (Phase 1)
│   │   ├── features/          ← Feature engineering (Phase 2)
│   │   │   ├── nlp/           ← MD&A diff, hedging detector, intent classifier
│   │   │   ├── geo/           ← Regional stress, court volume, Google Trends
│   │   │   └── macro/         ← Rate cycle, commodity shock, sector insolvency
│   │   ├── ml/                ← ML models (Phase 6)
│   │   │   └── convergence/   ← 34 Bayesian engines + Transformer
│   │   ├── ground_truth/      ← Label generation (Phase 3)
│   │   ├── training/          ← Model training scripts (Phase 6)
│   │   ├── services/          ← Scoring, evidence, entity resolution (Phase 7)
│   │   ├── routes/            ← FastAPI routers (Phase 7)
│   │   ├── tasks/             ← Celery tasks. celery_app.py + _impl.py
│   │   └── agents/            ← 85 ORACLE production agents (Phase 6+)
│   ├── alembic/               ← DB migrations
│   ├── scripts/seed_db.py     ← DB seeder
│   ├── tests/                 ← Test suite
│   ├── requirements.txt       ← ALL versions pinned
│   ├── requirements-dev.txt   ← Dev + test dependencies
│   ├── Dockerfile             ← Multi-stage, non-root user
│   ├── ruff.toml              ← Linting config
│   ├── mypy.ini               ← Type checking config
│   └── pyproject.toml         ← Pytest config
├── frontend/                  ← React/Vite (Phase 8A/8B)
├── notebooks/                 ← Exploratory analysis
├── .github/workflows/         ← CI (test+lint) + CD (deploy to DO)
├── docker-compose.yml         ← 7 services: db, mongodb, redis, api, worker, beat, frontend
├── do-app.yaml                ← DigitalOcean App Platform spec (tor1)
├── .env.example               ← All 35+ env vars documented
└── CLAUDE.md                  ← This file
```

---

## Critical Rules — Read Before Writing Any Code

### Language
- **English only.** No French NLP models. No bilingual processing. No French MD&A parsing.
- Quebec filings in French are out of scope.

### ML Architecture
- **ML models score. No LLM in production scoring. Ever.**
- Bayesian engines (work day 1) + Transformer (earns the right practice area by practice area)
- Groq API used in Phase 4 training ONLY. Never in production.
- 34 practice areas × 3 time horizons (30/60/90 day) = 34×3 output matrix per company

### Database Rules
- PostgreSQL: ALL structured data (companies, signals, features, scores, labels, users)
- MongoDB: ALL unstructured (social signals, corporate graph, law firm blog posts, scraped docs)
- Never store unstructured social content in PostgreSQL
- Never store structured relational data in MongoDB

### Async Rules
- ALL database operations must use async/await
- ALL external HTTP calls must use httpx (async) not requests (sync)
- NEVER block the event loop with synchronous I/O
- Use `asyncpg` driver — never psycopg2

### Security Rules
- NEVER hardcode secrets, API keys, passwords, or tokens
- ALL secrets come from environment variables via `get_settings()`
- JWT tokens carry ONLY: sub (user_id), role, type, iat, exp
- bcrypt cost factor MUST be 12 (`bcrypt__rounds=12`)
- Rate limiter MUST fail open (allow requests) when Redis is unavailable
- Docker MUST run as non-root user

### Celery Rules
- Use RedBeat scheduler — NEVER default file-based scheduler
- `worker_prefetch_multiplier=1` — fair scheduling, always
- `task_acks_late=True` — acknowledge after completion, always
- Always set `task_time_limit` and `task_soft_time_limit`
- Route tasks to correct queues: scrapers/features/scoring/agents/default

### Code Quality Requirements
- Every phase must pass: ruff check, ruff format, mypy, bandit
- Minimum 70% test coverage per phase
- NO bare except clauses — always catch specific exceptions
- ALL external calls (HTTP, DB, Redis, MongoDB) must have try/except with logging
- NO print() statements — use structlog

---

## Environment Variables (Key Ones)

```bash
SECRET_KEY          # JWT signing key — min 32 chars — CHANGE IN PRODUCTION
DATABASE_URL        # postgresql+asyncpg://oracle:oracle@localhost:5432/oracle_db
MONGODB_URL         # mongodb://localhost:27017 or Atlas URL
REDIS_URL           # redis://localhost:6379/0
ENVIRONMENT         # development | staging | production
GROQ_API_KEY        # Phase 4 ONLY — training pseudo-labeling — never production
CANLII_API_KEY      # Free — register at developer.canlii.org
OPENSKY_USERNAME    # Free — register at opensky-network.org
OPENSKY_PASSWORD    #
PROXYCURL_API_KEY   # LinkedIn scraping — 10 free credits/month
ALPHA_VANTAGE_API_KEY # Market data — 25 free requests/day
TWITTER_BEARER_TOKEN  # Twitter/X API
HIBP_API_KEY        # HaveIBeenPwned dark web monitoring
SENTRY_DSN          # Error monitoring — production only
SPACES_KEY          # DigitalOcean Spaces — model artifact storage
SPACES_SECRET       #
```

Full list in `.env.example`

---

## Running Locally

```bash
# First time
cp .env.example .env
# Edit .env — set SECRET_KEY

# Start everything
docker compose up

# API docs:    http://localhost:8000/api/docs
# Health:      http://localhost:8000/api/health
# Frontend:    http://localhost:5173
# Flower:      docker compose --profile monitoring up

# Run tests
make test

# Lint
make lint

# Format
make fmt

# Migrations
make migrate
```

---

## Default Credentials (Development Only)

```
Admin:   admin@halcyon.legal  / ChangeMe123!
Partner: partner@halcyon.legal / partner123!
```

**Change these before any real deployment.**

---

## Phase 0 — What Was Built

Phase 0 established the complete project scaffold. All architectural decisions are
implemented and verified. The app boots cleanly. Migrations run. Auth works. Tests pass.

### Key Files Added in Phase 0
- `app/config.py` — pydantic-settings v2, all env vars, production validator
- `app/database.py` — async SQLAlchemy 2.0 (asyncpg) + Motor MongoDB
- `app/main.py` — FastAPI with lifespan context manager
- `app/cache/client.py` — Redis cache + sliding window rate limiting
- `app/auth/` — full JWT auth system (4 files)
- `app/middleware/` — error handler + request logging + rate limiter
- `app/tasks/celery_app.py` — Celery + RedBeat, 5 queues, full beat schedule
- `app/tasks/_impl.py` — task stubs for all 90+ future tasks
- `backend/Dockerfile` — multi-stage, non-root
- `docker-compose.yml` — 7 services
- `do-app.yaml` — DigitalOcean App Platform (tor1)
- `.github/workflows/ci.yml` — ruff + mypy + bandit + pytest
- `.github/workflows/cd.yml` — auto-deploy to DigitalOcean on push to main
- `tests/test_health.py` — 8 smoke tests
- `tests/conftest.py` — pytest async configuration

### Audit Results — Phase 0
All 10 architecture checks passed. No bugs found. No hardcoded secrets.
No deprecated patterns. See Phase 0 Word document for full audit details.

---

## 34 Practice Areas (Scoring Engines)

M&A/Corporate, Litigation/Dispute Resolution, Regulatory/Compliance,
Employment/Labour, Insolvency/Restructuring, Securities/Capital Markets,
Competition/Antitrust, Privacy/Cybersecurity, Environmental/Indigenous/Energy,
Tax, Real Estate/Construction, Banking/Finance, Intellectual Property,
Immigration (Corporate), Infrastructure/Project Finance, Wills/Estates,
Administrative/Public Law, Arbitration/International Dispute, Class Actions,
Construction/Infrastructure Disputes, Defamation/Media Law,
Financial Regulatory (OSFI/FINTRAC), Franchise/Distribution,
Health Law/Life Sciences, Insurance/Reinsurance, International Trade/Customs,
Mining/Natural Resources, Municipal/Land Use, Not-for-Profit/Charity Law,
Pension/Benefits, Product Liability, Sports/Entertainment,
Technology/Fintech Regulatory, Data Privacy & Technology

---

## 10 Model Enhancements (Phase 6)

1. Multi-horizon prediction (30/60/90 day windows)
2. Mandate velocity scoring (rate of change alerting)
3. Corporate graph network (director interlocks — MongoDB)
4. Active learning loop (model surfaces uncertain cases)
5. Signal co-occurrence mining (Apriori on ground truth)
6. Industry-specific signal weighting (per sector multipliers)
7. Counterfactual explainability (SHAP — what would lower this score)
8. Cross-jurisdiction risk propagation
9. Anomaly detection layer (autoencoder)
10. Temporal decay modeling per practice area

---

## 85 ORACLE Production Agents

Agents 001-002: Infrastructure (System Health Guardian, Secret Rotation Watcher)
Agents 003-006: Core Scrapers (Orchestrator, Source Discovery, Budget Manager, Blog Monitor)
Agents 007-008: Scraper Audit (Data Quality Sentinel, Canary)
Agents 009-011: Scraper Performance (Grader, Triangulation, Format Change Detector)
Agents 012-015: Feature Engineering (Freshness, Negative Features, Peer Contamination, ESG)
Agents 016-017: Ground Truth (Retrospective Labeler, Negative Sampler)
Agents 018-019: LLM Training Core (Pseudo-Label Quality, Training Data Curator)
Agents 020-022: Live Feeds (Priority Router, Velocity Monitor, Dead Signal Resurrector)
Agents 023-027: ML Scoring (Model Selector, Anomaly Escalation, Score Decay, Sector Baseline, CCAA Cascade)
Agent 028: API (Rate Limit Enforcer)
Agent 029: Frontend (Dashboard Freshness)
Agents 030-032: Feedback Loop (Active Learning, Drift Detector, Mandate Confirmation Hunter)
Agents 033-035: Optimisation (Signal Weight, Regulatory Calendar, Competitive Intelligence)
Agents 036-050: Scraper Intelligence (Change Detection, URL Discovery, Payload Integrity, etc.)
Agents 051-060: LLM Training Advanced (Prompt Optimiser, Label Consistency, etc.)
Agents 061-066: Meta-Intelligence (Health Supervisor, Inter-Agent Bus, Self-Healing ML, etc.)
Agents 067-074: Signal Intelligence (Executive Behaviour, Supply Chain, Whistleblower, etc.)
Agents 075-079: MLOps (DB Performance, Feature Drift, Signal Discovery, etc.)
Agents 080-085: Network/Calibration (Graph Population, Temporal Miner, Ensemble Coordinator, etc.)

All implemented as Celery tasks in app/tasks/_impl.py (stubs in Phase 0, implemented Phase 6+)

---

## Phase 5 — What Was Built

Phase 5 established the live data feed pipeline — priority signals now delivered in < 60
seconds via Redis Streams instead of waiting for the next batch cycle.

### Key Files Added in Phase 5
- `app/services/live_feed.py` — LiveFeedRouter: Redis Stream `oracle:live:signals`, consumer
  group `scoring_consumers`, push/read/ack/stream_length helpers, `live_feeds_enabled` feature flag
- `app/services/velocity_monitor.py` — VelocityMonitor: 48-hour rolling velocity via Redis sorted
  sets, 30-day baseline normalisation, `signal_velocity_score` per company cached as Redis hash
- `app/services/linkedin_trigger.py` — LinkedInTrigger: on-demand Proxycurl lookup capped at
  5/day (Redis counter), fires only on confirmed C-suite departure signals from Agent 067
- `app/services/resurrector.py` — DeadSignalResurrector: queries scraper_health, detects silence
  beyond 2× expected interval, dispatches high-priority Celery re-run per category
- `app/tasks/_impl.py` — 10 new tasks: 6 live scrapers (sedar/osc/canlii/news/scc/edgar),
  Agents 020/021/022 (Priority Router, Velocity Monitor, Resurrector), Agent 067 LinkedIn trigger
- `app/tasks/celery_app.py` — 10 new beat entries: live scrapers every 5–30 min, stream consumer
  every 1 min, velocity monitor every 5 min, resurrector every 30 min; 10 new routing rules
- `tests/test_phase5_live_feeds.py` — 50+ tests covering all 4 services + Celery task registration

### Live-Trigger Sources (polling intervals)
- SEDAR+ material change reports → every 5 minutes
- OSC enforcement actions → every 10 minutes
- CanLII new decisions → every 15 minutes
- Globe / FP / Reuters RSS → every 5 minutes
- SCC decisions → every 30 minutes
- EDGAR 8-K filings → every 5 minutes

### Agents Activated in Phase 5
- Agent 020 — Priority Router (process_live_feed_events — scoring queue, every 1 min)
- Agent 021 — Velocity Monitor (monitor_signal_velocity — agents queue, every 5 min)
- Agent 022 — Dead Signal Resurrector (run_dead_signal_resurrector — agents queue, every 30 min)
- Agent 067 — Executive Behaviour support (trigger_linkedin_lookup — agents queue, on-demand)

---

*Last updated: Phase 8B — March 2026**
*Next update: Phase 9 completion**

---

## Phase 6 — What Was Built

Phase 6 trains all 34 × 3 = 102 mandate probability models and implements all 10 ML enhancements.
This is the core intelligence layer. All scoring is now ML-driven — no more rule-based weights.

### Key Files Added in Phase 6

**ML Models (`backend/app/ml/`)**
- `bayesian_engine.py` — XGBoost + Optuna per practice area × 3 horizons. `CalibratedClassifierCV(method='isotonic')` for probability calibration. Optimal threshold per horizon via PR curve. `load_all_engines()` called at API startup — zero cold-start.
- `transformer_scorer.py` — `MandateTransformer`: PyTorch multi-head attention (4 layers, 8 heads, d_model=128) with `LearnedPositionalEncoding` and `GlobalAttentionPooling`. Shared encoder → 3 horizon heads (multi-task). `TransformerScorer` inference wrapper.
- `orchestrator.py` — `MandateOrchestrator`: routes each practice area to best model. Transformer takes over ONLY when it beats Bayesian by ≥ 3 F1 points on holdout. `get_orchestrator()` singleton.
- `velocity_scorer.py` — Rate of change over 7-day window. Aggregate via top-5 mean. `flag_high_velocity_companies()` triggers BD alerts.
- `graph_features.py` — NetworkX director interlock graph from MongoDB. `graph_centrality` + `peer_distress_score` features. MongoDB async helpers for node/edge upserts.
- `active_learning.py` — Identifies companies with 30d probability in [0.4, 0.6]. Queues for priority scraping (not human review).
- `cooccurrence.py` — Apriori (mlxtend) on mandate event baskets. min_support=0.05, min_lift=1.5, max 200 rules stored.
- `sector_weights.py` — Mutual information calibration per sector. Cap at 3× multiplier. `compute_aggregate_multiplier()` → `sector_weight_multiplier` feature column.
- `counterfactuals.py` — SHAP `TreeExplainer` (1000× faster than KernelExplainer). Only actionable features exposed. Top 3 counterfactuals per company.
- `cross_jurisdiction.py` — Propagation graph in MongoDB. Decay: subsidiary=0.85, peer=0.40, competitor=0.25. Convergence formula for aggregate feature.
- `anomaly_detector.py` — Symmetric autoencoder (bottleneck d=16). Trained on CLEAN companies only. Threshold = mean + 2σ reconstruction error. Softcapped z-score output.
- `temporal_decay.py` — Exponential decay: `w = base_weight × exp(-λt)`. Lambda grid search [0.002…0.20]. Floor: λ≥0.002 (half-life ≥ 7 days). Convergence formula for category aggregates.

**Training Pipeline (`backend/app/training/`)**
- `train_all.py` — Full Azure batch pipeline: build datasets → train all 34 practice areas → anomaly detector → co-occurrence mining → sector weight calibration → upload to DO Spaces → flush model_registry.
- `dataset_builder.py` — Pulls `company_features` + `mandate_labels` from PostgreSQL. Hard holdout: last 6 months. Builds sequence tensors for transformer.
- `model_registry.py` — Records training results, active model selection, F1 scores. Flushed to `model_registry` table. Loaded by Orchestrator at startup.
- `spaces_uploader.py` — boto3 upload/download to `oracle-models` bucket on DO Spaces. Versioned by timestamp.

**Azure job (`azure/training/azure_job.py`)**
- Submits `train_all.py` as Azure ML command job. MLflow autologging. Environment: Python 3.12 + all ML deps. `--wait` flag for CI blocking.

**Celery Tasks (`backend/app/tasks/phase6_tasks.py`)**
- `agents.refresh_model_orchestrator` (Agent 023) — Hot-reload orchestrator from DB every 6h
- `agents.run_anomaly_escalation` (Agent 024) — Daily: escalate high anomaly_score companies
- `agents.clean_stale_scores` (Agent 025) — Weekly: purge scoring_results older than 90d
- `agents.update_sector_baseline` (Agent 026) — Monthly: deferred to Azure training
- `agents.run_ccaa_cascade` (Agent 027) — Daily: cascade class actions + securities + employment on new CCAA filings
- `scoring.score_company_batch` — Score N companies, store results in scoring_results
- `agents.run_active_learning` — Weekly: identify uncertain companies → active_learning_queue
- `agents.seed_decay_config` — One-time: seed signal_decay_config with default lambdas

**Database (`backend/alembic/versions/0006_phase6_ml.py`)**
- `model_registry` — Active model per practice area + F1 scores
- `scoring_results` — 34×3 matrix per company per day + velocity + anomaly
- `signal_rules` — Apriori co-occurrence rules (practice_area, antecedents, support, confidence, lift)
- `sector_signal_weights` — Per-sector signal multipliers
- `scoring_explanations` — SHAP counterfactuals for high-scoring companies
- `signal_decay_config` — Lambda per signal type (default priors, replaced by calibration)
- `active_learning_queue` — Companies flagged for priority signal collection

**Tests (`backend/tests/ml/test_phase6_ml.py`)**
- 34 practice area count assertion
- Output matrix is exactly 34×3
- Probabilities clamped to [0.001, 0.999]
- Transformer architecture output shape
- Velocity clamp + sign tests
- Temporal decay half-life formula
- Anomaly detector safe fallback when unloaded
- Co-occurrence transaction matrix shape
- Cross-jurisdiction propagation decay ordering
- Orchestrator bayesian default + F1 threshold enforcement
- All 8 Celery tasks registered
- Migration file exists and is valid Python

### Agents Activated in Phase 6
- Agent 023 — Model Selector (`agents.refresh_model_orchestrator` — agents queue, every 6h)
- Agent 024 — Anomaly Escalation (`agents.run_anomaly_escalation` — agents queue, daily)
- Agent 025 — Score Decay (`agents.clean_stale_scores` — agents queue, weekly)
- Agent 026 — Sector Baseline (`agents.update_sector_baseline` — agents queue, monthly)
- Agent 027 — CCAA Cascade (`agents.run_ccaa_cascade` — agents queue, daily)

---

## Phase 7 — What Was Built

Phase 7 exposes the 34×3 mandate probability matrix as an authenticated REST API with
Redis caching, SHAP explainability, batch scoring, fuzzy company search, signal feed,
and practice area trend analytics.

### Performance Fix — `score_company_batch`

**File:** `backend/app/tasks/phase6_tasks.py`

Replaced N+1 DB loop with a three-phase bulk pattern:
- **Phase A** — One `SELECT DISTINCT ON (company_id)` to fetch all features for the batch
- **Phase B** — In-memory ML scoring loop (zero DB I/O)
- **Phase C** — Single `executemany` INSERT for all results

50-company batch: 100 DB round-trips → 2.

### Key Files Added in Phase 7

**Scoring Service (`backend/app/services/scoring_service.py`)**
- `get_company_score(company_id, db)` — Redis cache key `score:{id}:{YYYY-MM-DD}`, TTL 6h → DB fallback
- `get_batch_scores(company_ids, practice_areas, db)` — cache-aware bulk retrieval (max 50)
- `get_company_explain(company_id, db)` — top 5 SHAP counterfactuals from `scoring_explanations` table
- `invalidate_score_cache(company_id)` — deletes today's cache key; called by live feed processor after new signal ingestion

**Route Files (`backend/app/routes/`)**
- `scores.py` — prefix `/v1/scores`, tags `["scores"]`
  - `GET /{company_id}` → `ScoreResponse` (company_id, company_name, scored_at, scores dict[str, HorizonScores], velocity_score, anomaly_score, confidence, top_signals, model_versions)
  - `GET /{company_id}/explain` → `list[ExplainItem]` (practice_area, horizon, score, top_shap_features, counterfactuals, base_value, explained_at)
  - `POST /batch` → `list[dict | None]` — max 50 company_ids; optional `practice_areas` filter; 422 if >50
  - 404 detail: `"No scores found for company {id}. Scoring may be pending."`
- `companies.py` — prefix `/v1/companies`, tags `["companies"]`
  - `GET /search?q=` — rapidfuzz WRatio, score_cutoff=60, aliases cached 1h under `companies:aliases:v1`
  - `GET /{company_id}` — company profile + latest `company_features` row, cached 1h under `company:{id}:profile`
- `signals.py` — prefix `/v1/signals`, tags `["signals"]`
  - `GET /{company_id}` — last 90 days from `signal_records`, optional `signal_type` filter, limit 1–200
- `trends.py` — prefix `/v1/trends`, tags `["trends"]`
  - `GET /practice_areas` — signal counts per `practice_area_hints` over 7/30/90 days, cached 1h under `trends:practice_areas:v1`

**Database (`backend/alembic/versions/0007_phase7_api.py`)**
- `api_request_log` — id (BIGSERIAL), endpoint VARCHAR(200), company_id (nullable FK → companies.id),
  response_time_ms FLOAT, user_id INT, status_code INT, created_at TIMESTAMPTZ
- Indexes: `ix_api_request_log_endpoint`, `ix_api_request_log_created_at`, `ix_api_request_log_company_id`

**main.py Updates**
- Registers all 4 Phase 7 routers under `/api` prefix
- Orchestrator warm-up in lifespan startup — non-blocking; logs warning if models not yet downloaded
- `GET /api/health` now includes `ml_ready: bool` and `"ml": "ready" | "not_loaded"` in components dict

**Tests (`backend/tests/test_phase7_api.py`)**
15 tests: schema field validation, 404 for unknown company, 401 for unauthenticated requests,
batch 422 for >50 ids, cache invalidation key format, bulk-fetch assertion (execute called
exactly 2×), missing-features increments failed count, explain endpoint, trends endpoint.

### Agent Activated in Phase 7
- Agent 028 — Rate Limit Enforcer (operates via middleware; no new Celery task)

---

## Phase 8A — What Was Built

Phase 8A delivers a functional React frontend wired to the Phase 7 API — navigable, authenticated,
and data-driven. This is the working MVP UI; visual polish (ConstructLex Pro design system) comes in Phase 8B.

### Frontend Stack
React 18 + Vite + Zustand + Axios (custom client) + Recharts. All dependencies were already
present in `frontend/package.json`.

### Key Files Added in Phase 8A

**API Layer (`frontend/src/api/client.js`)**
- Axios instance — base URL from `VITE_API_URL` env var
- JWT request interceptor: attaches `Authorization: Bearer {token}` from Zustand auth store
- 401 response interceptor: clears auth store → redirects to `/login`
- Exported endpoint groups: `scores` (get, explain, batch), `companies` (search, get), `signals` (list), `trends` (practiceAreas)

**Zustand Stores (`frontend/src/stores/`)**
- `auth.js` — state: `token`, `user`, `error`; actions: `login(email, pw)` (stores token in sessionStorage), `logout()` (clears + redirects), `loadUser()` (calls `/auth/me`)
- `scores.js` — state: `Map<id, {data, fetchedAt}>`, stale threshold 6h; actions: `fetchScore(id)`, `fetchBatch(ids)`, `getScore(id)`, `isLoading(id)`, `getError(id)`

**Pages (`frontend/src/pages/`)**
- `LoginPage.jsx` — email/password form → `useAuthStore.login()`
- `DashboardPage.jsx` — TrendCharts + navigation links to search and signals
- `SearchPage.jsx` — fuzzy company search input → results list → navigate to company detail
- `CompanyDetailPage.jsx` — company profile stats + tab view (ScoreMatrix / SignalFeed) + link to `/explain`
- `ExplainPage.jsx` — SHAP counterfactuals grouped by practice area
- `SignalsFeedPage.jsx` — signal feed filtered by company ID
- `admin/ScrapersAdminPage.jsx` — scraper health table (admin only)
- `admin/UsersAdminPage.jsx` — user management table (admin only)

**Components (`frontend/src/components/`)**
- `ScoreMatrix.jsx` — 34×3 table sorted by 30d score DESC; cell color: white (0.0) → teal #0C9182 (1.0) via RGB interpolation; click row → `navigate('/companies/${companyId}')`
- `SignalFeed.jsx` — paginated list (PAGE_SIZE=20), `signal_type` filter dropdown, ConfidenceBadge with color-coded percentage
- `TrendCharts.jsx` — Recharts `BarChart` with count_7d/30d/90d bars per practice area (top 20, angled X labels)
- `PrivateRoute.jsx` — reads `token` from `useAuthStore`; redirects to `/login` if absent; `adminOnly` prop redirects non-admins to `/dashboard`

**`frontend/src/App.jsx`** — React Router v6 with all 8 routes wrapped in `<PrivateRoute>` where required; `useEffect` calls `loadUser()` on mount when token present

**`frontend/.env.example`** — added `VITE_API_URL=http://localhost:8000`

### Route Map

| URL | Component | Auth |
|-----|-----------|------|
| `/login` | `LoginPage` | Public |
| `/dashboard` | `DashboardPage` | Private |
| `/companies/:id` | `CompanyDetailPage` | Private |
| `/companies/:id/explain` | `ExplainPage` | Private |
| `/search` | `SearchPage` | Private |
| `/signals` | `SignalsFeedPage` | Private |
| `/admin/scrapers` | `ScrapersAdminPage` | Admin only |
| `/admin/users` | `UsersAdminPage` | Admin only |


---

## Phase 8B — What Was Built

Phase 8B applies the ConstructLex Pro design system to every Phase 8A component. The functional frontend becomes a production-grade, brand-consistent UI. No routing changes, no new API endpoints except the top-velocity query for the dashboard.

### Design System Applied

**CSS tokens (defined once in `src/styles/design-system.css`, consumed everywhere via `var()`):**
- Background: `#F8F7F4` (warm off-white)
- Text: `#1A1A2E` / `#555566` / `#8888AA` (three tiers)
- Accent: `#0C9182` → `#059669` gradient, dark `#065F5B`
- Score heatmap: 5 bands (`#F0FAFA` → `#A7D9D4` → `#4DB8B0` → `#0C9182` → `#065F5B`)
- Typography: Cormorant Garamond (display/headings) + Plus Jakarta Sans (body) + JetBrains Mono (data/scores)
- Skeleton shimmer animation defined in CSS — no JS

### Key Files Added / Replaced in Phase 8B

**Design System**
- `frontend/src/styles/design-system.css` — All CSS custom properties, base reset, skeleton keyframe, scrollbar styling
- `frontend/index.html` — Google Fonts preload for all 3 typefaces

**New Layout**
- `frontend/src/components/layout/Sidebar.jsx` — Fixed 240px sidebar, collapsible to 64px icon-only, active route indicator, admin section, firm logo placeholder, sign-out button
- `frontend/src/components/layout/AppShell.jsx` — Wraps sidebar + main content. Used by all authenticated pages (not LoginPage).

**New Shared Components**
- `frontend/src/components/Skeleton.jsx` — 6 skeleton variants: `Skeleton`, `SkeletonText`, `SkeletonCard`, `SkeletonRow`, `SkeletonTable`, `SkeletonCompanyHeader`. No spinners anywhere.
- `frontend/src/components/Sparkline.jsx` — Inline SVG 7-day trend line. `viewBox="0 0 80 24"`, normalized to series min/max, area fill + end dot, colour matched to score heatmap.
- `frontend/src/components/VelocityBadge.jsx` — Rising ↑ / Falling ↓ / Flat — badge. Green for rising, muted for falling.

**Replaced Components (Phase 8A → 8B)**
- `ScoreMatrix.jsx` — 5-band heatmap (was single RGB interpolation), Cormorant Garamond PA labels, sparklines column (optional), contrast-safe text (white text above 70%, dark below)
- `SignalFeed.jsx` — Colour-coded confidence badges (green/amber/red), border-left accent per signal card, skeleton loading state, empty state with icon
- `TrendCharts.jsx` — ConstructLex teal palette on Recharts BarChart, custom styled tooltip

**Replaced Pages (Phase 8A → 8B)**
- `LoginPage.jsx` — Split layout: left brand panel (teal gradient + italic quote) + right form. No AppShell.
- `DashboardPage.jsx` — Top 20 velocity companies table (calls `/v1/scores/top-velocity`) + trend charts. Skeleton loading.
- `SearchPage.jsx` — Skeleton loading list, branded empty state, focus-glow on input.
- `CompanyDetailPage.jsx` — VelocityBadge + anomaly flag in header. Skeleton for matrix. SHAP link button.
- `ExplainPage.jsx` — SHAP bar charts (inline CSS bars), green counterfactual cards.
- `SignalsFeedPage.jsx` — Global feed with limit switcher (50/100/200).
- `ScrapersAdminPage.jsx` — Status dot (green/amber/red), reliability % in heat-coloured mono, auto-refresh every 60s.
- `UsersAdminPage.jsx` — Role badges per colour tier (admin=amber, partner=teal, associate/readonly=grey).

**Updated**
- `frontend/src/App.jsx` — Imports `./styles/design-system.css`. Routes unchanged.
- `frontend/src/api/client.js` — Adds `scores.topVelocity(limit)` calling `GET /api/v1/scores/top-velocity`

**Backend addition (`backend/app/routes/scores.py`)**
- Add `GET /top-velocity?limit=N` route BEFORE `/{company_id}` to avoid path collision
- SQL: `DISTINCT ON (company_id)` latest scoring_results → sort by velocity DESC
- Cache: 15-min TTL under `top_velocity:{limit}`
- Auth: `require_partner`
- Instructions in `backend/app/routes/scores_8b_addition.py`

### Agents Activated in Phase 8B
- Agent 029 — Dashboard Freshness (monitors top-velocity cache staleness — no new Celery task; operates via existing cache TTL)

*Last updated: Phase 12 — March 2026*
*All phases complete.*

---

## Phase 12 — What Was Built

Phase 12 closes the post-launch optimization loop: weekly usage analytics, ML score quality monitoring, human signal weight overrides, targeted Azure ML retraining, and an admin optimization dashboard.

### Key Files Added in Phase 12

**Services**
- `backend/app/services/analytics_service.py` — `compute_weekly_usage_report()`: pulls `api_request_log`, computes p50/p95, top companies, cache hit rate, stores in `usage_reports`, delivers via Slack webhook or structlog. `get_perf_report()` for on-demand latency analysis.
- `backend/app/services/score_quality.py` — `compute_score_quality_report()`: pulls `prediction_accuracy_log`, computes per-practice-area precision/recall, identifies worst 5, checks training data volume (`mandate_labels`), stores in `score_quality_reports`, writes `backend/reports/score_quality_{date}.md`.

**ML Extensions**
- `backend/app/ml/sector_weights.py` — New: `recalibrate_from_confirmations(db)` (re-runs MI calibration on 30 days of confirmed mandates, updates `sector_signal_weights`), `refresh_cooccurrence_rules(db)` wrapping Apriori, `load_human_overrides_from_cache()`, `compute_aggregate_multiplier()` extended with `human_overrides` parameter (human wins).
- `backend/app/ml/cooccurrence.py` — New: `refresh_rules(db)` re-mines Apriori rules from `mandate_confirmations` × `signal_records` and replaces `signal_rules` table entries.

**Azure**
- `azure/training/azure_job.py` — New `--practice-areas` CLI flag for targeted practice-area retraining. `submit_training_job(practice_areas=[...])` passes comma-separated list to `train_all.py`.

**API Routes (`backend/app/routes/optimization.py`)**
- Prefix `/v1/optimization`, tags `["optimization"]`
- `GET /usage-report` → latest `usage_reports` row (require_partner)
- `GET /score-quality` → latest `score_quality_reports` row (require_partner)
- `GET /perf-report?days=7` → p50/p95/p99 by endpoint sorted by p95 DESC; `needs_attention: true` if p95 > 300ms (require_partner)
- `GET /signal-overrides` → list active `signal_weight_overrides` (require_partner)
- `POST /signal-override` → create override, deactivates existing pair, invalidates Redis cache (require_partner)
- `DELETE /signal-override/{id}` → deactivate override, invalidates Redis cache (require_partner)

**Celery Tasks (`backend/app/tasks/phase12_tasks.py`)**
- `agents.compute_usage_report` — Agent 033, weekly Monday 08:00 UTC (agents queue)
- `agents.recalibrate_signal_weights` — Agent 034, monthly 1st 02:00 UTC (agents queue)
- `agents.check_retrain_trigger` — Agent 035, weekly Sunday 03:00 UTC (agents queue)

**Database (`backend/alembic/versions/0009_phase12_optimization.py`)**
- `usage_reports` — weekly snapshots (top_companies JSONB, endpoint_breakdown JSONB, p50/p95, cache_hit_rate)
- `score_quality_reports` — per-practice-area accuracy summaries (summary JSONB, worst_five JSONB)
- `signal_weight_overrides` — human BD team multipliers (0.01–5.0) per signal_type × practice_area; human override wins over ML weight
- `retrain_submissions` — records of Azure ML retraining jobs submitted by Agent 035

**Frontend**
- `frontend/src/pages/admin/OptimizationPage.jsx` — Route `/admin/optimization` (admin only). Three sections: Usage Report (top companies, p95, cache hit rate), Score Quality (34-row table; worst 5 in amber; low-data flags), Signal Overrides (active list + inline create/remove form). Skeleton loading throughout.
- `frontend/src/api/client.js` — Added `optimization` endpoint group (6 methods). All endpoint groups attached to default export.
- `frontend/src/App.jsx` — Added `/admin/optimization` route.
- `frontend/src/components/layout/Sidebar.jsx` — Added "Optimization" nav item to admin section.

**Config (`backend/app/config.py`)**
- `optimization_report_retention_weeks: int = 52`
- `retrain_drift_threshold: float = 0.10`

**Tests (`backend/tests/test_phase12_optimization.py`)**
- 26 tests: migration validity, 4-table check, config settings, analytics service, score quality (worst-five logic, markdown writer), sector weights override integration, cooccurrence stub, Azure job signature, 3 Celery tasks registered, beat schedule correctness, override Pydantic model validation, 34-practice-area count, reports/.gitkeep.

### Agents Activated in Phase 12
- Agent 033 — Usage Analytics (`agents.compute_usage_report` — agents queue, weekly Monday 08:00 UTC)
- Agent 034 — Signal Weight Recalibration (`agents.recalibrate_signal_weights` — agents queue, monthly 1st 02:00 UTC)
- Agent 035 — Retraining Trigger (`agents.check_retrain_trigger` — agents queue, weekly Sunday 03:00 UTC)

---

## Known Limitations

1. **Phase 9–11 dependencies**: Phase 12 analytics services (`score_quality.py`, `check_retrain_trigger`) gracefully degrade when `prediction_accuracy_log`, `mandate_confirmations`, and `model_drift_alerts` tables don't exist (Phase 9 not yet implemented). They log warnings and return empty results rather than crashing.
2. **Single-tenant only**: Multi-tenant architecture is designed but not activated (`multi_tenant_enabled=False`). Each new law firm requires a separate deployment.
3. **English-only NLP**: French-language filings (SEDAR Québec) are out of scope. No bilingual signal processing.
4. **Azure ML credentials required for retraining**: Agent 035 `check_retrain_trigger` will log a warning and record a dry-run job ID if `AZURE_SUBSCRIPTION_ID` / `AZURE_RESOURCE_GROUP` / `AZURE_WORKSPACE_NAME` env vars are not set.
5. **p95 threshold is static**: The 300ms "needs_attention" flag in `/perf-report` is hardcoded. High-variance endpoints (batch scoring) may always flag amber.
6. **Score quality recall not computed**: Recall requires knowing all real mandates that occurred — this would require complete mandate confirmation coverage (Phase 9). Currently only precision and avg lead days are populated.
7. **GraphSAGE deferred**: Phase 6 used NetworkX centrality for the director interlock graph. PyTorch Geometric GraphSAGE was deferred from Phase 6 and has not been implemented.

---

## Recommended Next Features

1. **Email digest**: Weekly usage report delivered via SMTP (not just Slack). Add `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `REPORT_EMAIL_TO` env vars.
2. **Multi-tenant support**: Activate `multi_tenant_enabled` flag. Each firm gets isolated DB schema, separate JWT namespace, and Vercel deployment.
3. **Mobile app / push alerts**: React Native app with push notifications when a watched company's score crosses a threshold.
4. **API key access**: Allow law firm clients to query the scoring API via API keys (not JWT). Add `api_keys` table with rate limits per key.
5. **Slack BD alerts**: When a company's 30d score crosses 0.7, push a Slack alert to the BD partner's channel with top signals and SHAP explanation.
6. **GraphSAGE upgrade**: Replace NetworkX in `graph_features.py` with PyTorch Geometric GraphSAGE for richer director interlock embeddings.
7. **Practice area filtering**: Let partners subscribe to only the practice areas they handle. Reduces noise in the ScoreMatrix.
8. **Automatic CLAUDE.md sync**: On each phase completion, auto-update CLAUDE.md via a CI step rather than manual Agent update.
9. **Prometheus + Grafana dashboards**: The `/api/metrics` endpoint (Phase 10) enables full Prometheus scraping. Wire to Grafana for real-time dashboards visible to the BD team.
10. **Feedback labelling UI**: Partners can label ORACLE predictions as correct/incorrect directly from the ScoreMatrix, feeding the Phase 9 accuracy tracker without needing to go to the Feedback page.
