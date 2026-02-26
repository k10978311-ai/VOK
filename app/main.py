"""VOK - Video downloader and content scraper. Entry point."""

import sys

from PyQt5.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QIcon
from PyQt5.QtWidgets import QApplication
from qfluentwidgets import Theme, setTheme, setThemeColor, FluentIcon, InfoBar, InfoBarPosition, SplashScreen

from app.common.paths import PROJECT_ROOT
from app.config import load_settings
from app.ui.main_window import MainWindow
from app.ui.theme import apply_app_palette


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
    app = QApplication(sys.argv)
    app.setApplicationName("VOK")
    app.setApplicationDisplayName(f"VOK - Video Downloader (v{__version__})")
    app.setStyle("Fusion")

    s = load_settings()
    theme_name = s.get("theme", "Dark")
    theme_color = s.get("theme_color", "#0078D4")
    setTheme(_THEME_MAP.get(theme_name, Theme.DARK))
    setThemeColor(QColor(theme_color))
    apply_app_palette(theme_name, theme_color)

    window = MainWindow()

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

    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
