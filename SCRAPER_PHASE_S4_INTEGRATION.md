# ORACLE Scraper Phase S4 — Integration, Celery Wiring & Final Validation
# Run AFTER Phase S3 is complete and pushed.
# This is the final scraper phase. After this, start infrastructure provisioning.

## Pre-conditions
- Phases S1, S2, S3 all complete and pushed
- All scraper stubs replaced with real implementations
- All scrapers registered and passing unit tests

## What This Phase Does
1. Wire all scrapers into Celery scheduled tasks (RedBeat)
2. Implement scraper health monitoring (existing ScraperHealth model)
3. Run integration validation — verify end-to-end signal flow
4. Add missing scrapers to the budget manager
5. Final smoke test: 7-day accumulation readiness check
6. Update HANDOFF.md with deployment sequence

---

## TASK 1 — Celery Task Wiring

### Verify existing Celery task file
Find the Celery tasks file (likely `backend/app/tasks/scrapers.py` or similar):
```bash
find backend/app/ -name "*.py" -exec grep -l "@celery\|@shared_task\|@app.task" {} \;
```

For each scraper category, there should be a Celery task:
```python
from celery import shared_task
from app.database import get_sync_db
import asyncio

@shared_task(name="scrapers.run_regulatory", bind=True, max_retries=3)
def run_regulatory_scrapers(self):
    """Run all regulatory scrapers. Scheduled: daily 6am Toronto."""
    from app.scrapers.registry import ScraperRegistry
    from app.scrapers.storage import store_signals
    
    scrapers = ScraperRegistry.all_by_category("regulatory")
    total = 0
    
    with get_sync_db() as db:
        for scraper_class in scrapers:
            try:
                scraper = scraper_class()
                results = asyncio.run(scraper.scrape())
                asyncio.run(store_signals(results, db))
                total += len(results)
                log.info("scraper_complete", source=scraper.source_id, count=len(results))
            except Exception as exc:
                log.error("scraper_failed", source=scraper_class.source_id, error=str(exc))
                continue
    
    return {"category": "regulatory", "signals_stored": total}

# Repeat for: social, geo, corporate, legal, market, news, jobs, lawfirms
```

### RedBeat schedule (beat_schedule)
Add to Celery config:
```python
beat_schedule = {
    # Regulatory — daily, staggered to avoid hammering at same time
    "regulatory-scrapers-daily": {
        "task": "scrapers.run_regulatory",
        "schedule": crontab(hour=6, minute=0),  # 6am Toronto (UTC-5 → 11am UTC)
    },
    # Social — twice daily (morning + evening)
    "social-scrapers-morning": {
        "task": "scrapers.run_social",
        "schedule": crontab(hour=7, minute=30),
    },
    "social-scrapers-evening": {
        "task": "scrapers.run_social",
        "schedule": crontab(hour=19, minute=30),
    },
    # Geo — daily
    "geo-scrapers-daily": {
        "task": "scrapers.run_geo",
        "schedule": crontab(hour=8, minute=0),
    },
    # Corporate filings — daily (market hours awareness)
    "corporate-scrapers-daily": {
        "task": "scrapers.run_corporate",
        "schedule": crontab(hour=9, minute=0),
    },
    # Market data — every 4 hours during market hours
    "market-scrapers-market-hours": {
        "task": "scrapers.run_market",
        "schedule": crontab(hour="9,13,17", minute=30),
    },
    # Feature engineering — daily 2am (after scrapers finish)
    "feature-engineering-daily": {
        "task": "features.run_all_features",
        "schedule": crontab(hour=2, minute=0),
    },
    # ML scoring — daily 3am (after features)
    "ml-scoring-daily": {
        "task": "scoring.run_all_companies",
        "schedule": crontab(hour=3, minute=0),
    },
}
```

---

## TASK 2 — Budget Manager Integration

