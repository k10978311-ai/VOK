#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
echo "Updating dependencies (uv lock --upgrade)..."
uv lock --upgrade
echo "Syncing environment..."
uv sync
echo "Done."
