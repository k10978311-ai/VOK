"""
Dashboard view — welcome screen for VOK Downloader.
"""

import os
import platform
import subprocess
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QVBoxLayout
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    CardWidget,
    FluentIcon,
    SubtitleLabel,
    IconWidget,
)

from app.common.paths import INSTRUCTIONS_DIR
from app.config import load_settings
from app.ui.components.home_banner import HomeBanner

from .base import BaseView

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SECTION_SPACING   = 20
CARD_PADDING      = 16
FEATURE_ICON_SIZE = 32
GRID_SPACING      = 14

FEATURE_TOOLS = (
    ("Multi-Source Support", "1000+ sites: YouTube, TikTok, Pinterest & more.", FluentIcon.GLOBE),
    ("Quality Selector",     "Pick 4K, 1080p, 720p or audio-only (MP3/M4A).",  FluentIcon.SETTING),
    ("Batch Download",       "Paste multiple URLs or an entire playlist.",       FluentIcon.ADD),
    ("Smart File Naming",    "Files saved by title/channel automatically.",      FluentIcon.EDIT),
)

HOW_TO_STEPS = (
    "1. Copy a video URL from your browser.",
    "2. Go to the Download tab, paste the URL, and choose your format.",
    "3. Click Download — track progress in the Logs tab.",
)


class DashboardView(BaseView):
    """Home / Dashboard view for VOK Downloader."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Dashboard")
        self._build_ui()

    def _build_ui(self):
        """Build dashboard sections in order."""
        self._add_banner()
        self._add_feature_grid()
        self._add_instructions_card()
        self._layout.addStretch(1)

    def _add_banner(self):
        """Full-width hero banner."""
        banner = HomeBanner(self)
        banner.open_folder_requested.connect(self._open_download_folder)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.addWidget(banner)

    def _add_feature_grid(self):
        """2x2 grid of feature/tool cards."""
        self._layout.setContentsMargins(24, 20, 24, 24)
        self._layout.addWidget(SubtitleLabel("Included Tools & Features"))

        grid = QGridLayout()
        grid.setContentsMargins(10, 10, 10, 10)
        grid.setSpacing(GRID_SPACING)

        for i, (title, desc, icon) in enumerate(FEATURE_TOOLS):
            grid.addWidget(
                self._make_feature_card(title, desc, icon),
                i // 2,
                i % 2,
            )

        self._layout.addLayout(grid)
        self._layout.addSpacing(SECTION_SPACING)

    def _make_feature_card(self, title, desc, icon):
        """Build a single feature card with icon, title, and description."""
        card = CardWidget(self)
        root = QVBoxLayout(card)
        root.setSpacing(8)

        icon_w = IconWidget(icon, card)
        icon_w.setFixedSize(FEATURE_ICON_SIZE, FEATURE_ICON_SIZE)
        root.addWidget(icon_w)

        title_lbl = SubtitleLabel(title, card)
        root.addWidget(title_lbl)

        desc_lbl = CaptionLabel(desc, card)
        desc_lbl.setWordWrap(True)
        root.addWidget(desc_lbl)

        root.addStretch(1)
        return card

    def _add_instructions_card(self):
        """How-to-use card with steps and optional images."""
        card = CardWidget(self)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(CARD_PADDING + 4, CARD_PADDING + 4, CARD_PADDING + 4, CARD_PADDING + 4)
        layout.setSpacing(12)
        layout.addWidget(SubtitleLabel("How to use", card))
        layout.addSpacing(4)

        for text in HOW_TO_STEPS:
            lbl = BodyLabel(text, card)
            lbl.setWordWrap(True)
            layout.addWidget(lbl)

        self._add_instruction_images(layout, card)
        self._layout.addWidget(card)

    def _add_instruction_images(self, layout: QVBoxLayout, parent):
        """Append instruction images from resources/instructions/ if present."""
        if not INSTRUCTIONS_DIR.exists():
            return
        for i in range(1, 10):
            for ext in (".png", ".jpg", ".jpeg"):
                path = INSTRUCTIONS_DIR / f"step{i}{ext}"
                if path.exists():
                    pix = QPixmap(str(path))
                    if not pix.isNull():
                        label = QLabel(parent)
                        label.setPixmap(
                            pix.scaledToWidth(560, Qt.SmoothTransformation)
                        )
                        label.setAlignment(Qt.AlignCenter)
                        layout.addWidget(label)
                    break

    def _open_download_folder(self):
        path = load_settings().get("download_path", "")
        target = (
            Path(path)
            if path and Path(path).exists()
            else Path.home() / "Downloads"
        )
        if not target.exists():
            return
        path_str = str(target)
        try:
            if platform.system() == "Darwin":
                subprocess.run(["open", path_str], check=False)
            elif platform.system() == "Windows":
                os.startfile(path_str)
            else:
                subprocess.run(["xdg-open", path_str], check=False)
        except Exception:
            pass