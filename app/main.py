"""VOK - Video downloader and content scraper. Entry point."""

import sys

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QIcon
from PyQt5.QtWidgets import QApplication
from qfluentwidgets import Theme, setTheme, setThemeColor, FluentIcon, SplashScreen

from app.common.paths import PROJECT_ROOT
from app.config import load_settings
from app.ui.main_window import MainWindow
from app.ui.theme import apply_app_palette

_THEME_MAP = {"Auto": Theme.AUTO, "Light": Theme.LIGHT, "Dark": Theme.DARK}


def main() -> int:
    """Run the application."""
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("VOK")
    app.setApplicationDisplayName("VOK - Video Downloader and Content Scraper")
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

    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
