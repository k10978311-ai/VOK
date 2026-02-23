from PyQt5.QtWidgets import QApplication
from qfluentwidgets import FluentIcon, FluentWindow, NavigationItemPosition

from app.common.paths import PROJECT_ROOT

from .views import DashboardView, DownloaderView, LogsView, SettingsView

APP_TITLE = "VOK — Download (Version 1.0)"


class MainWindow(FluentWindow):
    """Fluent-style window with download and analytics tools."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.initWindow()

        self.dashboard = DashboardView(self)
        self.downloader = DownloaderView(self)
        self.logs = LogsView(self)
        self.settings = SettingsView(self)

        self.addSubInterface(self.dashboard, FluentIcon.HOME, "Dashboard")
        self.addSubInterface(self.downloader, FluentIcon.DOWNLOAD, "Download")
        self.addSubInterface(self.logs, FluentIcon.FOLDER, "Logs")
        self.navigationInterface.addSeparator()
        self.addSubInterface(
            self.settings,
            FluentIcon.SETTING,
            "Settings",
            position=NavigationItemPosition.BOTTOM,
        )
        self.switchTo(self.downloader)

    def initWindow(self):
        """Initialize window size, title, and position."""
        self.resize(900, 640)
        self.setMinimumSize(720, 480)
        self.setWindowTitle(APP_TITLE)

        logo_path = PROJECT_ROOT / "resources" / "logo.png"
        if logo_path.exists():
            from PyQt5.QtGui import QIcon
            self.setWindowIcon(QIcon(str(logo_path)))

        desktop = QApplication.desktop().availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w // 2 - self.width() // 2, h // 2 - self.height() // 2)
