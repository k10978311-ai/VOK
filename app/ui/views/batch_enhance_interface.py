"""Batch Enhance view — orchestrates CommandBar, table widget, and worker queue."""

from __future__ import annotations

import math
import os
import subprocess
import sys
from collections import deque
from pathlib import Path

from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QVBoxLayout,
)
from qfluentwidgets import (
    Action,
    BodyLabel,
    CaptionLabel,
    CommandBar,
    FluentIcon as FIF,
    LargeTitleLabel,
    RoundMenu,
    ToolButton,
)

from app.common.signal_bus import signal_bus
from app.common.concurrent.enhance_worker import EnhancePostProcessWorker
from app.config import load_settings
from app.common.utils import (

    PAGE_SIZE,
    ST_DONE,
    ST_ERROR,
    ST_PENDING,
    ST_QUEUED,
    ST_RUNNING,
    VIDEO_EXTENSIONS,
)
from app.ui.components.batch_enhance_table import BatchEnhanceTable
from app.ui.dialogs.enhance_setting_dialog import EnhanceSettingDialog
from app.common.enhance_helpers import (
    build_output_path,
    options_from_settings,
    probe_video_meta,
)

from .base import BaseView

COL_IDX      = 0
COL_NAME     = 1
COL_SIZE     = 2
COL_RES      = 3
COL_DURATION = 4
COL_ETA      = 5
COL_STATUS   = 6
COL_PROGRESS = 7


