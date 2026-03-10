"""Download Table card: header, Clear button, and qfluentwidgets TableWidget with Time/Host/Status/Message/Path/Size/Progress."""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QVBoxLayout,
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
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(
            ["Time", "Host", "Status", "Format", "Message", "Path", "Size", "Progress"]
        )
        hdr_view = self.table.horizontalHeader()
        hdr_view.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hdr_view.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hdr_view.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        hdr_view.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        hdr_view.setSectionResizeMode(4, QHeaderView.Stretch)
        hdr_view.setSectionResizeMode(5, QHeaderView.Stretch)
        hdr_view.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        hdr_view.setSectionResizeMode(7, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setMinimumHeight(320)
        self.table.verticalHeader().setDefaultSectionSize(36)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        layout.addWidget(self.table)
