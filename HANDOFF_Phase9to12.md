# ORACLE — Handoff Brief: Phases 9–12

> READ THIS BEFORE CLAUDE.md.
> Written at the end of Phase 8B.
> Phases 0–8B are complete. The app is functional and production-styled.
> Your job is to complete the final four phases: Feedback Loop, Testing & Hardening, Deployment, and Post-Launch Optimization.

---

## Current State

| Phase | Status |
|-------|--------|
| 0–8B  | ✅ COMPLETE |
| 9 — Feedback Loop | ⏳ NEXT — start here |
| 10 — Testing & Hardening | ⏳ PENDING |
| 11 — Deployment | ⏳ PENDING |
| 12 — Post-Launch Optimization | ⏳ PENDING |

---

## What Exists (do not rebuild)

The codebase is production-quality. Do not re-architect. Do not change the tech stack. Read CLAUDE.md in full before touching any file.

**Backend:** FastAPI + PostgreSQL + MongoDB + Redis + Celery. All async. All tested.
**ML layer:** 34×3 BayesianEngine + TransformerScorer + Orchestrator. Trained via Azure.
**Frontend:** React 18 + Vite + ConstructLex Pro design system. All 8 pages functional.
**Infrastructure:** DO App Platform (tor1) + Vercel frontend + GitHub Actions CI/CD + DO Spaces models.

---

## Per-Phase Build Protocol (mandatory, no exceptions)

