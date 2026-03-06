from PyQt5.QtWidgets import QApplication
from qfluentwidgets import NavigationItemPosition, MSFluentWindow
from qfluentwidgets import FluentIcon

import app
from app.common.paths import PROJECT_ROOT
from app.config import load_settings

from .views import DashboardView, DownloaderView, SettingsView
from PyQt5.QtGui import QIcon

class MainWindow(MSFluentWindow):
    """Fluent-style window with download and analytics tools."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.initWindow()

        self.dashboard = DashboardView(self)
        self.downloader = DownloaderView(self)
        # self.studio = VokStudioView(self)
        # self.logs = LogsView(self)
        self.settings = SettingsView(self)

        self.addSubInterface(self.dashboard, FluentIcon.HOME, "Dashboard")
        self.addSubInterface(self.downloader, FluentIcon.DOWNLOAD, "Download")
        self.addSubInterface(
            self.settings,
            FluentIcon.SETTING,
            "Settings",
            position=NavigationItemPosition.BOTTOM,
        )

        default_page = load_settings().get("default_start_page", "Download")
        if default_page == "Dashboard":
            self.switchTo(self.dashboard)
        elif default_page == "Settings":
            self.switchTo(self.settings)
        else:
            self.switchTo(self.downloader)

    def initWindow(self):
        """Initialize window size, title, and position."""
        self.resize(1200, 840)
        self.setMinimumSize(900, 840)
        self.setWindowTitle(f"VOK — Download (v{app.__version__})")

        logo_path = PROJECT_ROOT / "resources" / "icon.ico"
        if logo_path.exists():
            self.setWindowIcon(QIcon(str(logo_path)))

        desktop = QApplication.desktop().availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w // 2 - self.width() // 2, h // 2 - self.height() // 2)
