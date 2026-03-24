# ORACLE — Phase Specifications

> This file contains the complete build specification for every phase.
> Claude Code reads the relevant phase section before starting work on that phase.
> Written during the claude.ai architecture session (March 2026).
> Do not modify phase specs without user approval.

---

## How to Use This File

Before starting any phase:
1. Read the phase section below in full
2. Read CLAUDE.md for all standing rules
3. Run pre-phase web research on the phase's domain
4. Only then write code

After completing any phase:
- Update CLAUDE.md phase status table
- Mark the phase ✅ COMPLETE with date
- Mark the next phase ⏳ NEXT

---

## Phase 1B — Scraper Audit & Validation

**Goal:** Prove that Phase 1 scrapers actually work. No ML, no features — just
instrumentation, health monitoring, and regression safety nets.

**Deliverables (all required):**

**1. Scraper Health API endpoint**
- `GET /api/v1/scrapers/health` — returns all scraper health records from scraper_health table
- `GET /api/v1/scrapers/health/{source_id}` — single scraper detail
- Fields: source_id, is_healthy, last_run_at, last_success_at, consecutive_failures,
  avg_duration_seconds, avg_records_per_run, reliability_score, circuit_breaker_state
- Auth: require_admin or require_partner

**2. Data Quality Validator** (`app/scrapers/audit/data_quality.py`)
- Checks every signal_record for: non-null source_id, valid signal_type,
  confidence_score in [0,1], no duplicate (source_id + source_url + published_at),
  published_at not in the future, signal_value parseable as JSON
- Runs as Celery task `scrapers.run_data_quality_check` daily at 03:00 UTC
- Writes results to new table: `data_quality_runs` (pass_count, fail_count, issues JSON)

**3. Pipeline Smoke Test** (`tests/integration/test_pipeline_smoke.py`)
- End-to-end test with a mock scraper that injects a known signal
- Verifies: signal written to signal_records (PostgreSQL) AND raw_payload written to
  MongoDB oracle_signals collection
- Verifies entity resolver is called and company_id populated if company exists
- Verifies scraper_health record updated after run
- Uses pytest fixtures with real test DB (not mocks) — separate test DB configured
  via TEST_DATABASE_URL env var

**4. Source Reliability Scorecard** (`app/scrapers/audit/scorecard.py`)
- Calculates per-scraper: success_rate (last 30 days), avg_records_per_run,
  p95_duration_seconds, data_freshness_hours (age of newest signal)
- Scores each scraper 0.0–1.0 (reliability_score in scraper_health table)
- Formula: reliability_score = (success_rate × 0.5) + (freshness_score × 0.3)
  + (volume_score × 0.2)
- Runs as Celery task `scrapers.update_reliability_scores` every 6 hours

**5. Canary System** (`app/scrapers/audit/canary.py`)
- CanaryScraper: fake scraper with source_id="canary" that always succeeds
- Injects 1 synthetic signal every 30 minutes with known values
- `GET /api/v1/scrapers/canary/status` — returns whether canary fired in last 60 min
- If canary fails 2 consecutive times → send alert (log ERROR + future: PagerDuty)
- Canary signals are tagged is_canary=True and excluded from ML training

**6. Regression Test Suite** (`tests/scrapers/test_regression.py`)
- For each scraper category: instantiate all scrapers, call health_check(), assert returns bool
- Assert ScraperRegistry.count() >= 69 (regression guard — catches accidental deregistration)
- Assert all 27 law firm scrapers are registered
- Assert migration 0002 exists and is valid Python
- Assert all Celery tasks in scraper_tasks.py are registered in the Celery app

**7. Scraper Dashboard React Component** (`frontend/src/components/ScraperHealth.jsx`)
- Table showing all scrapers: source_name, status (green/yellow/red), last_run, records/run
- Color coding: green = healthy, yellow = consecutive_failures 1-2, red = 3+
- Auto-refreshes every 60 seconds via polling /api/v1/scrapers/health
- Admin/partner only (hidden from readonly role)

**New Alembic migration:** `0003_phase1b_audit.py`
- Tables: `data_quality_runs`, add `is_canary` bool to signal_records

