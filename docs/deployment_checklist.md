# ORACLE — Production Deployment Checklist

> Complete every item in order before go-live. Items marked ⚠️ are blocking.

---

## 1. Secrets & Configuration

- [ ] ⚠️ `SECRET_KEY` changed from default — minimum 64 random characters
  ```bash
  python -c "import secrets; print(secrets.token_urlsafe(64))"
  ```
- [ ] ⚠️ Default admin password changed (`admin@halcyon.legal` / `ChangeMe123!`)
- [ ] ⚠️ Default partner password changed (`partner@halcyon.legal` / `partner123!`)
- [ ] ⚠️ `ENVIRONMENT=production` set in DO App Platform environment variables
- [ ] ⚠️ `DATABASE_URL` set to DO Managed PostgreSQL URL (asyncpg driver)
- [ ] ⚠️ `MONGODB_URL` set to MongoDB Atlas connection string
- [ ] ⚠️ `REDIS_URL` set to DO Managed Redis URL
- [ ] ⚠️ `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND` set (same Redis)
- [ ] `SENTRY_DSN` set — error monitoring active in production
- [ ] `SPACES_KEY` + `SPACES_SECRET` set — model artifact access
- [ ] `SLACK_WEBHOOK_URL` set — deploy failure + critical alerts
- [ ] `CANLII_API_KEY` set (free — register at developer.canlii.org)
- [ ] `ALPHA_VANTAGE_API_KEY` set (25 free requests/day)
- [ ] `PROXYCURL_API_KEY` set (LinkedIn trigger — 10 free credits/month)
- [ ] `TWITTER_BEARER_TOKEN` set (social signals)
- [ ] `HIBP_API_KEY` set (dark web monitoring)
- [ ] `GROQ_API_KEY` set IF retraining is needed (training only — never production scoring)
- [ ] All secrets set via DO App Platform console → **never committed to git**

---

## 2. Database

- [ ] ⚠️ DO Managed PostgreSQL provisioned in **tor1** region (Canadian data residency)
- [ ] ⚠️ Migrations applied manually (see script below) — **never run automatically**:
  ```bash
  CONFIRM=yes DATABASE_URL=postgresql+asyncpg://<user>:<pass>@<host>:25060/oracle_db \
    bash scripts/run_migrations.sh
  ```
- [ ] ⚠️ Verify migration head matches expected revision:
  ```bash
  cd backend && alembic current
  # Expected: 0008_phase9_feedback (head)
  ```
- [ ] Initial seed run (only on first deploy):
  ```bash
  cd backend && python -m scripts.seed_db
  ```
- [ ] `agents.seed_decay_config` Celery task run once (seeds signal_decay_config defaults):
  ```bash
  # Via Celery CLI after worker is up:
  celery -A app.tasks.celery_app:celery_app call agents.seed_decay_config
  ```

---

## 3. Model Artifacts

- [ ] ⚠️ Azure ML training job completed successfully (`azure/training/azure_job.py`)
- [ ] All 34 × 3 = 102 model artifacts uploaded to DO Spaces bucket `oracle-models`
- [ ] `model_registry` table populated (check: `SELECT COUNT(*) FROM model_registry`)
- [ ] Orchestrator loads at startup — GET `/api/health` returns `"ml_ready": true`

---

## 4. Application Health

- [ ] ⚠️ `GET /api/health` → HTTP 200, all components healthy
- [ ] ⚠️ `GET /api/ready` → HTTP 200
- [ ] Canary scraper has fired in the last 60 minutes
  ```bash
  # Check via API logs or scraper_health table:
  SELECT last_success_at FROM scraper_health
  WHERE scraper_name = 'canary' ORDER BY last_success_at DESC LIMIT 1;
  ```
- [ ] Celery worker connected and consuming from all queues (check Flower or `doctl logs`)
- [ ] RedBeat scheduler running — beat service logs show scheduled tasks

---

## 5. GitHub Actions Secrets

Set these in the repository settings (Settings → Secrets and variables → Actions):

| Secret | Description |
|--------|-------------|
| `DIGITALOCEAN_ACCESS_TOKEN` | DO personal access token — read/write App Platform scope |
| `DO_APP_ID` | App Platform app UUID — get via `doctl apps list` |
| `DO_API_URL` | Production API base URL (e.g. `https://oracle-bd-for-law.ondigitalocean.app`) |
| `SMOKE_TEST_TOKEN` | Valid JWT for a readonly service account — used by CD smoke tests |
| `SLACK_WEBHOOK_URL` | Incoming webhook URL for deploy failure Slack alerts |

- [ ] All 5 GitHub Actions secrets set

