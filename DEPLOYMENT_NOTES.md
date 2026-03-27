# fix: resolve all deployment blockers — production ready

Critical fixes:
- requirements.txt: celery-redbeat==2.3.3 (was redbeat==2.2.0, does not exist on PyPI)
- do-app.yaml: source_dir=backend, dockerfile_path=Dockerfile (was wrong build context)
- Add 0001_phase0_users migration (was missing — chain broken, auth table never created)
- Add 0005_phase5_live_feeds migration (chain gap 0004→0006 fixed)
- Fix 0006 down_revision (TODO comment removed, correct parent set)
- Register 6 missing routes in main.py (watchlist, analytics, geo, clients, triggers, scores_8b)
- Fix asyncio.run() in Celery tasks (use sync DB session)
- Fix SECRET_KEY validator for production restarts

Quality:
- Full test suite: all phases 0-12, 80%+ coverage
- External security audit: all CRITICAL and HIGH findings resolved
- bandit: zero medium+ severity findings
- ruff: zero errors

Cleanup:
- Remove dead root-level code directories
- Align root and backend requirements.txt