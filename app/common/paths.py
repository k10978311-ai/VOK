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
INSTRUCTIONS_DIR = RESOURCES_DIR / "instructions"
TRANSLATIONS_DIR = RESOURCES_DIR / "translations"
DOWNLOADS_DIR = PROJECT_ROOT / "downloads"

# AppData sub-folders (writable, not part of source tree)
APPDATA_DIR = PROJECT_ROOT / "AppData"
CACHE_DIR = APPDATA_DIR / "cache"
LOG_DIR = APPDATA_DIR / "log"
MODELS_DIR = APPDATA_DIR / "models"


def get_config_dir() -> Path:
    """Writable config dir: AppData/ beside project root in dev, OS app-data when frozen."""
    if getattr(sys, "frozen", False):
        if sys.platform == "darwin":
            base = Path.home() / "Library" / "Application Support" / "VOK"
        elif sys.platform == "win32":
            base = Path(os.environ.get("APPDATA", Path.home())) / "VOK"
        else:
            base = Path.home() / ".config" / "VOK"
    else:
        base = APPDATA_DIR
    base.mkdir(parents=True, exist_ok=True)
    return base


# Subfolder under user's Downloads used when no custom path is set
VOK_VIDEO_SUBFOLDER = "Vok_Video"


def get_default_downloads_dir() -> Path:
    """Default download folder: user's Downloads\\Vok_Video (created if missing).
    Used on first start and whenever no download_path is set.
    """
    path = Path.home() / "Downloads" / VOK_VIDEO_SUBFOLDER
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_log_dir() -> Path:
    """Log directory under config dir (e.g. AppData/log)."""
    path = get_config_dir() / "log"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_db_path() -> Path:
    """Database file path under config dir (e.g. AppData/database.db)."""
    return get_config_dir() / "database.db"


def get_cover_folder() -> Path:
    """Cover/thumbnails folder under config dir (e.g. AppData/Cover)."""
    path = get_config_dir() / "Cover"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_host_icons_cache_dir() -> Path:
    """Cache directory for host/favicon icons (e.g. AppData/host_icons)."""
    path = get_config_dir() / "host_icons"
    path.mkdir(parents=True, exist_ok=True)
    return path
