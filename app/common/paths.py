"""Project paths. PROJECT_ROOT is the VOK project directory."""

from pathlib import Path

# app/common/paths.py -> app -> VOK
PROJECT_ROOT = Path(__file__).resolve().parents[2]
APP_ROOT = PROJECT_ROOT / "app"
RESOURCES_DIR = PROJECT_ROOT / "resources"
DOWNLOADS_DIR = PROJECT_ROOT / "downloads"
