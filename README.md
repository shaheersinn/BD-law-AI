# ORACLE — BD for Law

> BigLaw business development intelligence platform  
> Python · FastAPI · PostgreSQL · Redis · Celery · React · Anthropic Claude

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green.svg)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## What This Is

ORACLE is a 22-module BD intelligence system for BigLaw firms. It monitors 28 signal types across regulatory feeds, court records, job postings, ADS-B flight data, SEDAR/EDGAR filings, and satellite imagery — then predicts which clients are about to leave and which prospects need a lawyer, before any competitor calls.

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **API** | FastAPI (async) | REST + SSE streaming, JWT auth |
| **Database** | PostgreSQL + SQLAlchemy 2.0 | All structured data |
| **ML** | XGBoost · LightGBM · scikit-learn | Churn, urgency, practice classifier |
| **Scrapers** | httpx · feedparser · BeautifulSoup | SEDAR, EDGAR, CanLII, RSS feeds, OpenSky |
| **Scheduler** | Celery + Redis | Nightly scraping, scoring, model retraining |
| **Cache** | Redis | AI response caching, rate limiting |
| **AI** | Anthropic Claude (+ Groq fallback) | All written intelligence output |
| **Frontend** | React + Vite + Recharts | Dashboard |

---

## Quick Start — Docker (2 commands)

```bash
cp .env.example .env
# Open .env and set ANTHROPIC_API_KEY (or GROQ_API_KEY for free)
# SECRET_KEY has a dev default but change it for any real deployment

docker compose up
```

**That's it.** Docker starts PostgreSQL, Redis, FastAPI, Celery worker, Celery beat, and the React frontend. On first boot it runs migrations and seeds demo data.

| Service | URL |
|---------|-----|
| Dashboard | http://localhost:3000 |
| API docs (Swagger) | http://localhost:8000/api/docs |
| API docs (ReDoc) | http://localhost:8000/api/redoc |
| Health check | http://localhost:8000/api/health |

---

## Local Development (no Docker)

### Prerequisites
- Python 3.12+
- Node 20+
- PostgreSQL 15+ running locally  
- Redis running locally

```bash
# Install all dependencies
make install

# Copy and configure environment
cp .env.example .env
# Edit: DATABASE_URL, REDIS_URL, ANTHROPIC_API_KEY or GROQ_API_KEY

# Run database migrations and seed demo data
cd backend
alembic upgrade head
python -m scripts.seed_db

# Terminal 1 — FastAPI
make dev-api        # http://localhost:8000

# Terminal 2 — React
make dev-front      # http://localhost:5173

# Terminal 3 — Celery worker (optional — needed for scrapers)
make dev-worker

# Terminal 4 — Celery beat / scheduler (optional)
make dev-beat
```

---

## Environment Variables

Copy `.env.example` to `.env`. The only required variable for a working demo is an LLM key.

```bash
# Choose one (both are free tiers available):
ANTHROPIC_API_KEY=sk-ant-...   # https://console.anthropic.com
GROQ_API_KEY=gsk_...           # https://console.groq.com (14,400 free req/day)

# Required for JWT auth (auto-generated default is fine for local dev)
SECRET_KEY=your-32-char-secret-key-here

# Everything else is optional — scrapers degrade gracefully when keys are missing
CANLII_API_KEY=       # https://developer.canlii.org (free)
OPENSKY_USERNAME=     # https://opensky-network.org (free)
OPENSKY_PASSWORD=
```

---

## Architecture

