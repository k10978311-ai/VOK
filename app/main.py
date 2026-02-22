"""VOK - Video downloader and content scraper. Entry point."""

import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QIcon
from PyQt5.QtWidgets import QApplication
from qfluentwidgets import Theme, setTheme, setThemeColor, FluentIcon, SplashScreen

from app.common.paths import PROJECT_ROOT
from app.config import is_first_run, load_settings
from app.ui.dialogs import SetupWizardDialog
from app.ui.main_window import MainWindow

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

    s = load_settings()
    setTheme(_THEME_MAP.get(s.get("theme", "Dark"), Theme.DARK))
    setThemeColor(QColor(s.get("theme_color", "#0078D4")))

    window = MainWindow()

    logo_path = PROJECT_ROOT / "resources" / "logo.png"
    splash_icon = QIcon(str(logo_path)) if logo_path.exists() else FluentIcon.DOWNLOAD
    splash = SplashScreen(splash_icon, parent=window, enableShadow=True)
    window.show()
    splash.show()
    app.processEvents()

    if is_first_run():
        splash.finish()
        setup = SetupWizardDialog()
        setup.exec_()
        s = load_settings()
        setTheme(_THEME_MAP.get(s.get("theme", "Dark"), Theme.DARK))
        setThemeColor(QColor(s.get("theme_color", "#0078D4")))

    splash.finish()

    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
