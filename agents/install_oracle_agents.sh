#!/bin/bash
# install_oracle_agents.sh
# Run this from your repo root to install all ORACLE custom agents into Claude Code.
# Usage: bash install_oracle_agents.sh

AGENTS_DIR="$HOME/.claude/agents"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Installing ORACLE custom agents to $AGENTS_DIR"
echo "================================================"

# Create agents directory if it doesn't exist
mkdir -p "$AGENTS_DIR"

# Copy all oracle agents
agents=(
  "oracle-contamination-purger.md"
  "oracle-feature-wirer.md"
  "oracle-ml-integrity-auditor.md"
  "oracle-refactorer.md"
  "oracle-deploy-readiness.md"
  "oracle-alembic-surgeon.md"
)

for agent in "${agents[@]}"; do
  src="$SCRIPT_DIR/$agent"
  dst="$AGENTS_DIR/$agent"
  if [ -f "$src" ]; then
    cp "$src" "$dst"
    echo "✅ Installed: $agent"
  else
    echo "❌ Missing:   $agent (not found at $src)"
  fi
done

echo ""
echo "================================================"
echo "Installed agents:"
ls "$AGENTS_DIR"/oracle-*.md 2>/dev/null | xargs -I{} basename {}

echo ""
echo "All agents:"
ls "$AGENTS_DIR"/*.md 2>/dev/null | wc -l
echo "agent files in $AGENTS_DIR"

echo ""
echo "How to invoke in Claude Code:"
echo "  /agent oracle-contamination-purger  — remove all anthropic/LLM code"
echo "  /agent oracle-feature-wirer         — wire feature engineering pipeline"
echo "  /agent oracle-ml-integrity-auditor  — validate 34x3 score matrix + no LLMs"
echo "  /agent oracle-refactorer            — split god files, add Pydantic models"
echo "  /agent oracle-deploy-readiness      — pre-deploy GO/NO-GO checklist"
echo "  /agent oracle-alembic-surgeon       — fix migration chain"
