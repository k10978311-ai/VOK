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

        title_lbl = SubtitleLabel(title, self)
        root.addWidget(title_lbl)

        desc_lbl = CaptionLabel(description, self)
        desc_lbl.setWordWrap(True)
        root.addWidget(desc_lbl)

        root.addStretch(1)