**New env vars:** None required for Phase 1B.

---

## Phase 1C — Scraper Performance Review & Alternative Discovery

**Goal:** Find which scrapers are broken or underperforming after real-world runs.
Add redundancy chains. Manage free-tier API budgets.

**Deliverables:**

**1. Performance Review Report** (auto-generated Markdown + stored in DB)
- Run after 7+ days of Phase 1B data
- Ranks scrapers by reliability_score ascending (worst first)
- For each scraper scoring < 0.6: root cause analysis (rate limited? blocked? schema changed?)
- Output: `reports/scraper_performance_{date}.md`

**2. Redundancy Chain System** (`app/scrapers/redundancy.py`)
- Maps each signal_type to ordered list of scrapers that can produce it
- If primary scraper fails 3 consecutive times → auto-promote secondary
- Example: `filing_material_change` → [sedar_plus, edgar, canada_gazette]
- Config in: `app/scrapers/redundancy_config.py` (explicit, not auto-discovered)

**3. Free-Tier Budget Manager** (extend existing `app/scrapers/budget_manager.py`)
- Track monthly usage per API: Twitter (10k tweets), Alpha Vantage (25/day),
  Proxycurl (10 credits), HIBP (unlimited but rate-limited)
- When budget > 80% consumed: reduce scrape frequency by half
- When budget > 95% consumed: pause scraper until next month
- Dashboard widget showing budget consumption per source

**4. Alternative Source Discovery** (research task, not code)
- For every scraper with reliability_score < 0.5 after Phase 1B:
  identify one alternative free data source
- Document alternatives in: `docs/alternative_sources.md`
- No code written — user decides which alternatives to implement

**5. Playwright Integration** (only if needed)
- If any Tier 1 source (SEDAR+, OSC, Globe) requires JS rendering: implement
  Playwright-based scraper as subclass of BaseScraper
- Base class: `app/scrapers/base_playwright.py` extending BaseScraper
- Use only if HTTP scraping fails — Playwright is last resort (slow, fragile)

---

## Phase 2 — Feature Engineering

**Goal:** Transform raw signal_records into ML-ready feature vectors.
60+ continuous features per company per day.

**Feature categories (implement all):**

**1. Filing Features** (`app/features/filing_features.py`)
- filing_frequency_30d: count of filings in last 30 days
- filing_frequency_delta: change vs prior 30 days (acceleration)
- material_change_count_90d: material change reports in 90 days
- md_a_sentiment_score: MD&A text sentiment (-1 to +1) — stub in Phase 2,
  populated by Phase 4 NLP
- hedging_language_score: count of hedging phrases in MD&A (Phase 4 NLP)
- restatement_flag: binary — any financial restatement in 180 days
- auditor_change_flag: binary — auditor changed in 365 days
- going_concern_flag: binary — going concern note in most recent filing

**2. Legal/Court Features** (`app/features/legal_features.py`)
- active_litigation_count: open court cases found in CanLII
- new_filing_30d: new court filings naming company in 30 days
- regulatory_action_count_90d: enforcement actions in 90 days
- canlii_mention_velocity: rate of change in CanLII mentions
- class_action_proximity: binary — class action filed against same-sector peer

**3. Employment Features** (`app/features/employment_features.py`)
- legal_hire_velocity: rate of new legal/compliance job postings
- exec_departure_count_90d: C-suite departures in 90 days
- layoff_signal_score: mass layoff signals from Job Bank + news
- gc_departure_flag: binary — General Counsel departure detected
- compliance_hire_spike: legal/compliance postings > 2x sector baseline

**4. Market Features** (`app/features/market_features.py`)
- price_decline_90d: stock price % change over 90 days
- volatility_30d: 30-day rolling volatility
- short_interest_ratio: short interest / float
- options_put_call_ratio: 30-day trailing put/call ratio
- volume_anomaly_score: trading volume vs 90-day average
- analyst_downgrade_count_30d: analyst rating changes

**5. NLP Signal Features** (`app/features/nlp/`)
These are STUBS in Phase 2. Populated by Phase 4 NLP models.
- `nlp_features.py`: intent_score (0–1 per practice area),
  named_entity_company_mentions, sentiment_trend_7d
