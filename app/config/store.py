"""Settings store: load/save from JSON file."""

import json
from pathlib import Path

from app.common.paths import get_config_dir, get_default_downloads_dir



def _settings_path() -> Path:
    return get_config_dir() / "vok_settings.json"


SETTINGS_PATH = _settings_path()


def is_first_run() -> bool:
    """True if no settings file exists yet (e.g. first install)."""
    return not _settings_path().exists()


def get_settings_path():
    """Return path to settings file (for uninstall/delete)."""
    return _settings_path()


_DEFAULTS = {
    "download_path": str(get_default_downloads_dir()),
    "single_video_default": True,
    "theme": "Dark",
    "theme_color": "#0078D4",
    "concurrent_downloads": 2,
    "concurrent_fragments": 4,
    "cookies_file": "",
}


def load_settings() -> dict:
    """Load settings from config file."""
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
