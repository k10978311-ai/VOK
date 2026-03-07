"""M3U8 / HLS Download interface — Coming Soon placeholder view."""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QHBoxLayout, QVBoxLayout
from qfluentwidgets import (
    BodyLabel,
    CardWidget,
    FluentIcon,
    LargeTitleLabel,
    StrongBodyLabel,
    TitleLabel,
)

from app.ui.components import CardHeader

from .base import BaseView


_PLANNED_FEATURES = [
    (FluentIcon.LINK,         "HLS / M3U8 Support",     "Download live and VOD streams from HLS (.m3u8) playlists natively."),
    (FluentIcon.VIDEO,        "Multi-Quality Selection", "Choose resolution (720p, 1080p, etc.) from master playlists automatically."),
    (FluentIcon.SYNC,         "Segment Merging",         "Fetch all segments and merge into a single MP4/MKV with FFmpeg."),
    (FluentIcon.SPEED_HIGH,   "Parallel Segment Download", "Download multiple segments concurrently for faster completion."),
    (FluentIcon.PLAY,         "Live Stream Capture",     "Record live HLS streams with optional time limits and auto-stop."),
    (FluentIcon.CERTIFICATE,   "Encrypted Streams",       "Support for AES-128 and common DRM patterns where allowed."),
]


class M3u8Interface(BaseView):
    """Coming-soon page for the M3U8 / HLS download feature."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("M3U8 Download")
        self._layout.setContentsMargins(24, 20, 24, 24)
        self._build_ui()

    def _build_ui(self) -> None:
        self._layout.addLayout(self._make_hero_row())
        self._layout.addSpacing(8)
        self._layout.addWidget(self._make_features_card())
        self._layout.addWidget(self._make_status_card())
        self._layout.addStretch(1)

    # ── Hero ──────────────────────────────────────────────────────────────

    def _make_hero_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(16)

        left = QVBoxLayout()
        left.setSpacing(6)

        title = LargeTitleLabel("M3U8 Download", self)
        left.addWidget(title)

        subtitle = BodyLabel(
            "Download HLS streams and M3U8 playlists directly — live TV, "
            "VOD, and adaptive streams in one place.",
            self,
        )
        subtitle.setWordWrap(True)
        left.addWidget(subtitle)

        row.addLayout(left, stretch=3)

        badge_card = CardWidget(self)
        badge_layout = QVBoxLayout(badge_card)
        badge_layout.setAlignment(Qt.AlignCenter)
        badge_layout.setContentsMargins(24, 20, 24, 20)

        coming_label = TitleLabel("Coming Soon", badge_card)
        coming_label.setAlignment(Qt.AlignCenter)
        badge_layout.addWidget(coming_label)

        desc = BodyLabel("Under active development", badge_card)
        desc.setAlignment(Qt.AlignCenter)
        badge_layout.addWidget(desc)

        row.addWidget(badge_card, stretch=1)
        return row

    # ── Planned features grid ─────────────────────────────────────────────

    def _make_features_card(self) -> CardWidget:
        card = CardWidget(self)
        layout = QVBoxLayout(card)
        layout.setSpacing(12)
        layout.addWidget(CardHeader(FluentIcon.DEVELOPER_TOOLS, "Planned Features", card))

        grid = QHBoxLayout()
        grid.setSpacing(12)

        left_col = QVBoxLayout()
        left_col.setSpacing(10)
        right_col = QVBoxLayout()
        right_col.setSpacing(10)

        for i, (icon, name, detail) in enumerate(_PLANNED_FEATURES):
            target = left_col if i % 2 == 0 else right_col
            target.addLayout(self._make_feature_row(card, icon, name, detail))

        left_col.addStretch(1)
        right_col.addStretch(1)
        grid.addLayout(left_col)
        grid.addLayout(right_col)
        layout.addLayout(grid)
        return card

    @staticmethod
    def _make_feature_row(parent, icon, name: str, detail: str) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(10)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)

        name_label = StrongBodyLabel(name, parent)
        detail_label = BodyLabel(detail, parent)
        detail_label.setWordWrap(True)

        text_col.addWidget(name_label)
        text_col.addWidget(detail_label)

        row.addLayout(text_col)
        return row

    # ── Status ────────────────────────────────────────────────────────────

    def _make_status_card(self) -> CardWidget:
        card = CardWidget(self)
        layout = QVBoxLayout(card)
        layout.setSpacing(8)
        layout.addWidget(CardHeader(FluentIcon.INFO, "Development Status", card))

        items = [
            "M3U8 parser and segment URL resolution — in progress",
            "FFmpeg concat/merge pipeline — planned",
            "Master playlist quality selection UI — planned",
            "Live stream recorder with progress — planned",
            "Encrypted segment handling (AES-128) — planned",
        ]
        for item in items:
            row = QHBoxLayout()
            dot = BodyLabel("•", card)
            dot.setFixedWidth(12)
            row.addWidget(dot)
            row.addWidget(BodyLabel(item, card))
            row.addStretch(1)
            layout.addLayout(row)

        layout.addSpacing(4)
        note = BodyLabel(
            "Stay tuned — follow VOK on GitHub for release updates.",
            card,
        )
        note.setWordWrap(True)
        layout.addWidget(note)
        return card
