"""Logs view."""

from qfluentwidgets import BodyLabel, LargeTitleLabel

from .base import BaseView


class LogsView(BaseView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Logs")
        title = LargeTitleLabel(self)
        title.setText("Logs")
        self._layout.addWidget(title)
        body = BodyLabel(self)
        body.setText("View application logs.")
        self._layout.addWidget(body)
