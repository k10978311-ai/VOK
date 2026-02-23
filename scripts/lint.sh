#!/usr/bin/env bash
# VOK — Lint and fix Python code (ruff).
# Run from project root: ./scripts/lint.sh  OR  from scripts/: ./lint.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

echo "=========================================="
echo "  VOK — Lint"
echo "=========================================="
echo ""

# Ensure ruff is available (prefer uv)
if ! command -v ruff &>/dev/null; then
    echo "[INFO] Ruff not in PATH. Syncing dev dependencies..."
    uv sync --extra dev 2>/dev/null || true
    if ! command -v ruff &>/dev/null && [ -d ".venv" ]; then
        export PATH="$ROOT_DIR/.venv/bin:$PATH"
    fi
fi

if ! command -v ruff &>/dev/null; then
    echo "[ERROR] Ruff not found. Install dev deps: uv sync --extra dev"
    echo "        Or: pip install ruff"
    exit 1
fi

echo "[1/3] Remove unused imports (F401)..."
ruff check . --select F401 --fix

echo "[2/3] Sort imports (I)..."
ruff check . --select I --fix

echo "[3/3] Full check (statistics)..."
ruff check . --statistics

echo ""
echo "Done. Tip: ruff check . --fix  for more auto-fixes;  ruff format .  to format."
echo ""
