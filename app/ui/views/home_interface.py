"""Home interface: URL Download and Tasks tabs."""

from PyQt5.QtWidgets import QSizePolicy, QStackedWidget, QVBoxLayout, QWidget
from qfluentwidgets import SegmentedWidget

from .url_dowload_interface import UrlDownloadInterface
from .task_dowload_interface import TaskDownloadInterface


class HomeInterface(QWidget):
    """Tabbed download home: URL Download (enter URL) | Tasks (table)."""

    _TAB_URL = "url_download"
    _TAB_TASKS = "tasks"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("HomeInterface")

        self.pivot = SegmentedWidget(self)
        self.pivot.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)

        self.stackedWidget = QStackedWidget(self)

        self.url_interface = UrlDownloadInterface(self)
        self.task_interface = TaskDownloadInterface(self)

        self._add_tab(self.url_interface, self._TAB_URL, self.tr("URL Download"))
        self._add_tab(self.task_interface, self._TAB_TASKS, self.tr("Tasks"))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        layout.addWidget(self.pivot)
        layout.addWidget(self.stackedWidget)

        self.stackedWidget.currentChanged.connect(self._on_index_changed)
        self.stackedWidget.setCurrentWidget(self.url_interface)
        self.pivot.setCurrentItem(self._TAB_URL)

    # ── Tab helpers ───────────────────────────────────────────────────────

    def _add_tab(self, widget: QWidget, route_key: str, text: str):
        widget.setObjectName(route_key)
        self.stackedWidget.addWidget(widget)
        self.pivot.addItem(
            routeKey=route_key,
            text=text,
            onClick=lambda: self.stackedWidget.setCurrentWidget(widget),
        )

    def _on_index_changed(self, index: int):
        widget = self.stackedWidget.widget(index)
        if widget:
            self.pivot.setCurrentItem(widget.objectName())

    # ── Public navigation ─────────────────────────────────────────────────

    def switch_to_url(self):
        """Navigate to the URL Download tab."""
        self.stackedWidget.setCurrentWidget(self.url_interface)
        self.pivot.setCurrentItem(self._TAB_URL)

    def switch_to_tasks(self):
        """Navigate to the Tasks table tab."""
        self.stackedWidget.setCurrentWidget(self.task_interface)
        self.pivot.setCurrentItem(self._TAB_TASKS)
