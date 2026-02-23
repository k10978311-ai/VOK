"""Dashboard view: welcome and how-to for video download users."""

import os
import platform
import subprocess
import webbrowser
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout
from qfluentwidgets import (
    BodyLabel,
    CardWidget,
    FluentIcon,
    LargeTitleLabel,
    PrimaryPushButton,
    PushButton,
    SubtitleLabel,
    ToolTipFilter,
    ToolTipPosition,
)

from app.common.paths import INSTRUCTIONS_DIR
from app.config import load_settings

from .base import BaseView

# Replace with your tutorial video URL (YouTube, etc.)
TUTORIAL_VIDEO_URL = "https://www.youtube.com/watch?v=mRD23Wdtr1M"


class DashboardView(BaseView):
    """Home view for users who download videos (YouTube, TikTok, etc.)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Dashboard")

        self._title = LargeTitleLabel(self)
        self._title.setText("Dashboard")
        self._layout.addWidget(self._title)

        self._subtitle = BodyLabel(self)
        self._subtitle.setText(
            "Download videos from YouTube, TikTok, Pinterest and 1000+ sites. "
            "Use the Download tab to paste a URL and choose quality."
        )
        self._subtitle.setWordWrap(True)
        self._layout.addWidget(self._subtitle)
        self._layout.addSpacing(16)

        btn_row = QHBoxLayout()
        open_btn = PrimaryPushButton("Open download folder", self)
        open_btn.setIcon(FluentIcon.FOLDER)
        open_btn.clicked.connect(self._open_download_folder)
        btn_row.addWidget(open_btn)
        btn_row.addStretch(1)
        self._layout.addLayout(btn_row)
        self._layout.addSpacing(24)

        # ── How to use (instructions with optional images and video) ─────────
        card = CardWidget(self)
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(12)
        card_layout.addWidget(SubtitleLabel("How to use", card))

        steps = [
            "1. Go to the Download tab and paste a video URL (e.g. from YouTube, TikTok, Pinterest).",
            "2. Choose quality (Best, 720p, Photo/Image, etc.) and the folder where to save.",
            "3. Click Download. Progress appears in the table and in the Logs tab.",
        ]
        for text in steps:
            lbl = BodyLabel(text, card)
            lbl.setWordWrap(True)
            card_layout.addWidget(lbl)

        # Optional instruction images: add step1.png, step2.png, … in resources/instructions/
        self._add_instruction_images(card_layout, card)

        # Watch tutorial video button
        video_row = QHBoxLayout()
        video_btn = PushButton("Watch tutorial video", card)
        video_btn.setToolTip("Watch the tutorial video to learn how to use the app")
        video_btn.setToolTipDuration(1000)
        video_btn.setIcon(FluentIcon.VIDEO)
        video_btn.clicked.connect(self._open_tutorial_video)
        video_btn.installEventFilter(ToolTipFilter(video_btn, showDelay=300, position=ToolTipPosition.TOP))
        video_row.addWidget(video_btn)
        video_row.addStretch(1)
        card_layout.addLayout(video_row)

        self._layout.addWidget(card)
        self._layout.addStretch(1)
        



    def _add_instruction_images(self, layout: QVBoxLayout, parent):
        """Add instruction images from resources/instructions/ if present (step1.png, step2.png, …)."""
        if not INSTRUCTIONS_DIR.exists():
            return
        for i in range(1, 10):
            for ext in (".png", ".jpg", ".jpeg"):
                path = INSTRUCTIONS_DIR / f"step{i}{ext}"
                if path.exists():
                    pix = QPixmap(str(path))
                    if not pix.isNull():
                        label = QLabel(parent)
                        label.setPixmap(pix.scaledToWidth(560, Qt.SmoothTransformation))
                        label.setAlignment(Qt.AlignCenter)
                        layout.addWidget(label)
                    break

    def _open_tutorial_video(self):
        try:
            webbrowser.open(TUTORIAL_VIDEO_URL)
        except Exception:
            pass

    def _open_download_folder(self):
        path = load_settings().get("download_path", "")
        target = Path(path) if path and Path(path).exists() else Path.home() / "Downloads"
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
