"""HomeBanner — hero banner for the Dashboard view."""

from __future__ import annotations

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QBrush, QColor, QLinearGradient, QPainter, QPainterPath
from PyQt5.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel,
    FluentIcon,
    TitleLabel,
)

from app.ui.components.studio_banner import FeatureTile


class HomeBanner(QWidget):
    """Hero banner for the Dashboard view.

    Signals
    -------
    open_downloader_requested : "Download" tile clicked
    open_logs_requested       : "Logs" tile clicked
    open_settings_requested   : "Settings" tile clicked
    """

    open_downloader_requested = pyqtSignal()
    open_logs_requested       = pyqtSignal()
    open_settings_requested   = pyqtSignal()
    open_folder_requested     = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(260)
        self._setup_content()

    # ── build ─────────────────────────────────────────────────────────────────

    def _setup_content(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(36, 32, 36, 28)
        root.setSpacing(0)

        # title + subtitle
        title = TitleLabel("VOK Downloader", self)
        title.setStyleSheet("font-size: 32px; font-weight: 700; color: white;")
        root.addWidget(title)

        sub = BodyLabel(
            "Download from YouTube, TikTok, Pinterest & 1000+ platforms — fast, offline, free.",
            self,
        )
        sub.setStyleSheet("color: rgba(255,255,255,0.72); font-size: 13px;")
        root.addWidget(sub)

        root.addStretch(1)

        # quick-nav tiles
        tiles_row = QHBoxLayout()
        tiles_row.setSpacing(12)
        tiles_row.setContentsMargins(0, 20, 0, 0)

        tile_download = FeatureTile(
            FluentIcon.DOWNLOAD, "Download", "Paste a URL and start", self
        )
        tile_logs = FeatureTile(
            FluentIcon.FOLDER, "Logs", "View downloaded files", self
        )
        tile_settings = FeatureTile(
            FluentIcon.SETTING, "Settings", "Configure the app", self
        )
        tile_folder = FeatureTile(
            FluentIcon.FOLDER_ADD, "Open Folder", "Browse your downloads", self
        )

        tile_download.clicked.connect(self.open_downloader_requested)
        tile_logs.clicked.connect(self.open_logs_requested)
        tile_settings.clicked.connect(self.open_settings_requested)
        tile_folder.clicked.connect(self.open_folder_requested)

        for tile in (tile_download, tile_logs, tile_settings, tile_folder):
            tiles_row.addWidget(tile)
        tiles_row.addStretch(1)
        root.addLayout(tiles_row)

    # ── paint ─────────────────────────────────────────────────────────────────

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()

        # dark base
        painter.fillRect(self.rect(), QColor("#1a1a1a"))

        # purple gradient overlay on the right half
        grad = QLinearGradient(w * 0.35, 0, w, h)
        grad.setColorAt(0.0, QColor(0, 0, 0, 0))
        grad.setColorAt(0.5, QColor("#4a1a7a"))
        grad.setColorAt(1.0, QColor("#2d0f5e"))
        painter.fillRect(self.rect(), QBrush(grad))

        # smooth wave ribbons (3 layered paths)
        wave_colors = [
            QColor(120, 60, 200, 80),
            QColor(90,  40, 170, 55),
            QColor(150, 80, 220, 40),
        ]
        offsets = [
            (0.55, 0.10, 0.75, -0.15, 0.95, 0.35, 1.15, 0.05),
            (0.60, 0.45, 0.78, 0.10, 0.92, 0.60, 1.10, 0.30),
            (0.50, 0.70, 0.72, 0.35, 0.90, 0.85, 1.05, 0.55),
        ]
        for color, (x0, y0, x1, y1, x2, y2, x3, y3) in zip(wave_colors, offsets):
            path = QPainterPath()
            path.moveTo(w * x0, h * y0)
            path.cubicTo(w * x1, h * y1, w * x2, h * y2, w * x3, h * y3)
            path.lineTo(w * 1.2, h * 1.2)
            path.lineTo(w * 0.4, h * 1.2)
            path.closeSubpath()
            painter.fillPath(path, QBrush(color))

        painter.end()
