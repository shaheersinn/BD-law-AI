#!/bin/bash
set -e

echo "=== ORACLE API Startup ==="
echo "Running Alembic migrations..."

cd /app

python -m alembic upgrade head

if [ $? -ne 0 ]; then
    echo "ERROR: Alembic migration failed. Aborting startup."
    exit 1
fi

echo "Migrations complete."
echo "Starting API server..."

exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 2 \
    --loop uvloop \
    --http httptools \
    --log-level info