Open `backend/app/scrapers/budget_manager.py`.
Verify all new scrapers have budget entries:
```python
_DEFAULT_BUDGET = {
    # Regulatory (free sources — generous limits)
    "regulatory_osc": {"daily_limit": 500, "monthly_limit": 15000},
    "regulatory_osfi": {"daily_limit": 200, "monthly_limit": 6000},
    "regulatory_bcsc": {"daily_limit": 200, "monthly_limit": 6000},
    "regulatory_asc": {"daily_limit": 200, "monthly_limit": 6000},
    "regulatory_fsra": {"daily_limit": 200, "monthly_limit": 6000},
    "regulatory_crtc": {"daily_limit": 100, "monthly_limit": 3000},
    "regulatory_opc": {"daily_limit": 200, "monthly_limit": 6000},
    "regulatory_us_doj": {"daily_limit": 500, "monthly_limit": 15000},
    "regulatory_sec_aaer": {"daily_limit": 300, "monthly_limit": 9000},
    # Social (API-limited)
    "social_reddit": {"daily_limit": 200, "monthly_limit": 5000},
    "social_twitter": {"daily_limit": 300, "monthly_limit": 9000},  # 10k/month total budget
    "social_linkedin": {"daily_limit": 1, "monthly_limit": 10},     # 10 Proxycurl credits/month
    "social_stockhouse": {"daily_limit": 100, "monthly_limit": 3000},
    # Geo
    "geo_municipal": {"daily_limit": 100, "monthly_limit": 3000},
    "geo_opensky": {"daily_limit": 400, "monthly_limit": 12000},    # 400 req/day free tier
    "geo_lobbyist": {"daily_limit": 50, "monthly_limit": 1500},
    "geo_dark_web": {"daily_limit": 20, "monthly_limit": 500},
}
```

For each scraper NOT in budget: it runs unconstrained — this is a bug.
Every scraper must have a budget entry.

---

## TASK 3 — Scraper Health Dashboard Integration

The `ScraperHealth` model and `/api/scrapers/health` endpoint already exist.
Verify the health tracking actually records outcomes:

After each scraper run, update ScraperHealth:
```python
async def _update_scraper_health(
    db: AsyncSession,
    source_id: str,
    success: bool,
    count: int,
    error_msg: str | None = None,
) -> None:
    from app.models.scraper_health import ScraperHealth
    from sqlalchemy import select
    
    result = await db.execute(
        select(ScraperHealth).where(ScraperHealth.source_id == source_id)
    )
    health = result.scalar_one_or_none()
    
    now = datetime.now(tz=UTC)
    if health:
        health.last_run_at = now
        health.last_success = success
        health.last_count = count
        health.consecutive_failures = 0 if success else health.consecutive_failures + 1
        if error_msg:
            health.last_error = error_msg
    else:
        db.add(ScraperHealth(
            source_id=source_id,
            last_run_at=now,
            last_success=success,
            last_count=count,
            consecutive_failures=0 if success else 1,
            last_error=error_msg,
        ))
    await db.commit()
```

Check: is this health update being called after each scraper run? If not, wire it in.

---

## TASK 4 — Signal → Feature → Score Pipeline Validation

Run this validation sequence end-to-end (with mocked external calls):

### Step 1: Verify signal storage
```python
# Confirm ScraperResult → Signal (PostgreSQL) → company_features pathway
python -c "
from app.scrapers.base import ScraperResult
from datetime import datetime, UTC

# Create a test signal
result = ScraperResult(
    source_id='regulatory_osc',
    source_name='OSC',
    signal_type='regulatory_enforcement',
    company_name='Test Corp',
    title='Test enforcement action',
    summary='Test',
    source_url='https://osc.ca/test',
    published_at=datetime.now(tz=UTC),
    raw_payload={},
    practice_area_hints=['securities', 'litigation'],
    confidence=0.85,
)
print('ScraperResult created OK')
print(f'Practice area hints: {result.practice_area_hints}')
"
```

### Step 2: Verify registry is complete
```python
python -c "
from app.scrapers.registry import ScraperRegistry

all_scrapers = ScraperRegistry.all()
print(f'Total scrapers registered: {len(all_scrapers)}')

by_category = {}
for s in all_scrapers:
    cat = s.CATEGORY
    by_category[cat] = by_category.get(cat, 0) + 1

for cat, count in sorted(by_category.items()):
    print(f'  {cat}: {count} scrapers')

# Verify all new scrapers present
new_scrapers = [
    'regulatory_osc', 'regulatory_osfi', 'regulatory_bcsc', 'regulatory_asc',
    'regulatory_fsra', 'regulatory_crtc', 'regulatory_opc',
    'regulatory_us_doj', 'regulatory_sec_aaer',
    'social_reddit', 'social_twitter', 'social_linkedin', 'social_stockhouse',
    'geo_municipal', 'geo_opensky', 'geo_lobbyist', 'geo_dark_web',
]
registered_ids = [s.source_id for s in all_scrapers]
missing = [s for s in new_scrapers if s not in registered_ids]
if missing:
    print(f'MISSING: {missing}')
else:
    print('All new scrapers registered: PASS')
"
```

