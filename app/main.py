"""VOK - Video downloader and content scraper. Entry point."""

import sys
import signal
import atexit

from PyQt5.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QIcon
from PyQt5.QtWidgets import QApplication
from qfluentwidgets import Theme, setTheme, setThemeColor, FluentIcon, InfoBar, InfoBarPosition, SplashScreen, qconfig
from app import bootstrap
from app.common.application import SingletonApplication, exception_hook  # noqa: F401 — installs sys.excepthook

from app.common.paths import PROJECT_ROOT, APPDATA_DIR
from app.common.i18n import apply_language, LANGUAGES
from app.config import load_settings
from app.ui.main_window import MainWindow
from app.ui.theme import apply_app_palette

# Global reference to main window for cleanup
_main_window = None


class _StartupUpdateChecker(QThread):
    """Background update check run once at startup."""
    update_found = pyqtSignal(str, str)  # (version, download_url)

    def __init__(self, current_version: str, parent=None):
        super().__init__(parent)
        self._current = current_version

    def run(self):
        from app.core.updater import check_update
        version, url = check_update(self._current)
        if version and url:
            self.update_found.emit(version, url)

_THEME_MAP = {"Auto": Theme.AUTO, "Light": Theme.LIGHT, "Dark": Theme.DARK}


def main() -> int:
    """Run the application."""
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    from app import __version__
    app = SingletonApplication(sys.argv, "VOK")
    app.setApplicationName("VOK")
    app.setApplicationDisplayName(f"VOK - Video Downloader (v{__version__})")
    app.setStyle("Fusion")

    # ── Translations ──────────────────────────────────────────────────────
    _lang_pref = load_settings().get("language", "Auto (System)")
    _locale_str = LANGUAGES.get(_lang_pref, "")
    apply_language(_locale_str)

    # Redirect QFluentWidgets internal config to AppData/ so config/ folder is not needed.
    qconfig.FILE = APPDATA_DIR / "config.json"

    s = load_settings()
    theme_name = s.get("theme", "Dark")
    theme_color = s.get("theme_color", "#0078D4")
    setTheme(_THEME_MAP.get(theme_name, Theme.DARK))
    setThemeColor(QColor(theme_color))
    apply_app_palette(theme_name, theme_color)

    # Setup signal handlers for graceful shutdown
    def cleanup_handler():
        if '_main_window' in globals() and _main_window:
            try:
                # Use the organized exit handler if available
                if hasattr(_main_window, 'exit_handler') and _main_window.exit_handler:
                    _main_window.exit_handler.perform_exit(force=True)
                else:
                    _main_window.onExit()
            except Exception as e:
                print(f"Error during cleanup: {e}")
                sys.exit(1)
    
    def signal_handler(signum, frame):
        print(f"\nReceived signal {signum}, performing cleanup...")
        cleanup_handler()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    atexit.register(cleanup_handler)

    window = MainWindow()
    global _main_window
    _main_window = window

    logo_path = PROJECT_ROOT / "resources" / "logo.png"
    splash_icon = QIcon(str(logo_path)) if logo_path.exists() else FluentIcon.DOWNLOAD
    splash = SplashScreen(splash_icon, parent=window, enableShadow=True)
    window.show()
    splash.show()
    app.processEvents()

    QTimer.singleShot(1000, splash.close)

    # Startup auto-update check (silent — shows InfoBar only if update found)
    if s.get("auto_update_on_start", True):
        _checker = _StartupUpdateChecker(__version__, parent=window)

        def _on_update_found(version: str, url: str) -> None:
            InfoBar.info(
                title=f"Update available: v{version}",
                content="A new version is available. Go to Settings → About to update.",
                isClosable=True,
                duration=8000,
                position=InfoBarPosition.TOP_RIGHT,
                parent=window,
            )

        _checker.update_found.connect(_on_update_found)
        QTimer.singleShot(1500, _checker.start)

    bootstrap.initialize()

    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
