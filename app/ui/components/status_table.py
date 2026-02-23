"""Reusable status table: Time / Status / Message columns with color-coded rows."""

from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QAbstractItemView, QHeaderView, QTableWidgetItem
from qfluentwidgets import TableWidget

_STATUS_COLORS: dict[str, str] = {
    "error": "#E81123",
    "warning": "#CA5010",
    "download": "#0078D4",
}


class StatusTable(TableWidget):
    """Pre-configured three-column table: Time | Status | Message.

    Rows are automatically color-coded by status level.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(3)
        self.setHorizontalHeaderLabels(["Time", "Status", "Message"])
        hdr = self.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.Stretch)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setAlternatingRowColors(True)
        self.setMinimumHeight(220)
        self.verticalHeader().setVisible(False)

    def append_row(self, time_str: str, status: str, message: str) -> None:
        """Append a new row and scroll to bottom."""
        row = self.rowCount()
        self.insertRow(row)
        color = _STATUS_COLORS.get(status)
        for col, text in enumerate([time_str, status, message]):
            item = QTableWidgetItem(text)
            if color:
                item.setForeground(QColor(color))
            self.setItem(row, col, item)
        self.scrollToBottom()

    def set_empty_hint(self, hint: str = "No entries yet.") -> None:
        """Show a single empty-state row."""
        self.setRowCount(1)
        self.setItem(0, 0, QTableWidgetItem(""))
        self.setItem(0, 1, QTableWidgetItem(""))
        self.setItem(0, 2, QTableWidgetItem(hint))
