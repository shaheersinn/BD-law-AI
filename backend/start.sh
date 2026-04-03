#!/bin/bash
set -e

echo "=== ORACLE API Startup ==="
echo "Starting API server (DB migrations are not run in-container; run Alembic from CI or a trusted host)."

cd /app

exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 2 \
    --loop uvloop \
    --http httptools \
    --log-level info