### Step 3: Verify no stubs remain
```bash
grep -rn "return \[\]" backend/app/scrapers/ --include="*.py" | grep -v "test_\|# " | grep -v "__init__"
```
Every hit that is NOT a commented-out stub (i.e., has no explanation comment above it) is a silent failure. Fix or document it.

---

## TASK 5 — Final Smoke Tests

### Full test suite
```bash
cd backend && pytest --tb=short -q
# Expected: 0 failures

cd backend && pytest --cov=app --cov-report=term-missing -q 2>&1 | grep -E "TOTAL|scrapers"
# Expected: scrapers/ coverage ≥ 70%
```

### Scraper registration check
```bash
python -c "
from app.scrapers.registry import ScraperRegistry
scrapers = ScraperRegistry.all()
stubs = [s for s in scrapers if not hasattr(s, 'scrape')]
print(f'Total: {len(scrapers)}, Stubs without scrape(): {len(stubs)}')
"
```

### Config check
```bash
python -c "
from app.config import get_settings
s = get_settings()
print('Config fields:')
for field in ['reddit_client_id', 'twitter_bearer_token', 'proxycurl_api_key', 'hibp_api_key']:
    val = getattr(s, field, 'MISSING')
    has_val = bool(val) and val != 'MISSING'
    print(f'  {field}: {\"SET\" if has_val else \"EMPTY (OK if no key yet)\"}')
"
```

---

## TASK 6 — Update HANDOFF.md for Infrastructure Provisioning

After all tasks complete, update HANDOFF.md with this section:

```markdown
## Scraper Phases Complete — Ready for Infrastructure Provisioning

### Scrapers implemented
- Phase S1: 9 regulatory scrapers (OSC, OSFI, BCSC, ASC, FSRA, CRTC, OPC, DOJ, SEC AAER)
- Phase S2: 4 social scrapers (Reddit, Twitter, LinkedIn, Stockhouse)
- Phase S3: 8 geo scrapers (Municipal Permits, OpenSky, Lobbyist, WSIB, Labour, Dark Web, CBSA, DBRS)
- Phase S4: Celery wiring, health monitoring, budget integration

### Total scrapers registered: [N]

### Infrastructure provisioning sequence
1. DigitalOcean App Platform (tor1):
   - Web service: FastAPI backend
   - Worker: Celery worker (2x)
   - Scheduler: Celery beat (RedBeat)
   - Managed PostgreSQL (1GB RAM to start)
   - Managed Redis (1GB)
   
2. MongoDB Atlas: Free tier M0 → upgrade when signal volume warrants

3. DO Spaces: Create bucket for model artifacts
   Bucket name: oracle-models
   Region: tor1

4. Vercel: Deploy frontend (auto from main branch)

5. Environment variables to set in DO App Platform:
   DATABASE_URL, MONGO_URL, REDIS_URL, JWT_SECRET_KEY,
   DO_SPACES_KEY, DO_SPACES_SECRET, DO_SPACES_BUCKET,
   REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET,
   TWITTER_BEARER_TOKEN, PROXYCURL_API_KEY, HIBP_API_KEY,
   SENTRY_DSN (optional)

### After deploy: 7-day accumulation
- Day 1: scrapers start running on schedule
- Day 3: first batch of signals in PostgreSQL
- Day 7: minimum data for Bayesian engines to produce meaningful scores
- Day 8+: ML scoring pipeline produces mandate probability matrix

### DO NOT expect ML output before day 8
```

---

## PHASE S4 COMPLETION CHECKLIST
- [ ] All scraper Celery tasks implemented with real category dispatch
- [ ] RedBeat schedule set for all categories
- [ ] Budget manager entries added for all 22+ new scrapers
- [ ] ScraperHealth update wired after each scraper run
- [ ] Full test suite: 0 failures
- [ ] No silent stubs: every return [] has a documented reason
- [ ] Total scrapers registered: print count and verify > 40
- [ ] HANDOFF.md updated with infrastructure provisioning sequence
- [ ] git commit -m "feat(scrapers): Phase S4 — Celery wiring, health monitoring, budget integration, full validation"
- [ ] git push origin main
- [ ] Begin DigitalOcean App Platform provisioning
