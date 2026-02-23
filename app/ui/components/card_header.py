"""Reusable card header row: icon + subtitle label."""

from PyQt5.QtWidgets import QHBoxLayout, QWidget
from qfluentwidgets import IconWidget, SubtitleLabel


class CardHeader(QWidget):
    """Horizontal icon + subtitle label row used as a card section title.

    Usage::

        card_layout.addWidget(CardHeader(FluentIcon.DOWNLOAD, "My Section", card))
    """

    def __init__(self, icon, text: str, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 4)
        layout.setSpacing(8)

        ico = IconWidget(icon, self)
        ico.setFixedSize(16, 16)
        self._label = SubtitleLabel(text, self)

        layout.addWidget(ico)
        layout.addWidget(self._label)
        layout.addStretch(1)

    def setText(self, text: str) -> None:
        self._label.setText(text)

    def text(self) -> str:
        return self._label.text()
