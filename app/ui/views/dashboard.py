"""
Dashboard view: welcome and info tools for video download users.
"""

import os
import platform
import subprocess
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QVBoxLayout

try:
    from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings
    _HAS_WEBENGINE = True
except ImportError:
    QWebEngineView = None
    QWebEngineSettings = None
    _HAS_WEBENGINE = False

from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    CardWidget,
    FluentIcon,
    LargeTitleLabel,
    PrimaryPushButton,
    PushButton,
    SubtitleLabel,
    IconWidget,
)

from app.common.paths import INSTRUCTIONS_DIR
from app.config import load_settings

from .base import BaseView

# --- Constants ---
TUTORIAL_VIDEO_ID = "QXL9TjHS2-I"
TUTORIAL_VIDEO_URL = f"https://www.youtube.com/watch?v={TUTORIAL_VIDEO_ID}"
TUTORIAL_WINDOW_TITLE = "Tutorial Video - របៀបប្រើ Tools Download Video"
SECTION_SPACING = 24
CARD_PADDING = 16
FEATURE_ICON_SIZE = 32
GRID_SPACING = 14

FEATURE_TOOLS = (
    ("Multi-Source Support", "Extract from 1000+ sites with ease.", FluentIcon.GLOBE),
    ("Quality Selector", "Choose up to 4K resolution or MP3 audio.", FluentIcon.SETTING),
    ("Batch Download", "Download entire playlists or multiple URLs.", FluentIcon.ADD),
    ("Smart Naming", "Automatically organize files by title/author.", FluentIcon.EDIT),
)

HOW_TO_STEPS = (
    "1. Copy a video URL from your browser.",
    "2. Paste it into the 'Download' tab and select your format.",
    "3. Click 'Download' and monitor the 'Logs' for status.",
)



class DashboardView(BaseView):
    """Home view for users who download videos with Info Tools grid."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Dashboard")
        self._build_ui()

    def _build_ui(self):
        """Build dashboard sections in order."""
        self._add_header()
        self._add_actions()
        self._add_feature_grid()
        self._add_instructions_card()
        self._layout.addStretch(1)

    def _add_header(self):
        """Title and subtitle."""
        title = LargeTitleLabel("Video Toolbox", self)
        self._layout.addWidget(title)

        subtitle = BodyLabel(
            "Download high-quality content from YouTube, TikTok, Pinterest, and 1000+ other platforms."
        )
        subtitle.setWordWrap(True)
        self._layout.addWidget(subtitle)
        self._layout.addSpacing(SECTION_SPACING)

    def _add_actions(self):
        """Primary action buttons."""
        row = QHBoxLayout()
        open_btn = PrimaryPushButton("Open Downloads Folder", self)
        open_btn.setIcon(FluentIcon.FOLDER)
        open_btn.clicked.connect(self._open_download_folder)
        row.addWidget(open_btn)
        row.addStretch(1)
        self._layout.addLayout(row)
        self._layout.addSpacing(SECTION_SPACING)

    def _add_feature_grid(self):
        """Grid of feature/tool cards."""
        self._layout.addWidget(SubtitleLabel("Included Tools & Features"))

        grid = QGridLayout()
        grid.setContentsMargins(0, 10, 0, 0)
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
        root = QHBoxLayout(card)
        root.setContentsMargins(CARD_PADDING, CARD_PADDING, CARD_PADDING, CARD_PADDING)
        root.setSpacing(12)

        icon_w = IconWidget(icon, card)
        icon_w.setFixedSize(FEATURE_ICON_SIZE, FEATURE_ICON_SIZE)

        text_col = QVBoxLayout()
        text_col.setSpacing(4)
        title_lbl = SubtitleLabel(title, card)
        desc_lbl = CaptionLabel(desc, card)

        text_col.addWidget(title_lbl)
        text_col.addWidget(desc_lbl)

        root.addWidget(icon_w, 0, Qt.AlignTop)
        root.addLayout(text_col, 1)
        return card

    def _add_instructions_card(self):
        """How-to-use card with steps and optional images."""
        card = CardWidget(self)
        layout = QVBoxLayout(card)
        layout.setSpacing(10)
        layout.addWidget(SubtitleLabel("How to use", card))

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