```
oracle-bd/
├── backend/
│   ├── app/
│   │   ├── auth/              JWT auth, user model, role-based access
│   │   │   ├── models.py      User ORM (admin/partner/associate/readonly)
│   │   │   ├── service.py     bcrypt passwords, JWT issuance, account lockout
│   │   │   ├── dependencies.py  require_auth, require_partner, require_admin
│   │   │   └── router.py      /login /refresh /logout /me /users
│   │   │
│   │   ├── cache/             Redis cache with typed key builders
│   │   │   └── client.py      get/set/delete, TTL constants, get_or_set pattern
│   │   │
│   │   ├── middleware/
│   │   │   ├── error_handler.py   Structured JSON errors + request IDs
│   │   │   └── rate_limiter.py    Per-user Redis rate limiting (60 AI/hr)
│   │   │
│   │   ├── ml/                Machine learning models
│   │   │   ├── convergence.py     Bayesian signal convergence (28 signals)
│   │   │   ├── churn_model.py     XGBoost + Platt calibration
│   │   │   ├── urgency_model.py   LightGBM + SMOTE + isotonic calibration
│   │   │   └── practice_classifier.py  Multi-label gradient boosting
│   │   │
│   │   ├── models/            SQLAlchemy ORM models
│   │   │   ├── client.py      Client, Matter, BillingRecord, ChurnSignal
│   │   │   ├── signal.py      Trigger, Alert, JetTrack, FootTrafficEvent,
│   │   │   │                  SatelliteSignal, PermitFiling, RegulatoryAlert
│   │   │   └── bd_activity.py Partner, BDActivity, Alumni, ContentPiece,
│   │   │                      WritingSample, ReferralContact, MatterSource
│   │   │
│   │   ├── routes/            FastAPI routers
│   │   │   ├── clients.py     CRUD + churn brief (cached) + SSE stream
│   │   │   ├── triggers.py    Live feed + label feedback loop + SSE stream
│   │   │   ├── geo.py         Intensity map, jets, foot traffic, satellite, permits
│   │   │   ├── ai.py          All AI generation endpoints + streaming
│   │   │   ├── watchlist.py   Watchlist CRUD, bulk CSV import, company search
│   │   │   └── analytics.py   Model performance, signal quality, BD analytics
│   │   │
│   │   ├── scrapers/          Data collection
│   │   │   ├── sedar.py       SEDAR+ material changes, confidentiality agreements
│   │   │   ├── edgar.py       SEC EDGAR confidential treatment, SC 13D, 8-K
│   │   │   ├── canlii.py      CanLII REST API — new litigation by company
│   │   │   ├── jobs.py        Indeed RSS — GC/CCO/CISO job posting intelligence
│   │   │   ├── enforcement.py OSC/OSFI/Competition Bureau/FINTRAC/ECCC RSS
│   │   │   └── opensky.py     ADS-B jet tracker — Bay Street proximity detection
│   │   │
│   │   ├── services/
│   │   │   ├── anthropic_service.py  17 named prompts + Groq fallback
│   │   │   ├── streaming.py          SSE streaming for real-time AI generation
│   │   │   ├── entity_resolution.py  RapidFuzz company name matching (82% threshold)
│   │   │   ├── audit_log.py          Append-only audit trail (Law Society compliance)
│   │   │   └── churn_feature_service.py  Feature extraction from billing data
│   │   │
│   │   ├── tasks/             Celery scheduled jobs
│   │   │   ├── celery_app.py  8 scheduled tasks (scraping, scoring, retraining)
│   │   │   └── _impl.py       Async task implementations
│   │   │
│   │   ├── config.py          Pydantic settings (all env vars)
│   │   ├── database.py        Async SQLAlchemy engine + session factory
│   │   └── main.py            FastAPI app, middleware wiring, router registration
│   │
│   ├── alembic/               Database migrations
│   ├── scripts/seed_db.py     Demo data seeder
│   ├── tests/                 45 tests across 3 files
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx            Main 22-module ORACLE dashboard
│   │   ├── api/client.js      Typed API client (auth, streaming, all endpoints)
│   │   └── pages/
│   │       ├── GeoPages.jsx   5 geospatial intelligence modules
│   │       └── NewModules.jsx  Live Triggers, BD Coaching, Ghost Studio
│   └── package.json
│
├── docker-compose.yml         6 services: db, redis, api, worker, beat, frontend
├── Makefile                   Developer shortcuts
└── .env.example               All environment variables documented
```

---

## API Reference

Full interactive docs at `http://localhost:8000/api/docs`.

### Authentication

```bash
# Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@halcyon.legal", "password": "admin123"}'
# Returns: { "access_token": "...", "refresh_token": "...", "role": "admin" }

# Use token
curl http://localhost:8000/api/clients/ \
  -H "Authorization: Bearer <access_token>"
```

Default seeded credentials (change immediately in production):
- `admin@halcyon.legal` / `admin123` — full access
- `partner@halcyon.legal` / `partner123` — partner role

