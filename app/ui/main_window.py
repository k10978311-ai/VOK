from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
from PyQt5.QtSql import QSqlDatabase
from qfluentwidgets import (
    FluentIcon,
    MessageBox,
    MSFluentWindow,
    NavigationItemPosition,
)

import app
from app.common.paths import PROJECT_ROOT
from app.common.database import DBInitializer, DatabaseThread, sqlSignalBus, SqlResponse
from app.common.signal_bus import signal_bus
from app.common.logger import Logger
from app.common.exit_app import initialize_exit_handler, ExitHandler
from app.config import load_settings
from app.ui.components.system_tray_icon import SystemTrayIcon

from ..common.icon import Icon
from ..common import resource

from .views import (
    AboutInterface,
    BatchEnhanceInterface,
    HomeInterface,
    SettingsView,
    TaskInterface,
)

# Window geometry
INITIAL_WIDTH, INITIAL_HEIGHT = 1200, 840
MIN_WIDTH, MIN_HEIGHT = 900, 840


class MainWindow(MSFluentWindow):
    """Fluent-style window with download and analytics tools."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = Logger("main_window")
        self.exit_handler = None

        self._init_database()
        self._init_window()
        self._create_views()
        self._setup_navigation()
        self._apply_default_page()
        self._connect_signals()

        initialize_exit_handler(self)
        self.exit_handler = ExitHandler(self)

    def _create_views(self):
        """Create and hold references to all sub-interfaces."""
        self.home = HomeInterface(self)
        self.taskInterface = TaskInterface(self)
        self.batchEnhance = BatchEnhanceInterface(self)
        self.about = AboutInterface(self)
        self.settings = SettingsView(self)
        self.systemTrayIcon = SystemTrayIcon(self)

    def _setup_navigation(self):
        """Register sub-interfaces with the navigation panel."""
        self.addSubInterface(self.home, FluentIcon.HOME, "Home")
        self.addSubInterface(self.batchEnhance, FluentIcon.ZOOM_IN, "Batch En..")
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

    def _apply_default_page(self):
        """Switch to the start page from settings."""
        page = load_settings().get("default_start_page", "Home")
        default_widgets = {
            "Dashboard": self.home,
            "Home": self.home,
            "Settings": self.settings,
            "About": self.about,
        }
        widget = default_widgets.get(page, self.home)
        self.switchTo(widget)

    def _init_window(self):
        """Initialize window size, title, icon, and position."""
        self.resize(INITIAL_WIDTH, INITIAL_HEIGHT)
        self.setMinimumSize(MIN_WIDTH, MIN_HEIGHT)
        self.setWindowTitle(f"VOK — Download (v{app.__version__})")

        logo_path = PROJECT_ROOT / "resources" / "icon.ico"
        if logo_path.exists():
            self.setWindowIcon(QIcon(str(logo_path)))

        desktop = QApplication.desktop().availableGeometry()
        self.move(
            desktop.width() // 2 - self.width() // 2,
            desktop.height() // 2 - self.height() // 2,
        )

    def _init_database(self):
        """Open the SQLite database and start the async DB thread."""
        DBInitializer.init()
        self.databaseThread = DatabaseThread(
            QSqlDatabase.database(DBInitializer.CONNECTION_NAME), self
        )
        sqlSignalBus.dataFetched.connect(self.onDataFetched)

    def _connect_signals(self):
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
            self.switchTo(self.home)
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
        """Handle window close: hide to tray or exit based on settings and modifiers."""
        modifiers = QApplication.keyboardModifiers()
        close_to_tray = load_settings().get("close_to_system_tray", True)
        
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
