#!/bin/bash
# run_migrations.sh — Run Alembic migrations against the target DATABASE_URL.
#
# Usage:
#   DATABASE_URL="postgresql+asyncpg://user:pass@host/db" bash scripts/run_migrations.sh
#   DATABASE_URL="postgresql+asyncpg://user:pass@host/db" bash scripts/run_migrations.sh --dry-run
#
# The script strips asyncpg from DATABASE_URL because Alembic uses psycopg2 (sync).
# Alembic's env.py also does this internally, so either form works.

set -e

if [ -z "$DATABASE_URL" ]; then
  echo "ERROR: DATABASE_URL environment variable is required."
  echo "Example: DATABASE_URL=postgresql+asyncpg://user:pass@host/db bash scripts/run_migrations.sh"
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

echo "=== ORACLE Migration Runner ==="
echo "Target: ${DATABASE_URL%%@*}@*** (credentials redacted)"
echo "Alembic head revision:"
python -m alembic heads

if [ "${1}" = "--dry-run" ]; then
  echo ""
  echo "DRY RUN — SQL that would be executed:"
  python -m alembic upgrade head --sql
  echo ""
  echo "Dry run complete. No changes applied."
else
  echo ""
  echo "Applying migrations..."
  python -m alembic upgrade head
  echo ""
  echo "Verifying current head:"
  python -m alembic current
  echo "Migration complete."
fi