### Key Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/auth/login` | Get JWT tokens |
| `GET` | `/api/clients/churn-scores` | All clients ranked by risk |
| `POST` | `/api/clients/{id}/churn-brief` | AI action brief (cached 6h) |
| `GET` | `/api/clients/{id}/churn-brief/stream` | Streaming SSE version |
| `GET` | `/api/triggers/live` | Live signal feed |
| `POST` | `/api/triggers/{id}/label` | Partner feedback → training data |
| `GET` | `/api/geo/jets` | Corporate jet tracks |
| `GET` | `/api/analytics/model-performance` | PR-AUC, precision, advance days |
| `GET` | `/api/analytics/health` | System health (DB, Redis, Celery) |
| `GET` | `/api/search?q=arctis` | Fuzzy company search |
| `POST` | `/api/watchlist/import` | Bulk CSV prospect import |

---

## The 22 Intelligence Modules

| # | Module | What It Does |
|---|--------|-------------|
| 1 | **Churn Predictor** | XGBoost scoring of client flight risk from billing + communication signals |
| 2 | **Regulatory Ripple** | OSC/OSFI/CSA/ECCC/FINTRAC feed monitoring → client-mapped alerts + AI drafts |
| 3 | **Relationship Heat Map** | Partner × client relationship matrix with whitespace gaps |
| 4 | **Live Triggers** | Real-time SEDAR/EDGAR/CanLII/Job signal feed with label buttons |
| 5 | **Mandate Heat Map** | Geopolitical jurisdiction demand scoring |
| 6 | **Jet Tracker** | ADS-B corporate jet Bay Street proximity detection |
| 7 | **Foot Traffic Intel** | GPS device clustering at competitor offices (commercial data) |
| 8 | **Satellite Signals** | Parking lot / construction change detection |
| 9 | **Permit Radar** | Environmental + construction permit scraping → legal need classification |
| 10 | **Pre-Crime Engine** | Legal Urgency Index scoring for prospects |
| 11 | **Mandate Formation** | Bayesian multi-signal convergence (6 layers) |
| 12 | **M&A Dark Signals** | Options anomalies + jet + SEDAR confidentiality convergence |
| 13 | **Competitor Radar** | Lateral hire tracking, practice expansion, conflict arbitrage |
| 14 | **Wallet Share** | Estimated capture rate vs total client legal spend |
| 15 | **Alumni Activator** | Former associate in-house trigger detection + warm outreach drafting |
| 16 | **GC Profiler** | Psychographic profiling from public information |
| 17 | **Associate Program** | BD tracking + AI coaching for associates |
| 18 | **Pitch Autopsy** | Win/loss analysis + AI debrief + 6-week campaign orchestration |
| 19 | **BD Coaching** | Partner-level behavioural feedback (Whoop for BD) |
| 20 | **Ghost Studio** | Voice-matched LinkedIn draft generation + content attribution |
| 21 | **Analytics** | Model performance, signal quality, system health |
| 22 | **Watchlist** | Company monitoring CRUD + bulk CSV import + fuzzy search |

---

## ML Models

### Churn Classifier (XGBoost)
Predicts client departure probability from billing and communication features.

```bash
# Prepare training data CSV with these columns:
# total_billed, yoy_billing_change, matters_opened, days_since_last_matter,
# disputes_this_year, writeoff_pct, gc_changed, days_since_last_contact,
# practice_area_count, label (1=churned, 0=stayed)

make train-churn  # expects data/churn_training_data.csv
```

### Legal Urgency Index (LightGBM)
Scores prospects 0-100 on how urgently they need legal counsel.

```bash
make train-urgency  # expects data/urgency_training_data.csv
```

### Convergence Engine (Bayesian)
No training required — runs immediately with calibrated priors. Improves after 6 months of label data.

| Signal | Base Weight | Source |
|--------|------------|--------|
| SEDAR confidentiality agreement | 0.91 | SEDAR+ |
| M&A confirmed (S-4/DEFM14A) | 0.96 | EDGAR |
| CCAA/bankruptcy filing | 0.94 | CanLII |
| Competition Bureau investigation | 0.91 | CompBureau RSS |
| OSC enforcement notice | 0.90 | OSC RSS |
| Corporate jet Bay St 2× in 14d | 0.88 | OpenSky |
| Material change report | 0.88 | SEDAR+ |
| Mass layoff + satellite drop | 0.82+0.82 | Permit + Satellite |
| ... | | |

