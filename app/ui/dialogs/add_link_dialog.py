"""Add Link dialog: single-URL input with clipboard pre-fill."""
from __future__ import annotations

from PyQt5.QtWidgets import QApplication

from qfluentwidgets import BodyLabel, LineEdit, MessageBoxBase


class AddLinkDialog(MessageBoxBase):
    """Single-URL input with Analyze & Add action."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.viewLayout.addWidget(BodyLabel(self.tr("Add Video URL"), self))

        self._input = LineEdit(self)
        self._input.setPlaceholderText(self.tr("https://youtube.com/watch?v=…"))
        self._input.setFixedHeight(40)
        self._input.setMinimumWidth(460)
        self._input.setClearButtonEnabled(True)

        clip = QApplication.clipboard().text().strip()
        if clip.startswith(("http://", "https://")):
            self._input.setText(clip)

        self.viewLayout.addWidget(self._input)
        self.viewLayout.setSpacing(10)
        self.yesButton.setText(self.tr("Analyze & Add"))
        self.cancelButton.setText(self.tr("Cancel"))

    def get_url(self) -> str:
        return self._input.text().strip()
