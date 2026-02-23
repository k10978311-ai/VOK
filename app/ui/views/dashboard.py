"""Dashboard view: recent downloads card with quick actions."""

import os
from pathlib import Path

from PyQt5.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QTableWidgetItem,
    QVBoxLayout,
)
from qfluentwidgets import (
    BodyLabel,
    CardWidget,
    FluentIcon,
    LargeTitleLabel,
    PrimaryPushButton,
    PushButton,
)

from app.common.state import get_recent_downloads
from app.config import load_settings
from app.ui.components import CardHeader

from .base import BaseView


class DashboardView(BaseView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Dashboard")

        self._title = LargeTitleLabel(self)
        self._title.setText("Dashboard")
        self._layout.addWidget(self._title)

        self._subtitle = BodyLabel(self)
        self._subtitle.setText("Recent downloads and quick actions.")
        self._layout.addWidget(self._subtitle)
        self._layout.addSpacing(8)

        # ── Recent downloads card ─────────────────────────────────────────
        card = CardWidget(self)
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(10)
        card_layout.addWidget(CardHeader(FluentIcon.HISTORY, "Recent downloads", card))

        from qfluentwidgets import TableWidget
        self._table = TableWidget(card)
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(["File name", "Date", "Size", "Path"])
        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(3, QHeaderView.Stretch)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.setMinimumHeight(240)
        self._table.verticalHeader().setVisible(False)
        card_layout.addWidget(self._table)

        btn_row = QHBoxLayout()
        open_btn = PrimaryPushButton("Open folder", card)
        open_btn.setIcon(FluentIcon.FOLDER)
        open_btn.clicked.connect(self._open_download_folder)
        refresh_btn = PushButton("Refresh", card)
        refresh_btn.setIcon(FluentIcon.SYNC)
        refresh_btn.clicked.connect(self._refresh_table)
        btn_row.addWidget(open_btn)
        btn_row.addWidget(refresh_btn)
        btn_row.addStretch(1)
        self._count_label = BodyLabel("", card)
        btn_row.addWidget(self._count_label)
        card_layout.addLayout(btn_row)

        self._layout.addWidget(card)
        self._layout.addStretch(1)

        self._refresh_table()

    # ── Helpers ───────────────────────────────────────────────────────────

    def _refresh_table(self):
        rows = get_recent_downloads()
        self._table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            self._table.setItem(i, 0, QTableWidgetItem(row["name"]))
            self._table.setItem(i, 1, QTableWidgetItem(row["date"]))
            self._table.setItem(i, 2, QTableWidgetItem(row.get("size", "")))
            self._table.setItem(i, 3, QTableWidgetItem(row["path"]))
        if rows:
            self._count_label.setText(f"{len(rows)} file(s)")
        else:
            self._table.setRowCount(1)
            self._table.setItem(0, 0, QTableWidgetItem("No downloads yet"))
            for col in (1, 2, 3):
                self._table.setItem(0, col, QTableWidgetItem(""))
            self._count_label.setText("")

    def _open_download_folder(self):
        path = load_settings().get("download_path", "")
        target = Path(path) if path and Path(path).exists() else Path.home() / "Downloads"
        if target.exists():
            os.startfile(str(target))

    def showEvent(self, event):
        super().showEvent(event)
        self._refresh_table()
