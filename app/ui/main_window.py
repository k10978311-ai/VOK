from PyQt5.QtCore import Qt, QThread
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
from PyQt5.QtSql import QSqlDatabase
from qfluentwidgets import NavigationItemPosition, MSFluentWindow, FluentIcon, MessageBox

import app
from app.common.paths import PROJECT_ROOT
from app.common.database import DBInitializer, DatabaseThread, sqlSignalBus, SqlResponse
from app.common.signal_bus import signal_bus
from app.common.logger import Logger
from app.common.exit_app import initialize_exit_handler, ExitHandler
from app.config import load_settings
from ..common.icon import Icon
from ..common import resource
from .views import BatchEnhanceInterface, CliperInterface, DashboardView, DownloaderView, M3u8Interface, SettingsView, TaskInterface, AboutInterface
from app.ui.components.system_tray_icon import SystemTrayIcon
class MainWindow(MSFluentWindow):
    """Fluent-style window with download and analytics tools."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = Logger("main_window")
        
        # Initialize exit handler
        self.exit_handler = None  # Will be set after window is fully initialized
        
        self.initDatabase()
        self.initWindow()

        self.dashboard = DashboardView(self)
        self.downloader = DownloaderView(self)
        self.taskInterface = TaskInterface(self)
        self.batchEnhance = BatchEnhanceInterface(self)
        self.clipper = CliperInterface(self)
        self.m3u8Download = M3u8Interface(self)
        self.systemTrayIcon = SystemTrayIcon(self)
        # self.studio = VokStudioView(self)
        # self.logs = LogsView(self)
        self.about = AboutInterface(self)
        self.settings = SettingsView(self)

        self.addSubInterface(self.dashboard, FluentIcon.HOME, "Home")
        self.addSubInterface(self.downloader, FluentIcon.DOWNLOAD, "Download")
        self.addSubInterface(self.batchEnhance, FluentIcon.ZOOM_IN, "BE")
        # self.addSubInterface(self.clipper, FluentIcon.CUT, "Clipper")
        # self.addSubInterface(self.m3u8Download, FluentIcon.LINK, "M3U8")
        self.addSubInterface(self.taskInterface, Icon.CLOUD_DOWNLOAD, "Tasks")

        self.addSubInterface(
            self.about,
            FluentIcon.INFO,
            "About",
            position=NavigationItemPosition.BOTTOM,
        )
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
        elif default_page == "About":
            self.switchTo(self.about)
        else:
            self.switchTo(self.downloader)

        self.connectSignalToSlot()
        
        # Initialize exit handler after all components are created
        initialize_exit_handler(self)
        self.exit_handler = ExitHandler(self)

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

    def initDatabase(self):
        """Open the SQLite database and start the async DB thread."""
        DBInitializer.init()
        self.databaseThread = DatabaseThread(
            QSqlDatabase.database(DBInitializer.CONNECTION_NAME), self
        )
        sqlSignalBus.dataFetched.connect(self.onDataFetched)

    def connectSignalToSlot(self):
        """Connect application-wide signals to window slots."""
        signal_bus.app_message.connect(self.onAppMessage)
        signal_bus.app_error.connect(self.onAppError)

    # ── Signal handlers ──────────────────────────────────────────────────

    def onDataFetched(self, response: SqlResponse):
        """Route async SQL result to the requesting callback."""
        if response.slot:
            response.slot(response.data)

    def onAppMessage(self, message: str):
        """Raise window on 'show' message (e.g. second instance launched)."""
        if message == "show":
            if self.windowState() & Qt.WindowMinimized:
                self.showNormal()
            else:
                self.show()
                self.raise_()
        else:
            self.switchTo(self.downloader)
            self.show()
            self.raise_()

    def onAppError(self, message: str):
        """Show unhandled-exception dialog and copy error to clipboard."""
        QApplication.clipboard().setText(message)
        w = MessageBox(
            "Unhandled exception occurred",
            "The error has been copied to the clipboard and written to the log.",
            self,
        )
        w.cancelButton.setText("Close")
        w.yesButton.hide()
        w.buttonLayout.insertStretch(0, 1)
        w.exec()

    # ── Window lifecycle ─────────────────────────────────────────────────

    def closeEvent(self, event):
        """Handle window close event - show confirmation dialog or hide to tray."""
        # Check if this is a forced shutdown (Alt+F4, X button with Shift, etc.)
        modifiers = QApplication.keyboardModifiers()
        
        # Load settings to check close-to-tray behavior
        from app.config import load_settings
        settings = load_settings()
        close_to_tray = settings.get("close_to_system_tray", True)
        
        if modifiers & Qt.ShiftModifier:
            # Force exit when Shift is held during close - show confirmation
            if self.exit_handler and self.exit_handler.request_exit_with_confirmation(self, "shift_close"):
                event.accept()
            else:
                self.logger.info("User cancelled exit, hiding to tray")
                event.ignore()
                self.hide()
        else:
            # Normal close behavior based on settings
            if close_to_tray:
                # Hide to system tray (default behavior)
                self.logger.info("Window closed, hiding to system tray")
                event.ignore()
                self.hide()
            else:
                # Exit application directly (with confirmation if enabled)
                if self.exit_handler and self.exit_handler.request_exit_with_confirmation(self, "window_close"):
                    event.accept()
                else:
                    # User cancelled exit, stay open
                    event.ignore()

    def onExit(self):
        """Perform application exit using the centralized exit handler."""
        if self.exit_handler:
            self.exit_handler.perform_exit()
        else:
            # Fallback if exit handler not initialized
            self.logger.warning("Exit handler not initialized, using fallback exit")
            QApplication.instance().quit()