---

## Scheduled Tasks

| Task | Schedule | Purpose |
|------|----------|---------|
| `scrape_sedar` | Every 2h (8am-6pm) | SEDAR+ material changes, confidentiality |
| `scrape_edgar` | Every hour (:15) | SEC EDGAR CTR, SC 13D, 8-K |
| `scrape_enforcement` | Every 4h | OSC/OSFI/CompBureau/FINTRAC/ECCC |
| `scrape_jobs` | Daily 6am | Indeed job posting intelligence |
| `scrape_canlii` | Daily 7am | New litigation for watchlist |
| `scrape_jets` | Daily 3am | OpenSky ADS-B jet tracks |
| `run_convergence_scoring` | Daily 2am | Score all active prospects |
| `update_churn_scores` | Daily 1am | Re-score all clients |
| `retrain_models` | Sunday 3am | Auto-retrain on accumulated labels |

---

## Data Sources

All sources have free tiers. No data is required to run the demo (seeded data is used).

| Source | What | URL | Cost |
|--------|------|-----|------|
| SEDAR+ | Material changes, M&A filings | sedarplus.ca | Free |
| SEC EDGAR | US filings, confidential treatment | efts.sec.gov | Free |
| CanLII | Canadian court records | developer.canlii.org | Free (register) |
| OpenSky Network | ADS-B jet tracking | opensky-network.org | Free (register) |
| OSC/OSFI/Competition Bureau | Regulatory enforcement RSS | Various | Free |
| Indeed RSS | Job postings | indeed.com/rss | Free |
| Transport Canada Registry | Aircraft registration | tc.canada.ca | Free CSV |
| SEDI | Insider trading / director changes | sedi.ca | Free |
| Ontario Environmental Registry | Permits | ero.ontario.ca | Free |
| IAAC | Federal environmental assessments | iaac-aeic.gc.ca | Free API |
| Groq API | Free LLM (Llama 3.1 70b) | console.groq.com | 14,400 req/day free |

---

## Deployment

### DigitalOcean (production)

```bash
# Configure app, worker, beat, and frontend in DigitalOcean App Platform.
# Set all runtime secrets in DO dashboard (not in git-managed files):
# SECRET_KEY, DATABASE_URL, MONGODB_URL, REDIS_URL,
# REDIS_RESULT_BACKEND, CELERY_BROKER_URL, CELERY_RESULT_BACKEND
#
# CI/CD triggers:
# doctl apps create-deployment <DO_APP_ID> --wait
# so existing DO app config/secrets are reused each deploy.
```

### Estimated Monthly Cost (5-partner firm)

| Item | Cost |
|------|------|
| Anthropic API | $20-40/month |
| Neon PostgreSQL | Free → $19/month |
| DigitalOcean backend | App Platform pricing |
| Upstash Redis | Free tier |
| DigitalOcean frontend static site | Included with DO app |
| **Total** | **$20-70/month** |

---

## Security Notes

Before going live with real client data:

1. **Change SECRET_KEY** to a real 32+ character random string
2. **Set ENVIRONMENT=production** in your deployment env vars
3. **Enable HTTPS** on your deployment platform
4. **Create real user accounts** (`POST /api/auth/users`) and delete the demo seed accounts
5. **Review ALLOWED_ORIGINS** — restrict to your actual domain
6. **Set up Sentry** for error monitoring (`SENTRY_DSN`)
7. Consider Canadian data residency requirements if your Law Society requires it (use `ca-central-1` on AWS or Azure Canada Central)

---

## Testing

```bash
make test
# or
cd backend && python -m pytest tests/ -v

# Run specific test file
cd backend && python -m pytest tests/test_auth.py -v
cd backend && python -m pytest tests/test_entity_resolution_extended.py -v
cd backend && python -m pytest tests/test_convergence.py -v
```

45 tests across auth flow, JWT claims, entity resolution (15 real Canadian company names), cache key determinism, and Bayesian convergence scoring.

---

## Contributing

1. Fork the repo
2. Create a feature branch: `git checkout -b feature/new-scraper`
3. Add tests for your scraper
4. Run `make test`
5. Submit a PR

---

## License

MIT — see [LICENSE](LICENSE).

Built for Halcyon Legal Partners LLP.