class BatchEnhanceInterface(BaseView):
    """Batch Enhance: add videos → configure settings → run enhancement queue."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Batch Enhance")
        self._layout.setContentsMargins(24, 20, 24, 0)
        self._layout.setSpacing(8)

        # Video list: (display_name, abs_path, size_bytes, resolution, duration_secs)
        self._videos: list[tuple[str, str, int, str, float]] = []
        self._current_page = 0
        self._sort_col: int | None = None
        self._sort_asc: bool = True

        # Enhancement state
        self._statuses: dict[str, tuple[str, str]] = {}   # path → (status, detail)
        self._workers: dict[str, EnhancePostProcessWorker] = {}
        self._queue: deque[str] = deque()

        self._build_ui()

    def _build_ui(self) -> None:
        self._build_header(self._layout)
        self._build_command_bar(self._layout)
        self._build_table(self._layout)
        self._build_footer(self._layout)

    # ── Page Header ───────────────────────────────────────────────────────────

    def _build_header(self, parent_layout: QVBoxLayout) -> None:
        title = LargeTitleLabel(self.tr("Batch Enhance"), self)
        parent_layout.addWidget(title)

        subtitle = BodyLabel(
            self.tr("Add videos, configure settings, and run enhancement in batch."),
            self,
        )
        subtitle.setStyleSheet("color: gray;")
        parent_layout.addWidget(subtitle)
        parent_layout.addSpacing(4)

    # ── CommandBar ────────────────────────────────────────────────────────────

    def _build_command_bar(self, parent_layout: QVBoxLayout) -> None:
        self.cmd = CommandBar()
        self.cmd.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)

        self.act_add_files  = Action(FIF.ADD,        self.tr("Add Files"))
        self.act_add_folder = Action(FIF.FOLDER_ADD, self.tr("Add Folder"))
        self.act_enhance    = Action(FIF.PLAY,       self.tr("Start Enhance"))
        self.act_stop       = Action(FIF.CANCEL,     self.tr("Stop All"))
        self.act_settings   = Action(FIF.SETTING,    self.tr("Settings"))
        self.act_select_all = Action(FIF.CHECKBOX,   self.tr("Select All"))
        self.act_deselect   = Action(FIF.REMOVE,     self.tr("Deselect All"))
        self.act_remove     = Action(FIF.DELETE,     self.tr("Remove"))
        self.act_clear      = Action(FIF.CLOSE,      self.tr("Clear All"))

        self.act_add_files.triggered.connect(self._on_add_files)
        self.act_add_folder.triggered.connect(self._on_add_folder)
        self.act_enhance.triggered.connect(self._on_enhance)
        self.act_stop.triggered.connect(self._on_stop_all)
        self.act_settings.triggered.connect(self._on_enhance_settings)
        self.act_select_all.triggered.connect(self._on_select_all)
        self.act_deselect.triggered.connect(self._on_deselect_all)
        self.act_remove.triggered.connect(self._on_remove_selected)
        self.act_clear.triggered.connect(self._on_clear_all)

        self.act_stop.setEnabled(False)

        for act in (self.act_add_files, self.act_add_folder):
            self.cmd.addAction(act)
        self.cmd.addSeparator()
        for act in (self.act_enhance, self.act_stop, self.act_settings):
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
        self._table_widget = BatchEnhanceTable(self)

        hdr = self._table_widget.table.horizontalHeader()
        if hdr:
            hdr.sectionClicked.connect(self._on_header_clicked)

        self._table_widget.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table_widget.table.customContextMenuRequested.connect(self._on_context_menu)
        self._table_widget.table.selectionModel().selectionChanged.connect(self._on_selection_changed)
        self._table_widget.filesDropped.connect(self._on_files_dropped)

        parent_layout.addWidget(self._table_widget, 1)

    # ── Footer ────────────────────────────────────────────────────────────────

    def _build_footer(self, parent_layout: QVBoxLayout) -> None:
        footer = QHBoxLayout()
        footer.setSpacing(12)
        footer.setContentsMargins(0, 4, 0, 12)

        self.status_label = BodyLabel(self.tr("0 video(s)"))
        footer.addWidget(self.status_label)

        self.selected_label = CaptionLabel("")
        self.selected_label.setStyleSheet("color: gray;")
        footer.addWidget(self.selected_label)

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

    def _on_files_dropped(self, paths: list[str]) -> None:
        existing = {p for _, p, *_ in self._videos}
        added = False
        for resolved in paths:
            if resolved not in existing:
                p = Path(resolved)
                res, dur = probe_video_meta(resolved)
                self._videos.append((p.name, resolved, p.stat().st_size, res, dur))
                existing.add(resolved)
                added = True
        if added:
            self._current_page = 0
            self._refresh_table()

    def _on_add_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self,
            self.tr("Select video files"),
            "",
            "Videos (*.mp4 *.mkv *.webm *.avi *.mov *.m4v *.wmv *.flv);;All files (*)",
        )
        if not files:
            return
        existing = {p for _, p, *_ in self._videos}
        for f in files:
            p = Path(f)
            resolved = str(p.resolve())
            if resolved not in existing and p.suffix.lower() in VIDEO_EXTENSIONS:
                res, dur = probe_video_meta(resolved)
                self._videos.append((p.name, resolved, p.stat().st_size, res, dur))
                existing.add(resolved)
        self._current_page = 0
        self._refresh_table()

    def _on_add_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, self.tr("Select folder with videos"))
        if not folder:
            return
        existing = {p for _, p, *_ in self._videos}
        new_items = []
        for p in Path(folder).iterdir():
            resolved = str(p.resolve())
            if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS and resolved not in existing:
                res, dur = probe_video_meta(resolved)
                new_items.append((p.name, resolved, p.stat().st_size, res, dur))
        self._videos.extend(new_items)
        self._current_page = 0
        self._refresh_table()

    def _on_enhance(self) -> None:
        if not self._videos:
            return
        selected_rows = {idx.row() for idx in self._table_widget.table.selectionModel().selectedRows()}
        page_start = self._current_page * PAGE_SIZE
        paths = (
            [self._videos[page_start + r][1] for r in selected_rows if page_start + r < len(self._videos)]
            if selected_rows
            else [v[1] for v in self._videos]
        )
        for path in paths:
            if self._statuses.get(path, (ST_PENDING, ""))[0] in (ST_QUEUED, ST_RUNNING, ST_DONE):
                continue
            self._statuses[path] = (ST_QUEUED, "Queued")
            if path not in self._queue:
                self._queue.append(path)
        self._refresh_table()
        self._pump_queue()

    def _on_stop_all(self) -> None:
        while self._queue:
            self._statuses[self._queue.popleft()] = (ST_ERROR, "Stopped")
        for worker in self._workers.values():
            worker.cancel()
        self._refresh_table()
        self._update_actions()

    def _on_enhance_settings(self) -> None:
        EnhanceSettingDialog(parent=self).exec_()

    def _on_select_all(self) -> None:
        self._table_widget.table.selectAll()

    def _on_deselect_all(self) -> None:
        self._table_widget.table.clearSelection()

    def _on_remove_selected(self) -> None:
        rows = sorted(
            {idx.row() for idx in self._table_widget.table.selectionModel().selectedRows()},
            reverse=True,
        )
        page_start = self._current_page * PAGE_SIZE
        for r in rows:
            global_idx = page_start + r
            if 0 <= global_idx < len(self._videos):
                path = self._videos[global_idx][1]
                self._cancel_worker(path)
                self._statuses.pop(path, None)
                self._videos.pop(global_idx)
        self._current_page = min(self._current_page, max(0, self._total_pages - 1))
        self._refresh_table()
        self._update_actions()

    def _on_clear_all(self) -> None:
        self._queue.clear()
        for path in list(self._workers):
            self._cancel_worker(path)
        self._workers.clear()
        self._statuses.clear()
        self._videos.clear()
        self._current_page = 0
        self._refresh_table()
        self._update_actions()

    # ── Enhancement pipeline ──────────────────────────────────────────────────

    def _pump_queue(self) -> None:
        max_concurrent = max(1, min(4, int(load_settings().get("concurrent_enhance", 2))))
        while len(self._workers) < max_concurrent and self._queue:
            path = self._queue.popleft()
            if not os.path.isfile(path) or path in self._workers:
                self._statuses[path] = (ST_ERROR, "File missing")
                continue
            worker = EnhancePostProcessWorker(
                path, build_output_path(path), options_from_settings(),
                job_id=path, parent=self,
            )
            worker.finished_signal.connect(
                lambda ok, msg, outp, sz, p=path: self._on_worker_finished(p, ok, msg, outp, sz)
            )
            worker.start()
            self._workers[path] = worker
            self._statuses[path] = (ST_RUNNING, "Processing…")
            signal_bus.enhance_started.emit(path, os.path.basename(path))
        self._refresh_table()
        self._update_actions()

    def _on_worker_finished(self, path: str, success: bool, message: str, output_path: str, size_bytes: int) -> None:
        self._workers.pop(path, None)
        self._statuses[path] = (
            (ST_DONE, "Done") if success else (ST_ERROR, (message or "Error")[:40])
        )
        signal_bus.enhance_finished.emit(
            path, success, os.path.basename(path), output_path or "", size_bytes
        )
        self._refresh_table()
        self._pump_queue()

    def _cancel_worker(self, path: str) -> None:
        worker = self._workers.pop(path, None)
        if worker:
            worker.cancel()
            worker.quit()

    def _update_actions(self) -> None:
        self.act_stop.setEnabled(bool(self._workers) or bool(self._queue))

    # ── Column sort ───────────────────────────────────────────────────────────

    def _on_header_clicked(self, col: int) -> None:
        if col not in (COL_NAME, COL_SIZE, COL_DURATION):
            return
        if self._sort_col == col:
            self._sort_asc = not self._sort_asc
        else:
            self._sort_col, self._sort_asc = col, True
        if col == COL_NAME:
            key = lambda v: v[0].lower()
        elif col == COL_SIZE:
            key = lambda v: v[2]
        else:
            key = lambda v: v[4]
        self._videos.sort(key=key, reverse=not self._sort_asc)
        self._current_page = 0
        self._refresh_table()

    # ── Selection feedback ────────────────────────────────────────────────────

    def _on_selection_changed(self) -> None:
        n = len(self._table_widget.table.selectionModel().selectedRows())
        self.selected_label.setText(self.tr(f"{n} selected") if n else "")

    # ── Context menu ──────────────────────────────────────────────────────────

    def _on_context_menu(self, pos: QPoint) -> None:
        row = self._table_widget.table.indexAt(pos).row()
        if row < 0:
            return
        global_idx = self._current_page * PAGE_SIZE + row
        if global_idx >= len(self._videos):
            return
        _, path, *_ = self._videos[global_idx]
        st = self._statuses.get(path, (ST_PENDING, ""))[0]

        menu = RoundMenu(title="", parent=self)
        if st != ST_DONE:
            menu.addAction(Action(FIF.PLAY, self.tr("Enhance this file"), triggered=lambda: self._enqueue_single(path)))
        if st == ST_ERROR:
            menu.addAction(Action(FIF.SYNC, self.tr("Retry"),             triggered=lambda: self._enqueue_single(path)))
        menu.addAction(Action(FIF.FOLDER, self.tr("Open folder"),         triggered=lambda: self._open_folder(path)))
        menu.addSeparator()
        menu.addAction(Action(FIF.DELETE, self.tr("Remove from list"),    triggered=lambda: self._remove_row(global_idx)))
        menu.exec_(self._table_widget.table.viewport().mapToGlobal(pos))

    def _enqueue_single(self, path: str) -> None:
        if self._statuses.get(path, (ST_PENDING, ""))[0] in (ST_QUEUED, ST_RUNNING):
            return
        self._statuses[path] = (ST_QUEUED, "Queued")
        if path not in self._queue:
            self._queue.append(path)
        self._refresh_table()
        self._pump_queue()

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
            path = self._videos[global_idx][1]
            self._cancel_worker(path)
            self._statuses.pop(path, None)
            self._videos.pop(global_idx)
            self._current_page = min(self._current_page, max(0, self._total_pages - 1))
            self._refresh_table()
            self._update_actions()

    # ── Pagination ────────────────────────────────────────────────────────────

    @property
    def _total_pages(self) -> int:
        return max(1, math.ceil(len(self._videos) / PAGE_SIZE))

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
            self._table_widget.show_empty()
            self.status_label.setText(self.tr("0 video(s)"))
            self.page_label.setText("1 / 1")
            self.prev_btn.setEnabled(False)
            self.next_btn.setEnabled(False)
            return

        page_start = self._current_page * PAGE_SIZE
        self._table_widget.populate(
            self._videos[page_start: page_start + PAGE_SIZE],
            page_start,
            self._statuses,
        )

        total   = len(self._videos)
        done    = sum(1 for st, _ in self._statuses.values() if st == ST_DONE)
        running = sum(1 for st, _ in self._statuses.values() if st == ST_RUNNING)
        parts   = [self.tr(f"{total} video(s)")]
        if done:
            parts.append(self.tr(f"{done} done"))
        if running:
            parts.append(self.tr(f"{running} running"))
        self.status_label.setText("  ·  ".join(parts))

        pages = self._total_pages
        self.page_label.setText(f"{self._current_page + 1} / {pages}")
        self.prev_btn.setEnabled(self._current_page > 0)
        self.next_btn.setEnabled(self._current_page < pages - 1)
