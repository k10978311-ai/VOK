"""Project paths. PROJECT_ROOT is the VOK project directory."""

import os
import sys
from pathlib import Path

if getattr(sys, "frozen", False):
    # PyInstaller bundle: use _MEIPASS for read-only assets
    _base = Path(sys._MEIPASS)
else:
    # app/common/paths.py -> app -> VOK
    _base = Path(__file__).resolve().parents[2]

PROJECT_ROOT = _base
APP_ROOT = PROJECT_ROOT / "app"
RESOURCES_DIR = PROJECT_ROOT / "resources"
ICONS_DIR = RESOURCES_DIR / "icons"
DOWNLOADS_DIR = PROJECT_ROOT / "downloads"


def get_config_dir() -> Path:
    """Writable config dir: user app data when frozen, else project root."""
    if getattr(sys, "frozen", False):
        if sys.platform == "darwin":
            base = Path.home() / "Library" / "Application Support" / "VOK"
        elif sys.platform == "win32":
            base = Path(os.environ.get("APPDATA", Path.home())) / "VOK"
        else:
            base = Path.home() / ".config" / "VOK"
        base.mkdir(parents=True, exist_ok=True)
        return base
    return PROJECT_ROOT


def get_default_downloads_dir() -> Path:
    """Default download folder: user's Downloads when frozen, else project downloads."""
    if getattr(sys, "frozen", False):
        return Path.home() / "Downloads"
    return DOWNLOADS_DIR
