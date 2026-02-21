__version__ = "0.1.0"

from .dashboard import DashboardView
from .downloader import DownloaderView
from .logs import LogsView
from .scraper import ScraperView
from .settings import SettingsView

__all__ = ["DashboardView", "DownloaderView", "LogsView", "ScraperView", "SettingsView"]
