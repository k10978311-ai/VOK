"""Settings store: load/save from JSON file and central path constants."""

import json
from pathlib import Path

from app.common.paths import (
    get_config_dir,
    get_cover_folder,
    get_db_path,
    get_default_downloads_dir,
    get_log_dir,
    PROJECT_ROOT,
)

# ── Config / app data paths (used by database, logger, entity) ─────────────────

CONFIG_FOLDER = get_config_dir()
CONFIG_FILE = CONFIG_FOLDER / "vok_settings.json"
DB_PATH = get_db_path()
LOG_FOLDER = get_log_dir()
COVER_FOLDER = get_cover_folder()


def _settings_path() -> Path:
    return CONFIG_FILE


SETTINGS_PATH = _settings_path()

# Legacy path: vok_settings.json was previously saved at the project root.
_LEGACY_SETTINGS_PATH = PROJECT_ROOT / "vok_settings.json"


def is_first_run() -> bool:
    """True if no settings file exists yet (e.g. first install)."""
    return not _settings_path().exists()


def get_settings_path():
    """Return path to settings file (for uninstall/delete)."""
    return _settings_path()


_DEFAULTS = {
    "download_path": str(get_default_downloads_dir()),
    "download_format": "Best (video+audio)",
    "single_video_default": True,
    "theme": "Dark",
    "theme_color": "#F0860D",
    "language": "Auto (System)",
    "concurrent_downloads": 2,
    "concurrent_fragments": 4,
    "cookies_file": "",
    "default_start_page": "Download",
    "sound_alert_on_complete": True,
    "sound_alert_on_error": True,
    "auto_update_on_start": True,
    "auto_reset_link_before_download": True,
    "enhance_keep_original": True,
    "enhance_logo_path": "",
    "enhance_logo_position": "center",
    "enhance_logo_size": 120,
    "enhance_logo_x": 10,
    "enhance_logo_y": 10,
    "enhance_flip": "none",
    "enhance_speed": 1.0,
    "enhance_brightness": 0,
    "enhance_contrast": 0,
    "enhance_saturation": 0,
    "enhance_auto": False,
    "enhance_aspect_ratio": "original",
    "enhance_bg_type": "blur",
    "enhance_bg_color": "#000000",
    "enhance_task_store_history": True,
    
    # Exit application behavior settings
    "exit_confirmation": True,
    "close_to_system_tray": True,
    "exit_timeout_seconds": 3,
}


def get_default_settings() -> dict:
    """Return a copy of default settings (for reset-to-defaults)."""
    return _DEFAULTS.copy()


def _migrate_legacy_settings() -> None:
    
    dest = _settings_path()
    if dest.exists() or not _LEGACY_SETTINGS_PATH.exists():
        return
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(_LEGACY_SETTINGS_PATH.read_bytes())
        _LEGACY_SETTINGS_PATH.unlink(missing_ok=True)
    except OSError:
        pass


def load_settings() -> dict:
    """Load settings from config file (migrates legacy root path on first call)."""
    _migrate_legacy_settings()
    path = _settings_path()
    if not path.exists():
        return _DEFAULTS.copy()
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        out = _DEFAULTS.copy()
        out.update(data)
        return out
    except (json.JSONDecodeError, OSError):
        return _DEFAULTS.copy()


def save_settings(settings: dict) -> None:
    """Persist settings to config file."""
    path = _settings_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
    except OSError:
        pass
