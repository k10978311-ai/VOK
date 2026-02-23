#!/usr/bin/env bash
# VOK — Format Python code (ruff format).
# Run from project root: ./scripts/format.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

if ! command -v ruff &>/dev/null; then
    [ -d ".venv" ] && export PATH="$ROOT_DIR/.venv/bin:$PATH"
    uv sync --extra dev 2>/dev/null || true
fi

if ! command -v ruff &>/dev/null; then
    echo "[ERROR] Ruff not found. Run: uv sync --extra dev"
    exit 1
fi

echo "Formatting with ruff..."
ruff format .
echo "Done."