- `mda_diff.py`: semantic diff between current and prior MD&A
- `hedging_detector.py`: count of hedging phrases vs prior period
- All stubs return 0.0 until Phase 4 trains the models

**6. Geographic Features** (`app/features/geo/`)
- `regional_stress.py`: provincial insolvency rate, court volume index
- `google_trends_score.py`: normalised Google Trends spike score for company name
- `macro_cycle.py`: Bank of Canada rate cycle phase (0=easing, 1=tightening),
  sector-specific insolvency leading indicator

**7. Network Features** (`app/features/network_features.py`)
- director_interlocks_count: shared directors with companies in distress
  (from MongoDB corporate graph — stub until Phase 6 Graph population)
- law_firm_shared_counsel: binary — shares counsel with a company in litigation

**Database:**
- New table: `company_features` — one row per company per day
  Columns: company_id, feature_date, plus one float column per feature (60+ cols)
- Alembic migration: `0004_phase2_features.py`
- Populated by Celery task: `features.compute_features` — runs nightly at 01:00 UTC

**New tests:** `tests/features/test_feature_engineering.py`
- Test each feature function with synthetic signal_records
- Assert no NaN/Inf values in output
- Assert all features in [expected_min, expected_max]
- Assert feature computation is idempotent (run twice = same result)

---

## Phase 3 — Ground Truth Pipeline

**Goal:** Build the labeled training dataset. This is the most important phase
for ML quality. Garbage labels = garbage model.

**Architecture: 12 automated validation mechanisms (no partner input)**

**1. Retrospective Backtesting** (`app/ground_truth/retrospective.py`)
- For known public mandates (M&A, class actions, insolvencies from CanLII/news):
  verify ORACLE signals fired 30-90 days before
- Source: CanLII case filing timestamps, SEDAR+ legal contingency disclosures
- Generates positive labels: (company_id, practice_area, mandate_date, signal_ids[])

**2. SEDAR/EDGAR Legal Contingency Miner** (`app/ground_truth/contingency_miner.py`)
- Parses MD&A section "Contingencies" and "Legal Proceedings" from filings
- If new legal proceeding disclosed → positive label for Litigation/Class Actions
- If regulatory investigation disclosed → positive label for Regulatory
- Confidence: 0.95 (disclosed = confirmed)

**3. News Mandate Confirmation Detector** (`app/ground_truth/news_confirmation.py`)
- Monitors news for: "filed lawsuit against", "class action against",
  "received OSFI order", "reached settlement with"
- Matches company name to company_id via EntityResolver
- Generates positive label with mandate_confirmed_at timestamp

**4. CanLII Court Filing Timestamp Validator** (`app/ground_truth/canlii_validator.py`)
- Queries CanLII API for new cases naming company
- Decision date → mandate_confirmed_at
- Cross-references with company_features to verify signals existed before filing

**5–12. Additional mechanisms** (implement as stubs in Phase 3, populated in Phase 6+):
- Enforcement lead-time validation (regulatory action → confirm prior signals)
- M&A announcement retrospective (deal announced → verify M&A signals fired)
- Legal fee proxy disclosure mining (MD&A legal costs increase → prior signals)
- Law firm deal announcement scraping (firm announces client deal → label)
- Survival analysis (Kaplan-Meier — time-to-mandate distribution per signal)
- SCAC cross-validation (securities class action database)
- Synthetic control (comparable companies without events = negative labels)
- Out-of-sample holdout (most recent 6 months reserved, never used in training)

**Label Schema** (`app/models/ground_truth.py`):
```
mandate_labels table:
  company_id, practice_area (enum 34 values), mandate_confirmed_at,
  signal_ids (JSON array), confidence (float), source (enum),
  horizon_actual (int — days from first signal to mandate),
  is_negative_label (bool), label_method (enum 12 values)
```

**Negative label generation** (`app/ground_truth/negative_sampler.py`):
- For each positive label: sample 5 companies in same sector with no mandate
- These become negative labels (target = 0 for that practice area)
- Ratio enforced: 5:1 negative:positive per practice area

