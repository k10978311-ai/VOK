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
}


def get_default_settings() -> dict:
    """Return a copy of default settings (for reset-to-defaults)."""
    return _DEFAULTS.copy()


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
