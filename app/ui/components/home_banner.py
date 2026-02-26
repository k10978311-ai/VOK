"""HomeBanner — hero banner for the Dashboard view."""

from __future__ import annotations

from PyQt5.QtCore import Qt, QSize, pyqtSignal
from PyQt5.QtGui import QBrush, QColor, QIcon, QLinearGradient, QPainter, QPainterPath, QPixmap
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel,
    FluentIcon,
    TitleLabel,
    TransparentToolButton,
    isDarkTheme,
    qconfig,
)

from app.common.paths import RESOURCES_DIR
from app.ui.components.studio_banner import FeatureTile


class HomeBanner(QWidget):
    """Hero banner for the Dashboard view."""

    open_downloader_requested = pyqtSignal()
    open_logs_requested       = pyqtSignal()
    open_settings_requested   = pyqtSignal()
    open_youtube_link         = pyqtSignal()
    open_github               = pyqtSignal()
    open_folder_requested     = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(290)
        self._title: TitleLabel | None = None
        self._sub: BodyLabel | None = None
        self._setup_content()
        qconfig.themeChanged.connect(self._on_theme_changed)

    def _setup_content(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(36, 28, 36, 28)
        root.setSpacing(0)

        # ── Top row with title and GitHub link ─────────────────────────────────────
        top_row = QHBoxLayout()
        # top_row.setSpacing(8)

        self._title = TitleLabel("VOK Downloader", self)
        self._title.setStyleSheet("font-size: 32px; font-weight: 700;")
        top_row.addWidget(self._title)
        top_row.addStretch(1)

        self._github_btn = TransparentToolButton(self)
        self._github_btn.setIcon(QIcon(str(RESOURCES_DIR / "icons" / "github_filde.png")))
        self._github_btn.setIconSize(QSize(28, 28))
        self._github_btn.setToolTip("View on GitHub")
        self._github_btn.setFixedSize(48, 48)
        self._github_btn.clicked.connect(self.open_github)
        top_row.addWidget(self._github_btn)

        self._youtube_btn = TransparentToolButton(self)
        self._youtube_btn.setIcon(QIcon(str(RESOURCES_DIR / "icons" / "youtube.png")))
        self._youtube_btn.setIconSize(QSize(28, 28))
        self._youtube_btn.setToolTip("Watch tutorial on YouTube")
        self._youtube_btn.setFixedSize(48, 48)
        self._youtube_btn.clicked.connect(self.open_youtube_link)
        top_row.addWidget(self._youtube_btn)


        root.addLayout(top_row)
        root.addSpacing(6)

        # ── Subtitle ─────────────────────────────────────────────────────
        self._sub = BodyLabel(
            "Download from YouTube, TikTok, Pinterest & 1000+ platforms — fast, offline, free.",
            self,
        )
        self._sub.setStyleSheet("font-size: 13px;")
        self._sub.setWordWrap(True)
        root.addWidget(self._sub)

        root.addStretch(1)

        # ── Quick-nav tiles (no Settings, no GitHub tile) ─────────────────
        tiles_row = QHBoxLayout()
        tiles_row.setSpacing(12)
        tiles_row.setContentsMargins(0, 20, 20, 20)

        tile_download = FeatureTile(
            FluentIcon.DOWNLOAD, "Download", "Paste a URL and start", self
        )
        tile_logs = FeatureTile(
            FluentIcon.FOLDER, "Logs", "View downloaded files", self
        )
        tile_folder = FeatureTile(
            FluentIcon.FOLDER_ADD, "Open Folder", "Browse your downloads", self
        )

        tile_download.clicked.connect(self.open_downloader_requested)
        tile_logs.clicked.connect(self.open_logs_requested)
        tile_folder.clicked.connect(self.open_folder_requested)

        for tile in (tile_download, tile_logs, tile_folder):
            tiles_row.addWidget(tile)
        tiles_row.addStretch(1)
        root.addLayout(tiles_row)

        self._update_label_colors()

    def _on_theme_changed(self, _theme=None) -> None:
        self._update_label_colors()
        self.update()

    def _update_label_colors(self) -> None:
        dark = isDarkTheme()
        light_title  = QColor("#1a1a1a")
        dark_title   = QColor("white")
        light_sub    = QColor(30, 30, 30, 170)
        dark_sub     = QColor(255, 255, 255, 184)

        if self._title is not None:
            self._title.setTextColor(light_title, dark_title)
            self._title.setStyleSheet(
                f"font-size: 32px; font-weight: 700;"
                f" color: {'white' if dark else '#1a1a1a'};"
            )
        if self._sub is not None:
            self._sub.setTextColor(light_sub, dark_sub)
            self._sub.setStyleSheet(
                f"font-size: 13px;"
                f" color: {'rgba(255,255,255,0.72)' if dark else 'rgba(20,20,20,0.66)'};"
            )

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        dark = isDarkTheme()

        # base fill
        painter.fillRect(self.rect(), QColor("#1a1a1a") if dark else QColor("#f2f0f8"))

        # gradient overlay on the right two-thirds
        grad = QLinearGradient(w * 0.30, 0, w, h)
        if dark:
            grad.setColorAt(0.0, QColor(0, 0, 0, 0))
            grad.setColorAt(0.45, QColor("#3d1569"))
            grad.setColorAt(1.0, QColor("#1e0940"))
        else:
            grad.setColorAt(0.0, QColor(255, 255, 255, 0))
            grad.setColorAt(0.45, QColor(200, 180, 240, 200))
            grad.setColorAt(1.0, QColor(170, 140, 225, 230))
        painter.fillRect(self.rect(), QBrush(grad))

        # smooth wave ribbons (3 layered paths)
        if dark:
            wave_colors = [
                QColor(120, 60, 200, 80),
                QColor(90,  40, 170, 55),
                QColor(150, 80, 220, 40),
            ]
        else:
            wave_colors = [
                QColor(120, 70, 200, 38),
                QColor(90,  50, 175, 28),
                QColor(150, 90, 220, 22),
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