**Alembic migration:** `0005_phase3_ground_truth.py`
- Tables: `mandate_labels`, `label_audit_log`

**New tests:** `tests/ground_truth/test_label_generation.py`
- Assert 5:1 negative ratio enforced
- Assert no data leakage (holdout period signals never used as features)
- Assert all 12 label sources produce valid schema

---

## Phase 4 — LLM Training (Groq Only)

**Goal:** Fine-tune lightweight NLP models for legal text classification.
These REPLACE the stub NLP features from Phase 2 with real predictions.

**CRITICAL RULES FOR THIS PHASE:**
- Groq API ONLY. No OpenAI, no Anthropic, no other LLM.
- Models trained here are NEVER used in production scoring. Ever.
- These models produce features that feed the ML models in Phase 6.
- All training runs on Azure credits (batch jobs, not local GPU).

**What to train:**

**1. Practice Area Classifier** (`app/training/practice_area_classifier.py`)
- Input: text snippet (news headline, MD&A paragraph, court filing excerpt)
- Output: probability distribution over 34 practice areas
- Training data: CanLII decisions + law firm blog posts + regulatory announcements
- Model: fine-tuned Legal-BERT or canadian-legal-bert (HuggingFace)
- Training job: Azure ML batch job (`azure/training/practice_area_train.py`)

**2. Intent Detector** (`app/training/intent_detector.py`)
- Input: text snippet
- Output: binary classification — does this text indicate legal/regulatory intent?
- Training data: Refugee Law Lab ML dataset + synthetic negatives from general news
- Model: fine-tuned DistilBERT (smaller, faster inference)

**3. Hedging Language Detector** (`app/training/hedging_detector.py`)
- Input: MD&A paragraph
- Output: hedging_score (0–1) — how much uncertainty/legal hedging language
- Training data: annotated MD&A sections (Groq pseudo-labels on known high/low hedging)
- Model: logistic regression on TF-IDF features (interpretable, fast, good enough)

**4. Pseudo-Label Generator** (`app/training/pseudo_labeler.py`)
- Uses Groq API to pseudo-label unlabeled legal texts at scale
- Prompt template: asks Groq to classify text into practice areas + output JSON
- Quality gate: only accept labels where Groq confidence > 0.8 (from JSON output)
- Rate: 14,400 requests/day free tier — batch overnight
- Output: augmented training dataset for Phase 6 ML models

**Groq Integration** (`app/training/groq_client.py`):
- Model: llama-3.1-70b-versatile (best free-tier model for classification)
- Max concurrent requests: 10 (within free tier limits)
- Exponential backoff on 429
- All requests logged to `groq_usage_log` table for budget tracking

**Azure Batch Job Setup** (`azure/`):
- `azure/training/setup.py` — provisions Azure ML workspace
- `azure/training/submit_job.py` — submits training job with data from Spaces
- `azure/training/download_model.py` — pulls trained model, uploads to DO Spaces
- Jobs run on Standard_DS3_v2 (4 vCPU, 14GB RAM) — within free credits

**Model Storage:**
- All trained model artifacts → DigitalOcean Spaces `/models/phase4/`
- Versioned: `practice_area_v1.pkl`, `intent_v1.pkl`, `hedging_v1.pkl`
- Loaded at API startup via `app/ml/model_loader.py`

**New env vars:** `GROQ_API_KEY`, `AZURE_SUBSCRIPTION_ID`, `AZURE_RESOURCE_GROUP`,
`AZURE_ML_WORKSPACE`, `SPACES_KEY`, `SPACES_SECRET`, `SPACES_BUCKET`

---

## Phase 5 — Live Data Feeds

**Goal:** Priority signals delivered in < 60 seconds. Transform scrapers from
batch (every N hours) to event-driven (as-it-happens).

**Architecture: Redis Streams as event bus**

**1. Priority Signal Router** (`app/services/live_feed.py`)
- Redis Stream: `oracle:live:signals` (key)
- Consumer group: `scoring_consumers`
- Any scraper can push to stream instead of Celery queue for priority signals
- Stream retention: 24 hours (enough for re-processing on failure)

