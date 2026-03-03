"""Single feature card for the Dashboard feature grid: icon, title, description."""

from __future__ import annotations

from PyQt5.QtWidgets import QVBoxLayout
from qfluentwidgets import CaptionLabel, CardWidget, IconWidget, SubtitleLabel


ICON_SIZE = 32
CARD_PADDING = 18
CARD_SPACING = 8


class DashboardFeatureCard(CardWidget):
    """A compact card showing an icon, title, and short description."""

    def __init__(
        self,
        title: str,
        description: str,
        icon,
        parent=None,
    ):
        super().__init__(parent)
        self.setObjectName("DashboardFeatureCard")

        root = QVBoxLayout(self)
        root.setSpacing(CARD_SPACING)
        root.setContentsMargins(CARD_PADDING, CARD_PADDING, CARD_PADDING, CARD_PADDING)

        icon_w = IconWidget(icon, self)
        icon_w.setFixedSize(ICON_SIZE, ICON_SIZE)
        root.addWidget(icon_w)

        self._title_lbl = SubtitleLabel(title, self)
        root.addWidget(self._title_lbl)

        self._desc_lbl = CaptionLabel(description, self)
        self._desc_lbl.setWordWrap(True)
        root.addWidget(self._desc_lbl)

        root.addStretch(1)

    def set_texts(self, title: str, description: str) -> None:
        """Update title and description labels (used during retranslation)."""
        self._title_lbl.setText(title)
        self._desc_lbl.setText(description)
