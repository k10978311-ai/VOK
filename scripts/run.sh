#!/usr/bin/env bash
# VOK — Sync dependencies and run the app (macOS/Linux).
# Run from project root: ./scripts/run.sh  OR  from scripts/: ./run.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'
info()  { echo -e "${BLUE}[INFO]${NC} $1"; }
ok()    { echo -e "${GREEN}[OK]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Ensure we're in project root (run.py + pyproject.toml + app/)
if [ ! -f "$ROOT_DIR/run.py" ] || [ ! -f "$ROOT_DIR/pyproject.toml" ] || [ ! -d "$ROOT_DIR/app" ]; then
    error "Project root not found (expected run.py, pyproject.toml, app/)."
    exit 1
fi

cd "$ROOT_DIR"

echo ""
echo "=========================================="
echo "  VOK — Video Downloader & Scraper"
echo "=========================================="
echo ""

# uv: install if missing
if ! command -v uv &>/dev/null; then
    info "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi
if command -v uv &>/dev/null; then
    ok "uv: $(uv --version 2>/dev/null || true)"
fi

# Sync dependencies
info "Syncing dependencies..."
uv sync
ok "Dependencies ready."
echo ""

# FFmpeg check (recommended for audio/video)
if ! command -v ffmpeg &>/dev/null; then
    warn "FFmpeg not found (recommended for MP3 and merging)."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "  Install: brew install ffmpeg"
    elif command -v apt &>/dev/null; then
        echo "  Install: sudo apt install ffmpeg"
    elif command -v dnf &>/dev/null; then
        echo "  Install: sudo dnf install ffmpeg"
    fi
    echo ""
fi

# Run
info "Starting VOK..."
echo ""
exec uv run run.py