**2. Live-Trigger Sources (these become streaming, not batch):**
- SEDAR+ material change reports → live (poll every 5 minutes)
- OSC enforcement actions → live (RSS, poll every 10 minutes)
- CanLII new decisions → live (poll every 15 minutes)
- News: Globe, FP, Reuters → live (RSS, every 5 minutes)
- SCC decisions → live (RSS, every 30 minutes)
- EDGAR 8-K filings → live (RSS from SEC, every 5 minutes)

**3. Velocity Monitor** (`app/services/velocity_monitor.py`)
- Tracks signal rate per company per practice area over rolling 48-hour window
- If velocity > 2x 30-day baseline → escalate to high-priority queue
- Velocity score stored in company_features as `signal_velocity_score`

**4. LinkedIn On-Demand Trigger** (`app/services/linkedin_trigger.py`)
- When Agent 067 (Executive Behaviour) detects C-suite departure from news:
  trigger LinkedIn Proxycurl lookup for that specific executive
- Conserves Proxycurl credits — only runs on confirmed departure signal
- Max 5 LinkedIn lookups per day (within free credit budget)

**5. Dead Signal Resurrector** (`app/services/resurrector.py`)
- Monitors scrapers that haven't produced signals in > 2× their expected interval
- Triggers immediate re-run and health check
- If scraper is genuinely dead: promotes redundancy chain backup source

**Updated Celery Beat Schedule:**
- Live feed sources: every 5–15 minutes (replace 6-hour batch)
- Batch sources (Stats Canada, Google Trends): keep existing schedule
- Velocity monitor: every 5 minutes
- Dead signal resurrector: every 30 minutes

**New env vars:** None (Redis already configured)

---

## Phase 6 — ML Training + 10 Enhancements

**Goal:** Train all 34 × 3 = 102 scoring models. Implement all 10 enhancements.
This is the core ML phase.

**Model Architecture (from design):**
- Bayesian engine per practice area: works day 1, interpretable, fast
- Transformer temporal attention: earns the right practice area by practice area
  when it beats Bayesian on holdout F1 score
- Orchestrator: selects best model per practice area per inference call

**Base Models** (`app/ml/`):
- `bayesian_engine.py`: XGBoost with Bayesian hyperparameter optimisation (Optuna)
  One model per practice area. Features: all 60+ from Phase 2 + Phase 4 NLP.
  Labels: mandate_labels from Phase 3.
  Output: probability 0–1 for mandate in 30d, 60d, 90d (3 separate models per area)
- `transformer_scorer.py`: PyTorch transformer with temporal attention
  Input: time-series of signal embeddings (30-day window)
  Output: same 3-horizon probabilities

**Training Pipeline** (`app/training/train_all.py`):
- Runs on Azure (batch job, not local)
- For each of 34 practice areas:
  1. Pull features + labels from PostgreSQL
  2. Train Bayesian (XGBoost) with Optuna (100 trials)
  3. Train Transformer (10 epochs)
  4. Evaluate both on holdout (last 6 months, never seen in training)
  5. Save winner to DO Spaces with metadata
  6. Update orchestrator config

**10 Enhancements (implement all in this phase):**

1. **Multi-horizon prediction** — train separate model per horizon (30/60/90d).
   Already in base architecture. Ensure output is matrix not scalar.

2. **Mandate velocity scoring** (`app/ml/velocity_scorer.py`) — rate of change in
   mandate probability over 7 days. Score: (today_prob - 7d_ago_prob) / 7d_ago_prob.
   Stored as velocity_score in scoring_results table.

3. **Corporate graph network** (`app/ml/graph_features.py`) — MongoDB graph of
   director interlocks. GraphSAGE embeddings for network-based features.
   Requires: populate graph from SEDI + corporate registry data first.
   Node: company. Edge: shared director. Feature: graph_centrality, peer_distress_score.

4. **Active learning loop** (`app/ml/active_learning.py`) — model identifies
   companies where prediction confidence is 0.4–0.6 (uncertain).
   These are flagged for priority signal collection (more scraping, not partner review).
   Celery task: runs weekly, updates `active_learning_queue` table.

5. **Signal co-occurrence mining** (`app/ml/cooccurrence.py`) — Apriori algorithm
   on ground truth labels. Find signal combinations that together predict mandates
   better than individually. Output: `signal_rules` table with confidence + lift.

