"""FeatureTile — vertical gallery-style clickable card used in banner components."""

from __future__ import annotations

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import (
    CaptionLabel,
    FluentIcon,
    IconWidget,
    SubtitleLabel,
)


class FeatureTile(QWidget):
    """Vertical gallery tile: large icon, title, description, link arrow."""

    clicked = pyqtSignal()

    _NORMAL_BG  = "transparent"
    _HOVER_BG   = "rgba(255,255,255,0.10)"
    _PRESSED_BG = "rgba(255,255,255,0.06)"

    def __init__(
        self,
        icon: FluentIcon,
        title: str,
        subtitle: str = "",
        parent=None,
    ):
        super().__init__(parent)
        self.setFixedSize(168, 148)
        self.setCursor(Qt.PointingHandCursor)
        self._build(icon, title, subtitle)
        self._set_bg(self._NORMAL_BG)

    # ── layout ────────────────────────────────────────────────────────────────

    def _build(self, icon: FluentIcon, title: str, subtitle: str):
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(6)

        # top row: main icon (left) + link arrow (right)
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(0)

        icon_w = IconWidget(icon, self)
        icon_w.setFixedSize(36, 36)
        top_row.addWidget(icon_w)

        top_row.addStretch(1)

        arrow_w = IconWidget(FluentIcon.LINK, self)
        arrow_w.setFixedSize(14, 14)
        top_row.addWidget(arrow_w, 0, Qt.AlignTop)

        root.addLayout(top_row)
        root.addSpacing(8)

        # title
        title_lbl = SubtitleLabel(title, self)
        title_lbl.setStyleSheet(
            "color: white; font-size: 13px; font-weight: 600;"
            " background: transparent; padding: 0;"
        )
        title_lbl.setWordWrap(True)
        root.addWidget(title_lbl)

        # description
        if subtitle:
            desc_lbl = CaptionLabel(subtitle, self)
            desc_lbl.setStyleSheet(
                "color: rgba(255,255,255,0.60); font-size: 11px;"
                " background: transparent; padding: 0;"
            )
            desc_lbl.setWordWrap(True)
            root.addWidget(desc_lbl)

        root.addStretch(1)

    # ── style helpers ─────────────────────────────────────────────────────────

    def _set_bg(self, color: str):
        self.setStyleSheet(
            f"FeatureTile {{ background: {color}; border-radius: 8px; }}"
        )

    # ── mouse events ──────────────────────────────────────────────────────────

    def enterEvent(self, event):
        self._set_bg(self._HOVER_BG)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._set_bg(self._NORMAL_BG)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._set_bg(self._PRESSED_BG)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._set_bg(self._HOVER_BG if self.underMouse() else self._NORMAL_BG)
            if self.rect().contains(event.pos()):
                self.clicked.emit()
        super().mouseReleaseEvent(event)
