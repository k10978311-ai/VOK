"""Download Table card: header, Clear button, and jobs table with Time/Host/Status/Message/Path/Size/Progress."""

from PyQt5.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import CardWidget, FluentIcon, PushButton, TableWidget

from .card_header import CardHeader


class DownloadTableCard(CardWidget):
    """Card containing "Download Table" title, Clear button, and 7-column process table."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        hdr = QHBoxLayout()
        hdr.addWidget(CardHeader(FluentIcon.HISTORY, "Download Table", self))
        hdr.addStretch(1)
        self.clear_btn = PushButton("Clear", self)
        self.clear_btn.setIcon(FluentIcon.DELETE)
        hdr.addWidget(self.clear_btn)
        layout.addLayout(hdr)

        self.table = TableWidget(self)
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            ["Time", "Host", "Status", "Message", "Path", "Size", "Progress"]
        )
        hdr_view = self.table.horizontalHeader()
        hdr_view.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hdr_view.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hdr_view.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        hdr_view.setSectionResizeMode(3, QHeaderView.Stretch)
        hdr_view.setSectionResizeMode(4, QHeaderView.Stretch)
        hdr_view.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        hdr_view.setSectionResizeMode(6, QHeaderView.Fixed)
        self.table.setColumnWidth(6, 140)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setMinimumHeight(220)
        layout.addWidget(self.table)
