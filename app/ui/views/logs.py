"""Logs view: application log entries with Clear and Export actions."""

from pathlib import Path

from PyQt5.QtWidgets import QFileDialog, QHBoxLayout, QVBoxLayout
from qfluentwidgets import (
    BodyLabel,
    CardWidget,
    FluentIcon,
    InfoBar,
    InfoBarPosition,
    LargeTitleLabel,
    PrimaryPushButton,
    PushButton,
)

from app.common.state import clear_log_entries, get_log_entries
from app.ui.components import CardHeader, StatusTable

from .base import BaseView


class LogsView(BaseView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Logs")

        title = LargeTitleLabel(self)
        title.setText("Logs")
        self._layout.addWidget(title)

        subtitle = BodyLabel(self)
        subtitle.setText("Application log entries. Use Clear or Export as needed.")
        self._layout.addWidget(subtitle)
        self._layout.addSpacing(4)

        # ── Log card ──────────────────────────────────────────────────────
        card = CardWidget(self)
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(10)
        card_layout.addWidget(CardHeader(FluentIcon.DOCUMENT, "Log data", card))

        self._table = StatusTable(card)
        self._table.setMinimumHeight(280)
        card_layout.addWidget(self._table)

        btn_row = QHBoxLayout()
        refresh_btn = PushButton("Refresh", card)
        refresh_btn.setIcon(FluentIcon.SYNC)
        refresh_btn.clicked.connect(self._refresh_table)

        clear_btn = PushButton("Clear", card)
        clear_btn.setIcon(FluentIcon.DELETE)
        clear_btn.clicked.connect(self._clear_logs)

        export_btn = PrimaryPushButton("Export…", card)
        export_btn.setIcon(FluentIcon.SAVE)
        export_btn.clicked.connect(self._export_logs)

        btn_row.addWidget(refresh_btn)
        btn_row.addWidget(clear_btn)
        btn_row.addWidget(export_btn)
        btn_row.addStretch(1)
        self._count_label = BodyLabel("", card)
        btn_row.addWidget(self._count_label)
        card_layout.addLayout(btn_row)

        self._layout.addWidget(card)
        self._layout.addStretch(1)

        self._refresh_table()

    # ── Helpers ───────────────────────────────────────────────────────────

    def _refresh_table(self):
        entries = get_log_entries()
        self._table.setRowCount(0)
        if entries:
            for e in entries:
                self._table.append_row(
                    e.get("time", ""),
                    e.get("level", "info"),
                    e.get("message", ""),
                )
            self._count_label.setText(f"{len(entries)} entr{'y' if len(entries) == 1 else 'ies'}")
        else:
            self._table.set_empty_hint("No log entries yet.")
            self._count_label.setText("")

    def _clear_logs(self):
        clear_log_entries()
        self._refresh_table()

    def _export_logs(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export logs",
            str(Path.home() / "vok_logs.txt"),
            "Text files (*.txt);;All files (*)",
        )
        if not path:
            return
        entries = get_log_entries()
        try:
            with open(path, "w", encoding="utf-8") as f:
                for e in entries:
                    f.write(f"{e.get('time', '')}\t{e.get('level', '')}\t{e.get('message', '')}\n")
            InfoBar.success(
                title="Exported",
                content=f"Log saved to {Path(path).name}",
                isClosable=True,
                duration=3000,
                position=InfoBarPosition.TOP_RIGHT,
                parent=self,
            )
        except OSError as exc:
            InfoBar.error(
                title="Export failed",
                content=str(exc),
                isClosable=True,
                duration=4000,
                position=InfoBarPosition.TOP_RIGHT,
                parent=self,
            )

    def showEvent(self, event):
        super().showEvent(event)
        self._refresh_table()