6. **Industry-specific signal weighting** (`app/ml/sector_weights.py`) — per-sector
   multipliers for each signal type. E.g., oil price signal matters 3× more for
   energy companies than tech. Weights stored in `sector_signal_weights` table.
   Calibrated from training data, not manually set.

7. **Counterfactual explainability** (`app/ml/counterfactuals.py`) — for each
   high-score prediction: what would need to change to lower the score below 0.4?
   Uses SHAP TreeExplainer. Output: top 3 counterfactual features per company.
   Stored in `scoring_explanations` table.

8. **Cross-jurisdiction propagation** (`app/ml/cross_jurisdiction.py`) — when a
   US company (EDGAR) has a regulatory event, propagate signal to Canadian subsidiaries
   and peers. Propagation graph maintained in MongoDB.

9. **Anomaly detection** (`app/ml/anomaly_detector.py`) — autoencoder trained on
   normal company feature vectors. High reconstruction error = anomalous.
   anomaly_score stored per company per day. Threshold: > 2 standard deviations.

10. **Temporal decay** (`app/ml/temporal_decay.py`) — each signal type has a half-life
    per practice area. E.g., regulatory filing decays in 90 days; breach news decays in
    30 days; M&A rumour decays in 14 days. Signal weight = base_weight × exp(-λt).
    Decay parameters stored in `signal_decay_config` table, calibrated from training.

**New Alembic migrations:**
- `0006_phase6_ml.py`: scoring_results, signal_rules, sector_signal_weights,
  scoring_explanations, signal_decay_config, active_learning_queue

**New tests:** `tests/ml/test_ml_pipeline.py`
- Assert model file exists in DO Spaces after training
- Assert orchestrator selects correct model per practice area
- Assert output is 34×3 matrix (not scalar)
- Assert velocity score in [-1, 1] range
- Assert SHAP values sum to model output (Shapley consistency)

---

## Phase 7 — Scoring API

**Goal:** Authenticated REST API that returns the 34×3 mandate probability matrix
for any company, with explanations and velocity.

**Endpoints:**

```
GET  /api/v1/scores/{company_id}
  → 34×3 matrix + velocity + anomaly + confidence intervals + top signals

GET  /api/v1/scores/{company_id}/explain
  → SHAP counterfactuals for top 5 highest-scoring practice areas

GET  /api/v1/scores/batch
  Body: {company_ids: [...], practice_areas: [...optional...]}
  → Bulk scores, max 50 companies per request

GET  /api/v1/companies/search?q={name}
  → Fuzzy company search (rapidfuzz against company_aliases)

GET  /api/v1/companies/{company_id}
  → Company profile + current feature values

GET  /api/v1/signals/{company_id}
  → Recent signals for a company (last 90 days)

GET  /api/v1/trends/practice_areas
  → Aggregate signal volume per practice area (last 7/30/90 days)
  → Feeds the dashboard trend charts
```

**Score Response Schema:**
```json
{
  "company_id": 123,
  "company_name": "Shopify Inc.",
  "scored_at": "2026-03-23T10:00:00Z",
  "scores": {
    "ma": {"30d": 0.71, "60d": 0.84, "90d": 0.89},
    "litigation": {"30d": 0.12, "60d": 0.18, "90d": 0.22},
    ... (all 34 practice areas)
  },
  "velocity_score": 0.34,
  "anomaly_score": 0.08,
  "confidence": {"low": 0.67, "high": 0.91},
  "top_signals": [...],
  "model_versions": {"ma": "xgboost_v3", "litigation": "transformer_v1"}
}
```

**Caching:**
- Score results cached in Redis for 6 hours per company
- Cache key: `score:{company_id}:{date}`
- Cache invalidated on new signal ingestion for that company

**Performance targets:**
- Single company score: < 200ms p95 (from cache or fast recompute)
- Batch 50 companies: < 2 seconds p95
- Zero cold-start penalty (models pre-loaded at API startup)

