"""Main window: download tools only."""

from PyQt5.QtWidgets import QApplication
from qfluentwidgets import FluentWindow

from app.common.paths import PROJECT_ROOT

from .views import DownloaderView

APP_TITLE = "VOK — Download"


class MainWindow(FluentWindow):
    """Main window with download tools only (no sidebar)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.downloader = DownloaderView(self)
        self.initWindow()
        self.setCentralWidget(self.downloader)

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