Before writing any code for each phase:
1. Pre-phase web research (mandatory — research best practices for that phase's domain)
2. Read all research results and incorporate into design
3. Read CLAUDE.md in full for standing rules
4. Write code
5. Self-audit: ruff + mypy + bandit + logic check
6. Fix all issues
7. pytest — minimum 70% coverage for new code
8. Update CLAUDE.md phase status table
9. Deliver ZIP + Word document

---

## Phase 9 — Feedback Loop

**Goal:** Close the loop between ORACLE predictions and real-world mandate outcomes. When a mandate is confirmed (from news, CanLII, law firm announcements), record it against the prior prediction and use it to improve future scoring.

**What to build:**

**1. Mandate Confirmation Service** (`app/services/mandate_confirmation.py`)
- `confirm_mandate(company_id, practice_area, confirmed_at, source, evidence_url)` — writes to `mandate_confirmations` table
- Cross-references with prior scoring_results to compute `prediction_lead_days` (how many days before the mandate ORACLE had a score > 0.5)
- Updates `mandate_labels` with `confirmed_at` and `confirmation_source`

**2. Prediction Accuracy Tracker** (`app/services/accuracy_tracker.py`)
- For each confirmed mandate: find the highest scoring_results row from 30/60/90 days prior
- Compute: true positive (score > threshold at correct horizon), false negative, lead time
- Write to `prediction_accuracy_log` table: company_id, practice_area, horizon, predicted_score, was_correct, lead_days, confirmed_at
- Weekly Celery task: `agents.compute_prediction_accuracy` (Agent 030 — Active Learning)

**3. Drift Detector** (`app/services/drift_detector.py`)
- Agent 031 — runs weekly
- Compares rolling 30-day prediction accuracy vs prior 30-day baseline per practice area
- If accuracy drops > 10 percentage points: flag practice area in `model_drift_alerts` table
- Triggers orchestrator re-evaluation for flagged practice areas
- Uses Kolmogorov-Smirnov test on score distributions (before vs after window)

**4. Mandate Confirmation Hunter** (`app/services/confirmation_hunter.py`)
- Agent 032 — runs daily
- Scrapes law firm deal announcements, CanLII new filings, SEDAR legal contingency disclosures
- Attempts to match confirmed mandates to companies in ORACLE's company table (EntityResolver)
- Auto-generates mandate_confirmations records with `confirmation_source = "auto_detected"`
- Human review flag set to True for auto-detected (partner must confirm before counting in accuracy)

**5. Feedback API endpoints** (add to `app/routes/feedback.py`)
- `POST /api/v1/feedback/mandate` — partner manually confirms a mandate (requires require_partner)
  Body: `{company_id, practice_area, confirmed_at, source, notes}`
- `GET /api/v1/feedback/accuracy` — prediction accuracy summary per practice area
- `GET /api/v1/feedback/drift` — current model drift alerts

**6. New migration** `0008_phase9_feedback.py`
- `mandate_confirmations`: id, company_id, practice_area, confirmed_at, confirmation_source, evidence_url, is_auto_detected, reviewed_by_user_id, created_at
- `prediction_accuracy_log`: id, company_id, practice_area, horizon, predicted_score, threshold_used, was_correct, lead_days, confirmed_at, logged_at
- `model_drift_alerts`: id, practice_area, detected_at, accuracy_before, accuracy_after, delta, status (open/acknowledged/resolved)

**7. Feedback UI** (`frontend/src/pages/FeedbackPage.jsx`)
- Route: `/feedback` (require_partner)
- Section 1: "Confirm a Mandate" form — company search + practice area dropdown + date picker
- Section 2: Accuracy table — per practice area: precision, recall, avg lead time (last 90 days)
- Section 3: Drift alerts — any flagged practice areas with accuracy delta
- Add to Sidebar.jsx nav items

**New tests:** `tests/test_phase9_feedback.py`
- Mandate confirmation writes to both tables
- Drift detector correctly identifies 10+ point drop
- Auto-detected confirmations have is_auto_detected=True
- Accuracy log computation is idempotent
- Feedback endpoints return correct schema

**Agents activated:**
- Agent 030 — Active Learning / Accuracy tracker (`agents.compute_prediction_accuracy` — weekly)
- Agent 031 — Drift Detector (`agents.run_drift_detector` — weekly)
- Agent 032 — Mandate Confirmation Hunter (`agents.run_confirmation_hunter` — daily)

---

## Phase 10 — Testing & Hardening

**Goal:** Production-grade test coverage, load testing, security audit, error monitoring, and async architecture fixes.

**What to build:**

**1. Fix asyncio.run() in Celery tasks**
The Phase 6 note flagged this: `asyncio.run()` inside synchronous Celery tasks breaks if called from an already-running event loop. Fix: use a dedicated sync DB session for Celery tasks instead of the async FastAPI session. Create `app/database_sync.py` with a synchronous SQLAlchemy session factory (psycopg2 driver) for use in Celery tasks only. All Celery tasks that currently use `asyncio.run()` should switch to the sync session. Async FastAPI routes keep using the existing async session.

**2. Integration test suite** (`tests/integration/`)
- `test_full_pipeline.py` — end-to-end: inject a known signal → verify company_features updated → verify scoring_results written
- `test_api_auth.py` — all 4 roles attempt all protected endpoints, verify 401/403 correctly
- `test_batch_scoring.py` — batch of 50 companies scores in < 2 seconds (performance assertion)
- `test_cache_invalidation.py` — signal ingestion triggers cache bust for affected company

**3. Load test suite** (`tests/load/locustfile.py`)
- Locust scenarios: /search (50 users), /scores/{id} (200 users), /scores/batch (20 users)
- Assert: p95 < 200ms for single score, p95 < 2s for batch 50
- Run: `locust -f tests/load/locustfile.py --headless -u 200 -r 20 --run-time 60s`

**4. Security hardening**
- Run `bandit -r app/ -ll` — fix all medium+ severity findings
- Add `Content-Security-Policy` header in middleware
- Add `X-Content-Type-Options: nosniff` and `X-Frame-Options: DENY` headers
- Verify rate limiter correctly blocks 429 after threshold
- Verify JWT expiry enforced (no tokens older than 24h accepted)
- Run OWASP ZAP scan against staging — fix any high findings

**5. Error monitoring** (Sentry integration)
- Add `sentry-sdk[fastapi]` to requirements.txt
- Initialize in `app/main.py` lifespan if `SENTRY_DSN` env var is set
- Capture unhandled exceptions in Celery tasks via `sentry_sdk.capture_exception()`
- Add `SENTRY_DSN` to `.env.example` (already in env var list)

**6. Observability**
- Add `/api/metrics` endpoint: Prometheus-format counters for requests/s, scoring latency p50/p95, cache hit rate, scraper health counts
- Add `prometheus-client` to requirements.txt
- DO App Platform can scrape this endpoint

**7. Frontend hardening**
- Add React Error Boundary wrapping all routes (catches JS runtime errors, shows graceful error page)
- Add `retry` logic to Axios client (3 retries with 500ms backoff for 5xx responses)
- Verify all pages show skeleton loading (not blank) on slow API

**8. GraphSAGE upgrade** (optional — only if time permits)
- Replace NetworkX centrality in `graph_features.py` with PyTorch Geometric GraphSAGE
- Only proceed if `torch-geometric` installs cleanly in the Azure training environment
- This was deferred from Phase 6

**New tests:** minimum 70% coverage on all new code in this phase.

---

## Phase 11 — Deployment

**Goal:** Production deployment on DigitalOcean App Platform (tor1) + Vercel. SSL, domain, monitoring, and go-live checklist.

**What to build:**

**1. Pre-deployment checklist** (create `docs/deployment_checklist.md`)
- [ ] `SECRET_KEY` changed from default (minimum 64 chars, random)
- [ ] Default admin/partner credentials changed
- [ ] All API keys set in DO App Platform environment variables
- [ ] `ENVIRONMENT=production` set
- [ ] `SENTRY_DSN` set
- [ ] `SPACES_KEY` + `SPACES_SECRET` set (model artifacts)
- [ ] Azure ML training job completed successfully
- [ ] `alembic upgrade head` run against production DB
- [ ] `agents.seed_decay_config` Celery task run once
- [ ] Orchestrator loads cleanly (GET /api/health shows ml_ready: true)
- [ ] Canary scraper fires in last 60 minutes
- [ ] Vercel deployment succeeds with `VITE_API_URL` pointing to DO backend

**2. DO App Platform spec** — update `do-app.yaml`
- Verify all 4 services: `api` (FastAPI), `worker` (Celery worker), `beat` (Celery beat), `frontend` (static via Vercel or DO static site)
- Add health check path: `/api/health`
- Add `min_instance_count: 1` for api and worker to prevent cold starts
- Set `instance_size_slug: professional-xs` for worker (ML scoring needs RAM)

**3. Domain configuration**
- Point domain to Vercel (frontend) and DO (backend API)
- Configure CORS in FastAPI to accept the production frontend domain
- Update `ALLOWED_ORIGINS` in `app/config.py` settings

**4. Database migrations in production**
- DO NOT run migrations automatically in CD pipeline
- Create `scripts/run_migrations.sh` — manual trigger, requires `CONFIRM=yes` env var
- Document rollback procedure in `docs/deployment_checklist.md`

**5. GitHub Actions CD update** (`.github/workflows/cd.yml`)
- Deploy to DO App Platform on push to `main` branch
- Run smoke tests after deployment: GET /api/health, GET /api/v1/scores/top-velocity
- Notify on failure (Slack webhook or email)
- Never run migrations automatically — manual only

**6. Monitoring setup**
- Configure DO App Platform alerts: CPU > 80%, memory > 85%, error rate > 5%
- Configure Sentry alerts: new issues, regression issues
- Set up UptimeRobot (free) for external uptime monitoring of /api/health

**7. Backup configuration**
- DO Managed PostgreSQL: enable automated daily backups (7-day retention)
- MongoDB Atlas: verify backup is enabled
- DO Spaces: model artifacts are already versioned (immutable by timestamp)

---

## Phase 12 — Post-Launch Optimization

**Goal:** 30 days post-launch: monitor, tune, and improve based on real usage data.

**What to build:**

**1. Usage analytics** (`app/services/analytics_service.py`)
- Weekly report from `api_request_log`: top companies searched, top practice areas viewed, avg response times, cache hit rate
- Store weekly snapshot in `usage_reports` table
- Email report to admin (via simple SMTP) or log to structlog for manual review

**2. Score quality review**
- Pull last 30 days of `prediction_accuracy_log`
- Identify the 5 worst-performing practice areas (lowest precision)
- For each: check if the training data volume was sufficient (< 50 positives = unreliable)
- Document findings in `reports/score_quality_{date}.md`

**3. Signal weight recalibration**
- Re-run sector weight calibration on 30 days of new confirmed mandate data
- Update `sector_signal_weights` table
- Re-run Apriori co-occurrence mining on expanded mandate event set
- Update `signal_rules` table

**4. Model retraining trigger**
- If any practice area shows F1 drop > 10% on rolling accuracy (from Phase 9 drift detector):
  re-submit Azure training job for that practice area only (not full retrain)
- Add `--practice-areas` flag to `azure/training/azure_job.py` for targeted retraining

**5. Performance tuning**
- Analyse `api_request_log` for slowest endpoints
- If any p95 > 300ms: add DB index or extend cache TTL
- Review Celery task queue depths — if scoring queue > 1000 jobs: add a second worker

**6. BD feedback integration** (partner input session)
- Sit with BD team (or proxy with available user)
- Ask: which companies surprised you? Which signals feel noisy? Which practice areas are most useful?
- Adjust signal weights manually (add `signal_weight_overrides` table for human-set multipliers that override ML-calibrated weights)

**7. CLAUDE.md final update**
- Mark all phases complete
- Document known limitations for future development
- Document recommended next features (e.g. email alerts, mobile app, API keys for firm clients)

---

## Key Rules — Re-read Before Every Phase

- **ML models score. LLMs never score production. Ever.**
- **English only.** No French NLP, no bilingual processing.
- **PostgreSQL** = structured data. **MongoDB** = social/unstructured + corporate graph.
- **ALL DB calls async** (FastAPI). Celery tasks use sync session (`app/database_sync.py` — build in Phase 10).
- **ALL HTTP calls** use httpx (async). Never requests (sync).
- **No bare except.** No print(). No hardcoded secrets. No blocking I/O.
- **Celery:** RedBeat scheduler, `worker_prefetch_multiplier=1`, `task_acks_late=True`.
- **bcrypt** cost factor 12. **JWT** carries only: sub, role, type, iat, exp.
- **Rate limiter** must fail open when Redis is unavailable.
- **Docker** runs as non-root user.
- **Groq API** = Phase 4 training only. Never production.
- **Every phase:** ruff + mypy + bandit + pytest before delivery.
- **Every phase:** pre-phase web research before writing any code.

---

## Environment Variables Reminder

All secrets via `get_settings()`. Never hardcoded. Full list in `.env.example`.
Key production values to set before Phase 11:
- `SECRET_KEY` — change from default
- `SENTRY_DSN` — error monitoring
- `SPACES_KEY` / `SPACES_SECRET` — model artifacts
- `ENVIRONMENT=production`
- `ALLOWED_ORIGINS` — production frontend domain

---

## What Claude Code Should Do First

1. Read HANDOFF.md (this file)
2. Read CLAUDE.md in full
3. Run: `make lint` and `make test` — verify everything still passes before touching Phase 9
4. Fix any lint/test failures before starting Phase 9
5. Pre-phase research on feedback loop patterns and accuracy tracking for ML systems
6. Only then begin Phase 9

---

*Handoff written: March 2026*
*Phases complete: 0, 1, 1B, 1C, 2, 3, 4, 5, 6, 7, 8A, 8B*
*Next phase: 9 — Feedback Loop*