**New Alembic migration:** `0007_phase7_api.py`
- Table: `scoring_results` (company_id, scored_at, scores JSON, velocity, anomaly)
- Table: `api_request_log` (endpoint, company_id, response_time_ms, user_id)

---

## Phase 8A — Functional Frontend

**Goal:** Every feature works. Not beautiful — functional.
ConstructLex Pro design comes in Phase 8B.

**Pages/Routes:**
```
/login                  — JWT login form
/dashboard              — company list with top scores
/companies/:id          — company detail: score matrix + signals
/companies/:id/explain  — SHAP explanation view
/search                 — fuzzy company search
/signals                — recent signals feed
/admin/scrapers         — scraper health dashboard (admin only)
/admin/users            — user management (admin only)
```

**State management:** Zustand (already in package.json)
**HTTP client:** Axios with JWT interceptor (auto-refresh on 401)
**Charts:** Recharts (already in package.json)

**Score matrix component:**
- 34 × 3 table. Color scale: white (0) → teal (1.0)
- Sort by highest 30d score
- Click row → navigate to company detail

**Signal feed component:**
- Paginated list of recent signals (newest first)
- Filter by signal_type, practice_area, company
- Each signal shows: source, signal_text snippet, published_at, confidence badge

**All API calls authenticated.** If token expired → redirect to /login.

---

## Phase 8B — Production UI (ConstructLex Pro Theme)

**Goal:** Apply the ConstructLex Pro design system to all Phase 8A components.

**Design tokens (apply everywhere):**
```css
--background: #F8F7F4
--text-primary: #1A1A2E
--text-secondary: #555566
--accent-primary: #0C9182
--accent-secondary: #059669
--border: #E2E0DA
--surface: #FFFFFF
--surface-hover: #F0EFEC
```

**Typography:**
- Headings: Cormorant Garamond (Google Fonts)
- Body: Plus Jakarta Sans (Google Fonts)
- Monospace (scores, IDs, code): JetBrains Mono (Google Fonts)

**Score heatmap colours:**
- 0.0–0.3: #F0FAFA (near white)
- 0.3–0.5: #A7D9D4 (light teal)
- 0.5–0.7: #4DB8B0 (mid teal)
- 0.7–0.9: #0C9182 (accent-primary)
- 0.9–1.0: #065F5B (dark teal)

**Component polish:**
- Sidebar navigation with firm logo placeholder
- Dashboard: top 20 highest-velocity companies
- Practice area scores: sparkline trend per area (7-day history)
- Signal confidence badges: colour-coded by confidence_score band
- Loading skeletons (not spinners)
- Empty states with contextual messaging

---

## Phase 9 — Feedback Loop

**Goal:** System improves automatically from its own predictions.

**1. Active Learning Integration** (builds on Phase 6 active_learning.py)
- Weekly: pull 50 most uncertain predictions (confidence 0.4–0.6)
- For each: run targeted signal collection (more scraping on that company)
- Re-score after 7 days. If confidence resolves → add to training data.

**2. Mandate Confirmation Hunter** (`app/services/mandate_hunter.py`)
- Daily: for every company with score > 0.7 in any practice area:
  scan CanLII, news, SEDAR+ for confirmed mandate evidence
- If mandate confirmed → create mandate_label with label_method=auto_confirmed
- Feeds into next model retraining cycle

**3. Drift Detector** (`app/ml/drift_detector.py`)
- Monitors feature distribution weekly (using PSI — Population Stability Index)
- If PSI > 0.2 for any feature → flag model for retraining
- If PSI > 0.25 → auto-trigger retraining job on Azure

**4. Scheduled Retraining** (Celery beat)
- Full retraining: monthly (Azure batch job)
- Incremental update (new labels only): weekly
- Model validation: before any model is promoted to production,
  must beat current production model on holdout F1 by ≥ 0.02

**5. False Positive Audit Loop** (`app/ml/fp_audit.py`)
- Monthly: review predictions that scored > 0.7 but no mandate confirmed in 90 days
- These become high-confidence negative labels
- 30-day audit Celery task: `ml.run_fp_audit`

---

## Phase 10 — Testing & Hardening

**Goal:** Production-grade test coverage. Security hardening.

