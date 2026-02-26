from __future__ import annotations

from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QVBoxLayout,
)
from qfluentwidgets import (
    BodyLabel,
    CardWidget,
    ComboBox,
    FluentIcon,
    InfoBar,
    InfoBarPosition,
    LargeTitleLabel,
    PrimaryPushButton,
    PushButton,
)

from app.common.state import clear_log_entries, get_log_entries
from app.ui.components import CardHeader, StatusTable


class LogsDialog(QDialog):
    """Modal popup dialog that shows application log entries."""

    _LEVELS = ("All", "error", "warning", "download", "info")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Logs")
        self.setModal(True)
        self.setMinimumWidth(700)
        self.setMinimumHeight(520)
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowContextHelpButtonHint
        )
        self._active_filter: str = "All"
        self._setup_content()
        self._refresh_table()

    # ── Build ─────────────────────────────────────────────────────────────

    def _setup_content(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(12)

        # Title
        title = LargeTitleLabel("Logs", self)
        root.addWidget(title)

        sub = BodyLabel(
            "Application log entries. Use Clear or Export as needed.", self
        )
        root.addWidget(sub)
        root.addSpacing(4)

        # Log card
        card = CardWidget(self)
        card_layout = QVBoxLayout(card)
        # card_layout.setSpacing(10)
        # card_layout.addWidget(CardHeader(FluentIcon.DOCUMENT, "Log data", card))

        self._table = StatusTable(card)
        self._table.setMinimumHeight(320)
        card_layout.addWidget(self._table)

        # Button row
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

        filter_lbl = BodyLabel("Filter:", card)
        self._filter_combo = ComboBox(card)
        for level in self._LEVELS:
            self._filter_combo.addItem(level.capitalize())
        self._filter_combo.currentIndexChanged.connect(self._on_filter_changed)

        self._count_label = BodyLabel("", card)

        btn_row.addWidget(refresh_btn)
        btn_row.addWidget(clear_btn)
        btn_row.addWidget(export_btn)
        btn_row.addStretch(1)
        btn_row.addWidget(filter_lbl)
        btn_row.addWidget(self._filter_combo)
        btn_row.addSpacing(8)
        btn_row.addWidget(self._count_label)
        card_layout.addLayout(btn_row)

        root.addWidget(card)

    # ── Slots ─────────────────────────────────────────────────────────────

    def _on_filter_changed(self, index: int) -> None:
        self._active_filter = self._LEVELS[index]
        self._refresh_table()

    def _refresh_table(self) -> None:
        all_entries = get_log_entries() or []
        entries = (
            all_entries
            if self._active_filter == "All"
            else [
                e for e in all_entries
                if e.get("level", "info") == self._active_filter
            ]
        )
        self._table.setRowCount(0)
        if entries:
            for e in entries:
                self._table.append_row(
                    e.get("time", ""),
                    e.get("level", "info"),
                    e.get("message", ""),
                )
            count = len(entries)
            total = len(all_entries)
            suffix = "" if self._active_filter == "All" else f" of {total}"
            self._count_label.setText(
                f"{count}{suffix} entr{'y' if count == 1 else 'ies'}"
            )
        else:
            hint = (
                f"No '{self._active_filter}' entries."
                if self._active_filter != "All"
                else "No log entries yet."
            )
            self._table.set_empty_hint(hint)
            self._count_label.setText("")

    def _clear_logs(self) -> None:
        clear_log_entries()
        self._filter_combo.setCurrentIndex(0)
        self._refresh_table()

    def _export_logs(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export logs",
            str(Path.home() / "vok_logs.txt"),
            "Text files (*.txt);;All files (*)",
        )
        if not path:
            return
        entries = get_log_entries()
        with open(path, "w", encoding="utf-8") as fh:
            for e in entries:
                fh.write(
                    f"[{e.get('time', '')}] "
                    f"[{e.get('level', '').upper()}] "
                    f"{e.get('message', '')}\n"
                )
        InfoBar.success(
            title="Exported",
            content=f"Saved to {path}",
            position=InfoBarPosition.BOTTOM_RIGHT,
            duration=3000,
            parent=self,
        )

