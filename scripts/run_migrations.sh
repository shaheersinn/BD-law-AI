#!/usr/bin/env bash
# run_migrations.sh — Manual Alembic migration runner for ORACLE production.
#
# IMPORTANT: This script must NEVER be called automatically from CI/CD pipelines
# or container startup commands. It is a deliberate, manual operation.
#
# Usage:
#   CONFIRM=yes DATABASE_URL=postgresql+asyncpg://... bash scripts/run_migrations.sh
#
# Prerequisites:
#   1. Set DATABASE_URL to the production database connection string
#   2. Run this from the repository root
#   3. Ensure you have a recent database backup before running
#
# Rollback:
#   alembic downgrade -1                  # roll back one revision
#   alembic downgrade <revision_id>       # roll back to specific revision
#   alembic history                       # view revision history

set -euo pipefail

# ── Safety gate ───────────────────────────────────────────────────────────────

if [[ "${CONFIRM:-}" != "yes" ]]; then
  echo ""
  echo "ERROR: Set CONFIRM=yes to run migrations against the target database."
  echo ""
  echo "  CONFIRM=yes DATABASE_URL=<url> bash scripts/run_migrations.sh"
  echo ""
  echo "This script applies all pending Alembic migrations. It is a potentially"
  echo "destructive operation — always take a database backup first."
  echo ""
  exit 1
fi

# ── Validate environment ───────────────────────────────────────────────────────

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "ERROR: DATABASE_URL is not set. Export the production database URL before running."
  exit 1
fi

# ── Run migrations ─────────────────────────────────────────────────────────────

echo ""
echo "=== ORACLE Alembic Migration Runner ==="
echo "Target: ${DATABASE_URL%%@*}@****  (credentials redacted)"
echo ""

# Navigate to backend directory where alembic.ini lives
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$REPO_ROOT/backend"

echo "Current migration head:"
alembic current

echo ""
echo "Pending migrations:"
alembic history --indicate-current | head -20

echo ""
echo "Applying migrations..."
alembic upgrade head

echo ""
echo "Migration complete. Current head:"
alembic current
echo ""
echo "Done."
