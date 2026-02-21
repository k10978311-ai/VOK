"""Dashboard view."""

from qfluentwidgets import BodyLabel, LargeTitleLabel

from .base import BaseView


class DashboardView(BaseView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Dashboard")
        title = LargeTitleLabel(self)
        title.setText("Dashboard")
        self._layout.addWidget(title)
        body = BodyLabel(self)
        body.setText("Scail Media video downloader and content scraper.")
        self._layout.addWidget(body)
