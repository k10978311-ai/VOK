#!/usr/bin/env bash
# Build VOK for macOS (.app bundle).
# Run from project root: ./scripts/build_mac.sh
# Requires: uv (or pip) and pyinstaller (uv pip install -e ".[dev]" or pip install pyinstaller)

set -e
cd "$(dirname "$0")/.."
echo "========================================"
echo "  VOK — Build for macOS"
echo "========================================"

# Install dev deps (includes PyInstaller)
echo "Syncing dev dependencies..."
uv sync --extra dev

echo "[1/2] Building with PyInstaller..."
uv run pyinstaller vok.spec --clean --noconfirm

if [[ -d "dist/VOK.app" ]]; then
  echo "[2/2] Ad-hoc code signing (required for Apple Silicon / Gatekeeper)..."
  codesign --force --deep --sign - dist/VOK.app
  echo "Build successful!"
  echo ""
  echo "Output: dist/VOK.app"
  echo "Run: open dist/VOK.app"
  echo ""
  echo "Note: This build is ad-hoc signed for local use. For distribution, use an"
  echo "      Apple Developer ID and notarize the app."
else
  echo "[2/2] Build failed."
  exit 1
fi
