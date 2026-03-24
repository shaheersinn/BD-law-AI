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
| 1C — Scraper Performance | ⏳ PENDING | — |
| 2 — Feature Engineering | ⏳ PENDING | — |
| 3 — Ground Truth | ✅ COMPLETE | March 2026 |
| 4 — LLM Training (Groq only) | ✅ COMPLETE | March 2026 |
| 5 — Live Feeds | ✅ COMPLETE | March 2026 |
| 6 — ML Training + 10 Enhancements | ⏳ NEXT | — |
| 7 — Scoring API | ⏳ PENDING | — |
| 8A — Functional Frontend | ⏳ PENDING | — |
| 8B — Production UI (ConstructLex) | ⏳ PENDING | — |
| 9 — Feedback Loop | ⏳ PENDING | — |
| 10 — Testing & Hardening | ⏳ PENDING | — |
| 11 — Deployment | ⏳ PENDING | — |
| 12 — Post-Launch Optimization | ⏳ PENDING | — |

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

*Last updated: Phase 5 — March 2026*
*Next update: Phase 6 completion*
