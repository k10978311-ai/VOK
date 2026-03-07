"""Batch Enhance interface — CommandBar + video table + Enhance dialog."""

from __future__ import annotations

import math
import os
import subprocess
import sys
from pathlib import Path

from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QStackedWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    Action,
    BodyLabel,
    CaptionLabel,
    CommandBar,
    ComboBox,
    FluentIcon as FIF,
    PrimaryPushButton,
    PushButton,
    RoundMenu,
    SwitchButton,
    TableWidget,
    TitleLabel,
    ToolButton,
    setCustomStyleSheet,
)

from app.ui.utils import format_size

from .base import BaseView


_VIDEO_EXT = {".mp4", ".mkv", ".webm", ".avi", ".mov", ".m4v", ".wmv", ".flv"}
_PAGE_SIZE = 50

# Column indices
_COL_IDX      = 0
_COL_NAME     = 1
_COL_SIZE     = 2
_COL_STATUS   = 3
_COL_PROGRESS = 4

_COLS = ["#", "File Name", "Size", "Status", "Progress"]

_TABLE_QSS = "QTableView::item { padding-left: 8px; padding-right: 8px; }"


# ──────────────────────────────────────────────────────────────────────────────
# Enhance settings dialog
# ──────────────────────────────────────────────────────────────────────────────

class EnhanceDialog(QDialog):
    """Dialog for adjusting core enhancement options before starting."""

    def __init__(self, selected_count: int = 0, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Enhance Settings")
        self.setModal(True)
        self.setFixedWidth(420)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self._build(selected_count)

    def _build(self, selected_count: int) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)

        title = TitleLabel("Enhance Settings", self)
        root.addWidget(title)

        sub_text = (
            f"{selected_count} video(s) selected."
            if selected_count > 0
            else "No videos selected — will apply to all."
        )
        root.addWidget(BodyLabel(sub_text, self))

        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignRight)

        # Upscale factor
        self._scale_combo = ComboBox(self)
        self._scale_combo.addItems(["None", "2×", "4×"])
        form.addRow("Upscale:", self._scale_combo)

        # Denoise level
        self._denoise_combo = ComboBox(self)
        self._denoise_combo.addItems(["None", "Light", "Medium", "Strong"])
        form.addRow("Denoise:", self._denoise_combo)

        # Stabilize
        self._stabilize_switch = SwitchButton(self)
        self._stabilize_switch.setChecked(False)
        form.addRow("Stabilize:", self._stabilize_switch)

        # Codec
        self._codec_combo = ComboBox(self)
        self._codec_combo.addItems(["H.264 (libx264)", "H.265 (libx265)", "VP9", "AV1"])
        form.addRow("Output codec:", self._codec_combo)

        # Quality (CRF)
        self._quality_combo = ComboBox(self)
        self._quality_combo.addItems(["High (CRF 18)", "Medium (CRF 23)", "Low (CRF 28)"])
        self._quality_combo.setCurrentIndex(1)
        form.addRow("Quality:", self._quality_combo)

        root.addLayout(form)
        root.addSpacing(8)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        cancel_btn = PushButton("Cancel", self)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        start_btn = PrimaryPushButton("Start Enhance", self)
        start_btn.setIcon(FIF.PLAY)
        start_btn.clicked.connect(self.accept)
        btn_row.addWidget(start_btn)
        root.addLayout(btn_row)

    @property
    def settings(self) -> dict:
        """Return chosen settings as a dict (UI values, not wired to logic)."""
        return {
            "upscale":    self._scale_combo.currentText(),
            "denoise":    self._denoise_combo.currentText(),
            "stabilize":  self._stabilize_switch.isChecked(),
            "codec":      self._codec_combo.currentText(),
            "quality":    self._quality_combo.currentText(),
        }


# ──────────────────────────────────────────────────────────────────────────────
# Main view
# ──────────────────────────────────────────────────────────────────────────────

