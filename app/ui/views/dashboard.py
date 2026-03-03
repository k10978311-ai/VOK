"""
Dashboard view — welcome screen for VOK Downloader.
"""

from pathlib import Path

import webbrowser

from app.common.paths import get_default_downloads_dir
from app.common.shell import open_path_in_explorer
from app.config import load_settings
from app.ui.components import (
    DashboardFeatureGrid,
    DashboardInstructionsCard,
)
from app.ui.components.home_banner import HomeBanner
from app.ui.dialogs import LogsDialog

from .base import BaseView


class DashboardView(BaseView):
    """Home / Dashboard view for VOK Downloader."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Dashboard"))
        self._build_ui()

    def changeEvent(self, event) -> None:  # type: ignore[override]
        from PyQt5.QtCore import QEvent
        super().changeEvent(event)
        if event.type() == QEvent.LanguageChange:
            self.setWindowTitle(self.tr("Dashboard"))

    CONTENT_MARGINS = (24, 0, 24, 24)

    def _build_ui(self) -> None:
        self._layout.setContentsMargins(*self.CONTENT_MARGINS)

        banner = HomeBanner(self)
        banner.open_folder_requested.connect(self._open_download_folder)
        banner.open_logs_requested.connect(self._open_logs_dialog)
        banner.open_settings_requested.connect(self._open_settings)
        banner.open_downloader_requested.connect(self._open_downloader)
        banner.open_youtube_link.connect(self._open_youtube_link)
        banner.open_github.connect(self._open_github_link)

        self._layout.addWidget(banner)

        self._layout.addWidget(DashboardFeatureGrid(parent=self))
        self._layout.addWidget(DashboardInstructionsCard(parent=self))
        self._layout.addStretch(1)

    def _open_logs_dialog(self) -> None:
        dlg = LogsDialog(self.window())
        dlg.exec_()

    def _open_download_folder(self) -> None:
        path = load_settings().get("download_path", "")
        target = Path(path) if path and Path(path).exists() else get_default_downloads_dir()
        if target.exists():
            open_path_in_explorer(str(target))

    def _open_settings(self) -> None:
        self.window().switchTo(self.window().settings)

    def _open_downloader(self) -> None:
        self.window().switchTo(self.window().downloader)
    
    def _open_github_link(self) -> None:
        webbrowser.open("https://github.com/k10978311-ai/VOK")
    
    def _open_youtube_link(self) -> None:
        webbrowser.open("https://www.youtube.com/@vannyakh/videos")