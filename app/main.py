"""VOK - Video downloader and content scraper. Entry point."""

import sys

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication
from qfluentwidgets import setThemeColor

from app.ui.main_window import MainWindow


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

    setThemeColor("#0078D4")

    window = MainWindow()
    window.show()

    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
