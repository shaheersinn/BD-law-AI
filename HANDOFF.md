# ORACLE — Claude Code Handoff Brief

> READ THIS BEFORE CLAUDE.md.
> This file is the first-session brief for Claude Code.
> It was written in the claude.ai chat session where all architecture was designed
> and Phases 0 and 1 were built.

---

## Context

ORACLE is a BigLaw BD intelligence platform. It predicts which companies will need
legal counsel across 34 practice areas × 3 time horizons (30/60/90 days).

All architecture decisions, phases, agents, and rules were finalized in a prior
claude.ai session. Everything is captured in CLAUDE.md. Read CLAUDE.md in full
before writing any code.

---

## Current State

| What | Status |
|------|--------|
| Phase 0 — Scaffold | ✅ Complete. App boots. Auth works. |
| Phase 1 — Scrapers (90+) | ✅ Complete. 72 files, 0 audit errors. |
| Phase 1B — Scraper Audit | ⏳ NEXT — start here |
| All other phases | ⏳ Pending |

The codebase was built in claude.ai (no real lint/test runs possible there).
**Your first job is to run the real tool chain on what exists and fix everything
that fails before writing any new code.**

---

## First Session Protocol

```
1. Read HANDOFF.md (this file)
2. Read CLAUDE.md in full
3. Run: cd backend && pip install -r requirements.txt --break-system-packages
4. Run: ruff check app/ --fix
5. Run: ruff format app/
6. Run: mypy app/ --ignore-missing-imports
7. Run: bandit -r app/ -ll
8. Fix ALL issues found
9. Run: docker compose up -d
10. Run: pytest tests/ -v
11. Fix ALL test failures
12. Commit: git add -A && git commit -m "chore: real lint+test pass on Phase 0+1"
13. ONLY THEN begin Phase 1B
```

Do not skip steps. Do not begin Phase 1B until steps 1–12 are clean.

---

## Per-Phase Protocol (every phase, no exceptions)

Defined in CLAUDE.md under "Critical Rules". Summary:

1. Pre-phase web research (best practices for that phase's domain)
2. Read CLAUDE.md for context
3. Write code
4. security-auditor review (check for hardcoded secrets, bare except, sync requests, print())
5. code-reviewer quality gate
6. Run ruff + mypy + bandit + pytest — fix all failures
7. Update CLAUDE.md phase status table
8. Commit

---

## Key Rules — Memorise These

- **ML models score. LLMs never score production. Ever.**
- **English only.** No French NLP, no bilingual processing.
- **PostgreSQL** = structured data. **MongoDB** = social/unstructured + corporate graph.
- **ALL DB calls async.** asyncpg driver. Never psycopg2. Never sync SQLAlchemy.
- **ALL HTTP calls** use httpx (async). Never requests (sync).
- **No bare except.** No print(). No hardcoded secrets. No blocking I/O.
- **Celery** must use RedBeat scheduler, worker_prefetch_multiplier=1, task_acks_late=True.
- **JWT** carries only: sub, role, type, iat, exp.
- **bcrypt** cost factor must be 12.
- **Rate limiter** must fail open when Redis is unavailable.
- **Docker** runs as non-root user.
- **Groq API** = Phase 4 training ONLY. Never production.

---

## What Phase 1B Must Deliver

Phase 1B is the Scraper Audit & Validation phase. It must produce:

1. **Scraper health dashboard** — endpoint showing live status of all 90+ scrapers
2. **Data quality validator** — checks signal records for completeness + consistency
3. **Pipeline smoke test** — end-to-end test: scraper → signal → PostgreSQL + MongoDB
4. **Source reliability scorecard** — per-scraper success rate, avg records/run, p95 latency
5. **Canary system** — synthetic test signals that verify the pipeline is alive
6. **Regression test suite** — ensures scrapers don't silently break between deploys
7. **Live scraper dashboard** — React component showing scraper health in the UI

Deliver: all code + updated CLAUDE.md + Word document (Phase 1B).

---

## Environment

```
Backend:    FastAPI 0.115 / Python 3.12
DB:         PostgreSQL 15 (asyncpg) + MongoDB Atlas (Motor)
Cache:      Redis 7
Queue:      Celery 5.4 + RedBeat
Deploy:     DigitalOcean App Platform (tor1) — do-app.yaml
Frontend:   React 18 + Vite
CI/CD:      GitHub Actions (.github/workflows/)
```

Local dev:
```bash
cp .env.example .env   # set SECRET_KEY + API keys
docker compose up       # starts all 7 services
make test               # run test suite
make lint               # ruff + mypy + bandit
```

---

## Files to Read Before Coding

In order:
1. `HANDOFF.md` (this file)
2. `CLAUDE.md` (full project context)
3. `backend/app/scrapers/base.py` (BaseScraper contract)
4. `backend/app/scrapers/registry.py` (ScraperRegistry)
5. `backend/app/models/scraper_health.py` (ScraperHealth model)
6. `backend/app/tasks/scraper_tasks.py` (existing Celery task structure)

---

## Word Documents

Full phase specifications are in the Word documents delivered alongside each ZIP.
These are in your local downloads — they were not committed to the repo (too large).

If you need the spec for a phase, the user can provide it.
The most important spec for Phase 1B is Section 7 of the Phase 1 Word document:
"How to Run Phase 1 Scrapers" — this tells you what's already wired.

---

## Agent System (important)

**Production agents (85):** Celery tasks inside the deployed ORACLE app.
All exist as stubs in `app/tasks/_impl.py`. Implemented phase by phase.
These are NOT Claude Code sub-agents.

**Claude Code sub-agents (18 from lst97):** Install with:
```bash
# From repo root (if you have the agents folder)
cp agents/* ~/.claude/agents/
```
These activate automatically. agent-organizer sequences the right specialists per task.

**Dev role agents (12):** Claude adopts these mental frameworks automatically:
Backend Specialist, Frontend Specialist, DevOps Engineer, Security Engineer,
QA Engineer, Technical Writer, etc. No installation needed.

---

## If You Get Stuck

The full conversation history (all design decisions, every reasoning step)
is captured in the claude.ai chat session. The user can open it and ask
clarifying questions there, then bring answers back to Claude Code.

CLAUDE.md is the single source of truth for operational decisions.
If something is not in CLAUDE.md, assume the strictest interpretation of the rules above.

---

*Handoff written: March 2026*
*Phases complete: 0, 1*
*Next phase: 1B*