class BatchEnhanceInterface(BaseView):
    """Batch Enhance: CommandBar + paginated video table (50/page) + Enhance dialog."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Batch Enhance")
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

        self._videos: list[tuple[str, str, int]] = []  # (name, path, size)
        self._current_page = 0

        self._build_ui()

    def _build_ui(self) -> None:
        self._build_command_bar(self._layout)
        self._build_table(self._layout)
        self._build_footer(self._layout)

    # ── CommandBar ────────────────────────────────────────────────────────────

    def _build_command_bar(self, parent_layout: QVBoxLayout) -> None:
        self.cmd = CommandBar()
        self.cmd.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)

        self.act_add_folder  = Action(FIF.FOLDER_ADD, self.tr("Add Folder"))
        self.act_refresh     = Action(FIF.SYNC,       self.tr("Refresh"))
        self.act_enhance     = Action(FIF.PLAY,       self.tr("Enhance"))
        self.act_settings    = Action(FIF.SETTING,    self.tr("Settings"))
        self.act_select_all  = Action(FIF.CHECKBOX,   self.tr("Select All"))
        self.act_deselect    = Action(FIF.REMOVE,     self.tr("Deselect"))
        self.act_remove      = Action(FIF.DELETE,     self.tr("Remove"))
        self.act_clear       = Action(FIF.CLOSE,      self.tr("Clear All"))

        self.act_add_folder.triggered.connect(self._on_add_folder)
        self.act_refresh.triggered.connect(self._on_refresh)
        self.act_enhance.triggered.connect(self._on_enhance)
        self.act_settings.triggered.connect(self._on_enhance_settings)
        self.act_select_all.triggered.connect(self._on_select_all)
        self.act_deselect.triggered.connect(self._on_deselect_all)
        self.act_remove.triggered.connect(self._on_remove_selected)
        self.act_clear.triggered.connect(self._on_clear_all)

        for act in (self.act_add_folder, self.act_refresh):
            self.cmd.addAction(act)
        self.cmd.addSeparator()
        for act in (self.act_enhance, self.act_settings):
            self.cmd.addAction(act)
        self.cmd.addSeparator()
        for act in (self.act_select_all, self.act_deselect):
            self.cmd.addAction(act)
        self.cmd.addSeparator()
        for act in (self.act_remove, self.act_clear):
            self.cmd.addAction(act)

        parent_layout.addWidget(self.cmd)

    # ── Table ─────────────────────────────────────────────────────────────────

    def _build_table(self, parent_layout: QVBoxLayout) -> None:
        self._table_stack = QStackedWidget(self)

        # Empty state (index 0)
        empty = QWidget()
        empty_lay = QVBoxLayout(empty)
        empty_lay.setAlignment(Qt.AlignCenter)
        hint = BodyLabel(self.tr("No videos.  Click 'Add Folder' to load from a folder."), empty)
        hint.setAlignment(Qt.AlignCenter)
        empty_lay.addWidget(hint)
        self._table_stack.addWidget(empty)

        # Table (index 1)
        self.table = TableWidget()
        self.table.setColumnCount(len(_COLS))
        self.table.setHorizontalHeaderLabels([self.tr(c) for c in _COLS])

        hdr = self.table.horizontalHeader()
        if hdr:
            hdr.setSectionResizeMode(_COL_IDX,      QHeaderView.ResizeMode.Fixed)
            hdr.setSectionResizeMode(_COL_NAME,     QHeaderView.ResizeMode.Stretch)
            hdr.setSectionResizeMode(_COL_SIZE,     QHeaderView.ResizeMode.Fixed)
            hdr.setSectionResizeMode(_COL_STATUS,   QHeaderView.ResizeMode.Fixed)
            hdr.setSectionResizeMode(_COL_PROGRESS, QHeaderView.ResizeMode.Fixed)

        self.table.setColumnWidth(_COL_IDX,      40)
        self.table.setColumnWidth(_COL_SIZE,     100)
        self.table.setColumnWidth(_COL_STATUS,   95)
        self.table.setColumnWidth(_COL_PROGRESS, 100)

        v = self.table.verticalHeader()
        if v:
            v.setVisible(False)

        self.table.setEditTriggers(TableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(TableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(TableWidget.SelectionMode.ExtendedSelection)
        self.table.setBorderVisible(True)
        self.table.setBorderRadius(8)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._on_context_menu)

        setCustomStyleSheet(self.table, _TABLE_QSS, _TABLE_QSS)

        self._table_stack.addWidget(self.table)
        parent_layout.addWidget(self._table_stack, 1)

    # ── Footer ────────────────────────────────────────────────────────────────

    def _build_footer(self, parent_layout: QVBoxLayout) -> None:
        footer = QHBoxLayout()
        footer.setSpacing(12)
        footer.setContentsMargins(12, 4, 12, 8)

        self.status_label = BodyLabel(self.tr("0 video(s)"))
        footer.addWidget(self.status_label)

        hint = CaptionLabel(self.tr("Double-click to view details"))
        hint.setStyleSheet("color: gray;")
        footer.addWidget(hint)

        footer.addStretch()

        self.prev_btn = ToolButton(FIF.LEFT_ARROW)
        self.prev_btn.setEnabled(False)
        self.prev_btn.clicked.connect(self._on_page_prev)
        footer.addWidget(self.prev_btn)

        self.page_label = BodyLabel("1 / 1")
        footer.addWidget(self.page_label)

        self.next_btn = ToolButton(FIF.RIGHT_ARROW)
        self.next_btn.setEnabled(False)
        self.next_btn.clicked.connect(self._on_page_next)
        footer.addWidget(self.next_btn)

        parent_layout.addLayout(footer)

    # ── CommandBar handlers ───────────────────────────────────────────────────

    def _on_add_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select folder with videos")
        if not folder:
            return
        existing_paths = {p for _, p, _ in self._videos}
        new_items = [
            (p.name, str(p.resolve()), p.stat().st_size)
            for p in Path(folder).iterdir()
            if p.is_file() and p.suffix.lower() in _VIDEO_EXT
            and str(p.resolve()) not in existing_paths
        ]
        self._videos.extend(new_items)
        self._current_page = 0
        self._refresh_table()

    def _on_refresh(self) -> None:
        self._refresh_table()

    def _on_enhance(self) -> None:
        selected_rows = self.table.selectionModel().selectedRows()
        dlg = EnhanceDialog(selected_count=len(selected_rows), parent=self)
        dlg.exec_()

    def _on_enhance_settings(self) -> None:
        dlg = EnhanceDialog(selected_count=0, parent=self)
        dlg.exec_()

    def _on_select_all(self) -> None:
        self.table.selectAll()

    def _on_deselect_all(self) -> None:
        self.table.clearSelection()

    def _on_remove_selected(self) -> None:
        rows = sorted(
            {idx.row() for idx in self.table.selectionModel().selectedRows()},
            reverse=True,
        )
        page_start = self._current_page * _PAGE_SIZE
        for r in rows:
            global_idx = page_start + r
            if 0 <= global_idx < len(self._videos):
                self._videos.pop(global_idx)
        self._current_page = min(self._current_page, max(0, self._total_pages - 1))
        self._refresh_table()

    def _on_clear_all(self) -> None:
        self._videos.clear()
        self._current_page = 0
        self._refresh_table()

    # ── Table: context menu ───────────────────────────────────────────────────

    def _on_context_menu(self, pos: QPoint) -> None:
        row = self.table.indexAt(pos).row()
        if row < 0:
            return
        global_idx = self._current_page * _PAGE_SIZE + row
        if global_idx >= len(self._videos):
            return
        _, path, _ = self._videos[global_idx]

        menu = RoundMenu(title="", parent=self)
        menu.addAction(Action(FIF.PLAY,   "Enhance this file",  triggered=self._on_enhance))
        menu.addAction(Action(FIF.FOLDER, "Open folder",         triggered=lambda: self._open_folder(path)))
        menu.addSeparator()
        menu.addAction(Action(FIF.DELETE, "Remove from list",    triggered=lambda: self._remove_row(global_idx)))
        menu.exec_(self.table.viewport().mapToGlobal(pos))

    def _open_folder(self, path: str) -> None:
        if not path or not os.path.exists(path):
            return
        target = os.path.dirname(path) if os.path.isfile(path) else path
        try:
            if sys.platform == "win32":
                os.startfile(target)
            elif sys.platform == "darwin":
                subprocess.run(["open", target], check=False)
            else:
                subprocess.run(["xdg-open", target], check=False)
        except Exception:
            pass

    def _remove_row(self, global_idx: int) -> None:
        if 0 <= global_idx < len(self._videos):
            self._videos.pop(global_idx)
            self._current_page = min(self._current_page, max(0, self._total_pages - 1))
            self._refresh_table()

    # ── Pagination ────────────────────────────────────────────────────────────

    @property
    def _total_pages(self) -> int:
        return max(1, math.ceil(len(self._videos) / _PAGE_SIZE))

    def _on_page_prev(self) -> None:
        if self._current_page > 0:
            self._current_page -= 1
            self._refresh_table()

    def _on_page_next(self) -> None:
        if self._current_page < self._total_pages - 1:
            self._current_page += 1
            self._refresh_table()

    # ── Table refresh ─────────────────────────────────────────────────────────

    def _refresh_table(self) -> None:
        if not self._videos:
            self._table_stack.setCurrentIndex(0)
            self.status_label.setText(self.tr("0 video(s)"))
            self.page_label.setText("1 / 1")
            self.prev_btn.setEnabled(False)
            self.next_btn.setEnabled(False)
            return

        self._table_stack.setCurrentIndex(1)
        page_start = self._current_page * _PAGE_SIZE
        page_items = self._videos[page_start: page_start + _PAGE_SIZE]

        self.table.setUpdatesEnabled(False)
        self.table.setRowCount(len(page_items))
        for row, (name, _path, size) in enumerate(page_items):
            num_item = QTableWidgetItem(str(page_start + row + 1))
            num_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, _COL_IDX,      num_item)
            self.table.setItem(row, _COL_NAME,     QTableWidgetItem(name))
            self.table.setItem(row, _COL_SIZE,     QTableWidgetItem(format_size(size)))
            status_item = QTableWidgetItem(self.tr("Pending"))
            status_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, _COL_STATUS,   status_item)
            progress_item = QTableWidgetItem("—")
            progress_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, _COL_PROGRESS, progress_item)
        self.table.setUpdatesEnabled(True)

        total = len(self._videos)
        pages = self._total_pages
        self.status_label.setText(self.tr(f"{total} video(s)"))
        self.page_label.setText(f"{self._current_page + 1} / {pages}")
        self.prev_btn.setEnabled(self._current_page > 0)
        self.next_btn.setEnabled(self._current_page < pages - 1)
