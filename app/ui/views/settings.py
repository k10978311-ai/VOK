"""Settings view."""

from qfluentwidgets import BodyLabel, LargeTitleLabel

from .base import BaseView


class SettingsView(BaseView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        title = LargeTitleLabel(self)
        title.setText("Settings")
        self._layout.addWidget(title)
        body = BodyLabel(self)
        body.setText("Application settings.")
        self._layout.addWidget(body)
