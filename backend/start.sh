#!/bin/bash
set -e

echo "=== ORACLE API Startup ==="
echo "Environment: ${ENVIRONMENT:-development}"
echo "Step 1/3: Running Alembic migrations..."

cd /app

# Alembic reads DATABASE_URL from env and strips asyncpg internally (see alembic/env.py).
# This must succeed before we accept traffic.
python -m alembic upgrade head
echo "Migrations complete."

echo "Step 2/3: Seeding database (idempotent — skips if already seeded)..."
# --skip-if-seeded exits cleanly if users already exist.
# SEED_DEMO_DASHBOARD=1 controls whether demo companies/scores/triggers are created.
python -m scripts.seed_db --skip-if-seeded 2>&1 || {
  echo "ERROR: Seed script failed — see output above for cause. Continuing startup."
}
echo "Seed complete."

echo "Step 3/3: Starting API server..."
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 2 \
    --loop uvloop \
    --http httptools \
    --log-level info
