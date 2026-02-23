"""Config: settings store and setup."""

from app.config.store import get_settings_path, is_first_run, load_settings, save_settings

__all__ = ["get_settings_path", "is_first_run", "load_settings", "save_settings"]