**Coverage targets:**
- Overall: ≥ 90% line coverage
- `app/auth/`: 100%
- `app/ml/`: ≥ 85%
- `app/scrapers/`: ≥ 80%
- `app/routes/`: ≥ 90%

**Test types to add:**
- Load test: 100 concurrent score requests, verify p95 < 500ms
  (use locust: `tests/load/locust_score_api.py`)
- Security: OWASP ZAP scan against staging environment
- Fuzzing: hypothesis-based property tests on EntityResolver + feature computation
- Contract tests: verify all API responses match OpenAPI schema

**Security hardening checklist:**
- SQL injection: all queries use SQLAlchemy ORM (no raw SQL)
- XSS: CSP headers in middleware
- CSRF: not applicable (JWT API, no cookies)
- Rate limiting: verify rate limiter fails open (Redis down → requests pass)
- Secrets: rotate SECRET_KEY, verify no secrets in git history
- Dependencies: `pip-audit` scan, fix all HIGH/CRITICAL vulns
- Docker: verify non-root user, no exposed debug ports in production config

**API documentation:**
- OpenAPI spec auto-generated from FastAPI
- Add descriptions to all endpoints, request/response models
- `GET /api/docs` available in staging, disabled in production

---

## Phase 11 — Deployment

**Goal:** Live on the internet, HTTPS, monitoring, alerts.

**Infrastructure checklist:**
- Replace all `REPLACE_GITHUB_USERNAME` placeholders in do-app.yaml
- Replace domain placeholder `oracle-bd.example.com` with real domain
- Set all production env vars in DigitalOcean App Platform dashboard
- Configure DigitalOcean Managed PostgreSQL (not containerised DB)
- Configure MongoDB Atlas free tier → upgrade to M10 for production
- Configure DigitalOcean Managed Redis (not containerised Redis)

**CI/CD verification:**
- GitHub Actions CI runs on every PR: ruff + mypy + bandit + pytest
- GitHub Actions CD deploys to DigitalOcean on merge to main
- Verify CD pipeline completes successfully end-to-end

**Monitoring:**
- Sentry DSN configured: captures all unhandled exceptions
- Uptime monitor: configure DigitalOcean uptime check on /api/health
- Celery monitoring: Flower dashboard (admin access only, not public)
- Alert on: consecutive scraper failures > 3, canary failure, API p95 > 1s

**SSL:** DigitalOcean App Platform handles SSL automatically (Let's Encrypt)

**Database migrations:**
- Run all Alembic migrations in order against production DB
- Verify with: `alembic current` → should show latest revision

**Smoke test post-deploy:**
- `GET /api/health` → 200
- `GET /api/ready` → 200
- `POST /api/auth/login` with admin credentials → 200 + JWT
- `GET /api/v1/scores/{test_company_id}` → 200 + valid score matrix
- Celery worker: verify at least one successful scraper run after deploy

---

## Phase 12 — Post-Launch Optimization

**Goal:** Validate predictions against real mandate outcomes.
Improve weakest-performing practice areas.

**Monthly review cadence:**
1. Pull all predictions from 90 days ago with score > 0.5
2. Check CanLII/news/SEDAR+ for mandate confirmation
3. Calculate precision/recall per practice area
4. Identify bottom 5 practice areas by F1 score
5. Root cause: missing signals? bad labels? wrong features?
6. Implement fix (new scraper, new feature, label correction)
7. Retrain affected practice area models
8. Deploy → verify improvement on holdout

**KPIs to track (stored in `platform_metrics` table):**
- Precision@0.7 per practice area (what % of high-score predictions confirmed)
- Recall@0.5 per practice area (what % of real mandates were scored > 0.5)
- Mean days signal-to-mandate (lead time quality)
- Scraper uptime % per source
- API p95 latency (target: < 200ms)
- Signal volume per day (data pipeline health)

**Competitive intelligence integration** (Agent 035):
- Track law firm lateral hires (partner departing for competitor)
- These signal which practice areas competitors are investing in
- Source: legal industry publications (Precedent Magazine, Law Times RSS)

---

*This file is the authoritative phase specification for Claude Code.*
*Do not modify without user approval.*
*Last updated: Phase 1 complete — March 2026*