---

## 6. Frontend (Vercel or DO Static Site)

- [ ] ⚠️ `VITE_API_URL` set to production DO backend URL
- [ ] Frontend build succeeds: `npm run build` (no TypeScript or ESLint errors)
- [ ] Vercel (or DO static site) deployment succeeded
- [ ] Login page loads and accepts production credentials
- [ ] Dashboard renders — TrendCharts and top-velocity table populated
- [ ] Score matrix loads for at least one company
- [ ] `/api` proxying is NOT enabled in production (Vite proxy is dev-only)

---

## 7. CORS

The `ALLOWED_ORIGINS` env var in `app/config.py` controls CORS. The `do-app.yaml`
already sets it to the default DO domain:

```yaml
- key: ALLOWED_ORIGINS
  value: '["https://oracle-bd-for-law.ondigitalocean.app"]'
```

If using a custom domain (e.g. `oracle.halcyon.legal`), update this value in the
DO App Platform console to include both the custom domain and the DO default:

```json
["https://oracle.halcyon.legal", "https://oracle-bd-for-law.ondigitalocean.app"]
```

- [ ] `ALLOWED_ORIGINS` includes the production frontend URL
- [ ] `OPTIONS` pre-flight requests return HTTP 200 from the backend

---

## 8. Monitoring

### DigitalOcean App Platform Alerts
Configure in DO console → App → Insights → Alerts:

- [ ] CPU usage > 80% for 5 minutes — alert to Slack/email
- [ ] Memory usage > 85% for 5 minutes — alert to Slack/email
- [ ] HTTP error rate > 5% (5xx responses) for 5 minutes — alert to Slack/email
- [ ] Response time p95 > 500ms for 5 minutes — alert to Slack/email

### Sentry
Configure at sentry.io after setting `SENTRY_DSN`:

- [ ] "New issue" alert → email to engineering team
- [ ] "Regression" alert (issue recurs after being resolved) → email
- [ ] Set environment to `production` in Sentry project settings
- [ ] Verify Sentry receives at least one event after deployment (check health endpoint 404 test)

### UptimeRobot (free external monitoring)
- [ ] Create monitor at uptimerobot.com:
  - URL: `https://<DO_API_URL>/api/health`
  - Check interval: 5 minutes
  - Alert contact: email + Slack
- [ ] Verify monitor is "Up" and showing response time

---

## 9. Backups

### PostgreSQL (DO Managed Database)
- [ ] In DO console → Databases → `oracle-db` → Backups tab:
  - Enable automated backups
  - Retention: 7 days
  - Backup window: 03:00–04:00 UTC (low-traffic period)
- [ ] Test restore procedure in a staging environment before go-live

### MongoDB Atlas
- [ ] In Atlas console → Cluster → Backup:
  - M0 (free): continuous cloud backups enabled by default — verify
  - M10+: verify scheduled snapshots are active (daily recommended)
- [ ] Note: Atlas free tier (M0) has limited restore options — plan upgrade if data volume grows

### DO Spaces (Model Artifacts)
- [ ] Model artifacts are already versioned by timestamp in `oracle-models` bucket
- [ ] No additional backup needed — each training run creates a new immutable artifact
- [ ] To restore a previous model: update `model_registry` table to point to a prior version

---

## 10. Rollback Procedure

### Application Rollback (instant)
Revert to a previous DO App Platform deployment:

```bash
# List recent deployments
doctl apps list-deployments <APP_ID>

# Roll back to a specific deployment ID
doctl apps create-deployment <APP_ID> --deployment-id <PREVIOUS_DEPLOYMENT_ID>
```

Or: revert the git commit and push to `main` (CD pipeline redeploys automatically).

### Database Rollback
```bash
# Roll back one migration
CONFIRM=yes DATABASE_URL=<url> bash -c "cd backend && alembic downgrade -1"

# Roll back to a specific revision
CONFIRM=yes DATABASE_URL=<url> bash -c "cd backend && alembic downgrade 0007_phase7_api"

# View revision history
cd backend && alembic history
```

⚠️ **Always take a database backup before running any downgrade.**

---

## Post-Launch Verification (within 1 hour of go-live)

- [ ] At least one full scraper cycle completed (check scraper_health table)
- [ ] Celery beat schedule is firing — check beat service logs for scheduled task output
- [ ] At least one company has scoring_results written for today
- [ ] `/api/metrics` endpoint returns Prometheus text format (admin token required)
- [ ] Sentry dashboard shows no unresolved high-severity issues
- [ ] UptimeRobot shows 100% uptime since go-live

---

*Last updated: Phase 11 — March 2026*
