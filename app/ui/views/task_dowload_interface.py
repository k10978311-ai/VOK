from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from PyQt5.QtCore import QAbstractTableModel, QModelIndex, Qt, pyqtSignal
from PyQt5.QtGui import QCloseEvent, QDragEnterEvent, QDropEvent, QKeyEvent
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    Action,
    BodyLabel,
    CommandBar,
    InfoBar,
    InfoBarPosition,
    PrimaryPushButton,
    ProgressBar,
    PushButton,
    RoundMenu,
    TableView,
)
from qfluentwidgets import FluentIcon as FIF

INFOBAR_MS_SUCCESS = 3000
INFOBAR_MS_ERROR   = 5000
INFOBAR_MS_WARNING = 4000
INFOBAR_MS_INFO    = 3000

VIDEO_EXTENSIONS = {
    "mp4", "mkv", "avi", "mov", "wmv", "flv", "webm", "m4v", "ts", "mpeg", "mpg",
}
AUDIO_EXTENSIONS = {
    "mp3", "aac", "wav", "flac", "ogg", "m4a", "opus", "wma",
}
SUPPORTED_EXTENSIONS = VIDEO_EXTENSIONS | AUDIO_EXTENSIONS

# Table column indices
COL_IDX      = 0
COL_TITLE    = 1
COL_HOST     = 2
COL_FORMAT   = 3
COL_STATUS   = 4
COL_SIZE     = 5
COL_PROGRESS = 6
COL_PATH     = 7

_COL_HEADERS = ["#", "Title", "Host", "Format", "Status", "Size", "Progress %", "Save Path"]

_STATUS_PENDING  = "Pending"
_STATUS_RUNNING  = "Downloading"
_STATUS_DONE     = "Done"
_STATUS_ERROR    = "Error"
_STATUS_CANCELED = "Canceled"


def _open_folder(path: str) -> None:
    try:
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception:
        pass


# ── Download task table model ──────────────────────────────────────────────────

class DownloadTaskModel(QAbstractTableModel):
    """Model holding a list of download task rows."""

    def __init__(self) -> None:
        super().__init__()
        # Each row: dict with keys matching COL_* indices
        self._rows: List[Dict[str, Any]] = []

    # ── QAbstractTableModel interface ────────────────────────────────────────

    def rowCount(self, parent: Optional[QModelIndex] = None) -> int:
        return len(self._rows)

    def columnCount(self, parent: Optional[QModelIndex] = None) -> int:
        return len(_COL_HEADERS)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:  # type: ignore
        if not index.isValid():
            return None
        row = self._rows[index.row()]
        col = index.column()

        if role == Qt.DisplayRole:  # type: ignore
            if col == COL_IDX:
                return str(index.row() + 1)
            if col == COL_TITLE:
                return row.get("title", "")
            if col == COL_HOST:
                return row.get("host", "")
            if col == COL_FORMAT:
                return row.get("format", "")
            if col == COL_STATUS:
                return row.get("status", _STATUS_PENDING)
            if col == COL_SIZE:
                return row.get("size", "—")
            if col == COL_PROGRESS:
                p = row.get("progress", 0)
                return f"{p}%" if isinstance(p, int) else "—"
            if col == COL_PATH:
                return row.get("path", "")

        if role == Qt.TextAlignmentRole:  # type: ignore
            if col in (COL_IDX, COL_STATUS, COL_SIZE, COL_PROGRESS):
                return Qt.AlignCenter  # type: ignore
        return None

    def headerData(self, section: int, orientation: Qt.Orientation,
                   role: int = Qt.DisplayRole) -> Any:  # type: ignore
        if role == Qt.DisplayRole:  # type: ignore
            if orientation == Qt.Horizontal:  # type: ignore
                return _COL_HEADERS[section] if section < len(_COL_HEADERS) else None
            if orientation == Qt.Vertical:  # type: ignore
                return str(section + 1)
        if role == Qt.TextAlignmentRole:  # type: ignore
            return Qt.AlignCenter  # type: ignore
        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        if not index.isValid():
            return Qt.NoItemFlags  # type: ignore
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable  # type: ignore

    # ── Mutations ────────────────────────────────────────────────────────────

    def add_task(self, title: str, host: str = "", fmt: str = "",
                 path: str = "") -> int:
        """Append a new pending task; returns its row index."""
        row_idx = len(self._rows)
        self.beginInsertRows(QModelIndex(), row_idx, row_idx)
        self._rows.append({
            "title":    title,
            "host":     host,
            "format":   fmt,
            "status":   _STATUS_PENDING,
            "size":     "—",
            "progress": 0,
            "path":     path,
        })
        self.endInsertRows()
        return row_idx

    def update_task(self, row_idx: int, **kwargs: Any) -> None:
        if 0 <= row_idx < len(self._rows):
            self._rows[row_idx].update(kwargs)
            self.dataChanged.emit(
                self.index(row_idx, 0),
                self.index(row_idx, len(_COL_HEADERS) - 1),
                [Qt.DisplayRole],  # type: ignore
            )

    def remove_selected(self, rows: List[int]) -> None:
        for row_idx in sorted(rows, reverse=True):
            if 0 <= row_idx < len(self._rows):
                self.beginRemoveRows(QModelIndex(), row_idx, row_idx)
                self._rows.pop(row_idx)
                self.endRemoveRows()

    def clear(self) -> None:
        self.beginResetModel()
        self._rows.clear()
        self.endResetModel()

    def get_task(self, row_idx: int) -> Optional[Dict[str, Any]]:
        if 0 <= row_idx < len(self._rows):
            return self._rows[row_idx]
        return None


# ── Main widget ────────────────────────────────────────────────────────────────

class TaskDownloadInterface(QWidget):
    """Download queue: command bar + task table + progress bar."""

    download_requested = pyqtSignal(list)   # list[dict] of queued tasks
    finished           = pyqtSignal(str, str)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setAttribute(Qt.WA_DeleteOnClose)  # type: ignore

        self._enhance_enabled: bool = False

        self._init_ui()

    # ── UI setup ───────────────────────────────────────────────────────────

    def _init_ui(self) -> None:
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(12)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self._setup_toolbar()
        self._setup_table()
        self._setup_footer()
        # Apply enhance enabled state (uses status_label from footer)
        self._set_enhance_enabled(False)

    # ── Toolbar ────────────────────────────────────────────────────────────

    def _setup_toolbar(self) -> None:
        top = QHBoxLayout()
        top.setSpacing(6)
        top.setContentsMargins(0, 8, 0, 0)  # padding top for command bar

        self.command_bar = CommandBar(self)
        self.command_bar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)  # type: ignore
        top.addWidget(self.command_bar, 1)

        # Optimize (字幕校正) — checkable; when checked, enhance settings are allowed
        self.optimize_button = Action(
            FIF.EDIT,
            self.tr("字幕校正"),
            triggered=self._on_subtitle_optimization_changed,
            checkable=True,
        )
        self.command_bar.addAction(self.optimize_button)

        # Enhance settings (enabled only when optimize is checked)
        self._enhance_settings_action = Action(
            FIF.SETTING,
            self.tr("Enhance Settings"),
            triggered=self._on_enhance_configure,
        )
        self.command_bar.addAction(self._enhance_settings_action)

        self.command_bar.addSeparator()

        # Clear all
        self.command_bar.addAction(
            Action(FIF.DELETE, self.tr("Clear"), triggered=self._on_clear)
        )

        # Start (PushButton) and Download (PrimaryPushButton)
        self.start_button = PushButton(self.tr("Start"), self, icon=FIF.PLAY)
        self.start_button.setFixedHeight(34)
        self.start_button.clicked.connect(self._on_download_clicked)
        top.addWidget(self.start_button)

        self.download_button = PrimaryPushButton(self.tr("Download"), self, icon=FIF.DOWNLOAD)
        self.download_button.setFixedHeight(34)
        self.download_button.clicked.connect(self._on_download_clicked)
        top.addWidget(self.download_button)

        self.main_layout.addLayout(top)

    # ── Table ──────────────────────────────────────────────────────────────

    def _setup_table(self) -> None:
        self.task_table = TableView(self)
        self.model = DownloadTaskModel()
        self.task_table.setModel(self.model)

        self.task_table.setBorderVisible(True)
        self.task_table.setBorderRadius(8)
        self.task_table.setWordWrap(False)
        self.task_table.setSelectionBehavior(QAbstractItemView.SelectRows)  # type: ignore
        self.task_table.setEditTriggers(QAbstractItemView.NoEditTriggers)   # type: ignore
        self.task_table.setAlternatingRowColors(True)

        hdr = self.task_table.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(COL_TITLE, QHeaderView.Stretch)
        hdr.setSectionResizeMode(COL_PATH,  QHeaderView.Stretch)
        hdr.setSectionResizeMode(COL_IDX,   QHeaderView.Fixed)
        self.task_table.setColumnWidth(COL_IDX, 40)

        v_hdr = self.task_table.verticalHeader()
        v_hdr.setVisible(False)
        v_hdr.setDefaultSectionSize(40)

        self.task_table.setContextMenuPolicy(Qt.CustomContextMenu)  # type: ignore
        self.task_table.customContextMenuRequested.connect(self._show_context_menu)

        self.main_layout.addWidget(self.task_table)

    # ── Footer ─────────────────────────────────────────────────────────────

    def _setup_footer(self) -> None:
        footer = QHBoxLayout()
        footer.setContentsMargins(0, 0, 0, 0)

        self.progress_bar = ProgressBar(self)

        self.status_label = BodyLabel(self.tr("Add files or URLs to start downloading"), self)
        self.status_label.setMinimumWidth(120)
        self.status_label.setAlignment(Qt.AlignCenter)  # type: ignore

        self.cancel_button = PushButton(self.tr("Cancel"), self, icon=FIF.CANCEL)
        self.cancel_button.hide()
        self.cancel_button.clicked.connect(self._on_cancel)

        footer.addWidget(self.progress_bar, 1)
        footer.addWidget(self.status_label)
        footer.addWidget(self.cancel_button)
        self.main_layout.addLayout(footer)

    # ── Toolbar actions ────────────────────────────────────────────────────

    def _on_subtitle_optimization_changed(self, checked: bool) -> None:
        """When 字幕校正 is checked, allow enhance settings; when unchecked, disable them."""
        self._set_enhance_enabled(checked)

    def _set_enhance_enabled(self, enabled: bool) -> None:
        """Enable or disable enhance settings action. If disabling, turn off enhance."""
        self._enhance_settings_action.setEnabled(enabled)
        if not enabled:
            self._enhance_enabled = False
        if hasattr(self, "status_label") and self.status_label:
            self.status_label.setText(
                self.tr("Enhance settings enabled (字幕校正 on)")
                if enabled else
                self.tr("Enhance settings disabled (字幕校正 off)")
            )

    def _on_add_url(self) -> None:
        from PyQt5.QtWidgets import QInputDialog
        url, ok = QInputDialog.getText(
            self, self.tr("Add URL"),
            self.tr("Enter video/audio URL:"),
        )
        if ok and url.strip():
            self._add_url_task(url.strip())

    def _add_url_task(self, url: str) -> None:
        from urllib.parse import urlparse
        try:
            host = urlparse(url).netloc.replace("www.", "")
        except Exception:
            host = ""
        title = url[:60] + ("…" if len(url) > 60 else "")
        self.model.add_task(title=title, host=host, fmt="", path="")
        self.status_label.setText(self.tr(f"Added: {host or url}"))

    def _on_enhance_configure(self) -> None:
        from app.ui.dialogs.enhance_setting_dialog import EnhanceSettingDialog
        dlg = EnhanceSettingDialog(self)
        dlg.exec_()

    def _on_clear(self) -> None:
        self.model.clear()
        self.status_label.setText(self.tr("Queue cleared"))

    # ── Download / Cancel ──────────────────────────────────────────────────

    def _on_download_clicked(self) -> None:
        if self.model.rowCount() == 0:
            InfoBar.warning(
                self.tr("Warning"), self.tr("Add at least one file or URL first."),
                duration=INFOBAR_MS_WARNING, parent=self,
            )
            return
        tasks = [self.model.get_task(i) for i in range(self.model.rowCount())]
        tasks_clean = [t for t in tasks if t is not None]
        self._enhance_enabled = self.optimize_button.isChecked()
        self.start_button.setEnabled(False)
        self.download_button.setEnabled(False)
        self.cancel_button.show()
        self.progress_bar.setValue(0)
        self.status_label.setText(self.tr("Starting download…"))
        InfoBar.info(
            self.tr("Download started"),
            self.tr(f"Queued {len(tasks_clean)} task(s){' with Enhance' if self._enhance_enabled else ''}."),
            duration=INFOBAR_MS_INFO, parent=self,
        )
        self.download_requested.emit(tasks_clean)

    def _on_cancel(self) -> None:
        self.start_button.setEnabled(True)
        self.download_button.setEnabled(True)
        self.cancel_button.hide()
        self.progress_bar.setValue(0)
        self.status_label.setText(self.tr("Cancelled"))
        InfoBar.warning(
            self.tr("Cancelled"), self.tr("Download cancelled."),
            duration=INFOBAR_MS_WARNING, parent=self,
        )

    # ── Public progress API ────────────────────────────────────────────────

    def set_progress(self, value: int, status: str = "") -> None:
        self.progress_bar.setValue(value)
        if status:
            self.status_label.setText(status)

    def update_task_progress(self, row_idx: int, progress: int,
                             status: str = "", size: str = "") -> None:
        kwargs: Dict = {"progress": progress}
        if status:
            kwargs["status"] = status
        if size:
            kwargs["size"] = size
        self.model.update_task(row_idx, **kwargs)

    def on_finished(self, video_path: str = "", output_path: str = "") -> None:
        self.start_button.setEnabled(True)
        self.download_button.setEnabled(True)
        self.cancel_button.hide()
        self.progress_bar.setValue(100)
        self.status_label.setText(self.tr("Done"))
        if video_path or output_path:
            self.finished.emit(video_path, output_path)
        InfoBar.success(
            self.tr("Done"), self.tr("All downloads complete."),
            duration=INFOBAR_MS_SUCCESS,
            position=InfoBarPosition.BOTTOM,
            parent=self.parent() or self,
        )

    def on_error(self, error: str) -> None:
        self.start_button.setEnabled(True)
        self.download_button.setEnabled(True)
        self.cancel_button.hide()
        self.progress_bar.error()
        InfoBar.error(
            self.tr("Error"), self.tr(error),
            duration=INFOBAR_MS_ERROR, parent=self,
        )

    # ── Public task API ────────────────────────────────────────────────────

    def set_task(self, task: dict) -> None:
        title = task.get("title") or os.path.basename(task.get("file_path", "Unknown"))
        host  = task.get("host", "")
        fmt   = task.get("format", "")
        path  = task.get("file_path") or task.get("path", "")
        self.model.add_task(title=title, host=host, fmt=fmt, path=path)

    def add_url(self, url: str) -> None:
        self._add_url_task(url)

    # ── Drag & drop ────────────────────────────────────────────────────────

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        event.accept() if event.mimeData().hasUrls() else event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        added = 0
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if not os.path.isfile(path):
                continue
            ext = os.path.splitext(path)[1][1:].lower()
            if ext in SUPPORTED_EXTENSIONS:
                title = os.path.basename(path)
                self.model.add_task(title=title, host="Local", fmt=ext, path=path)
                added += 1
            else:
                InfoBar.warning(
                    self.tr(f"Skipped: .{ext}"),
                    self.tr("Unsupported format — drop video/audio files only."),
                    duration=INFOBAR_MS_WARNING, parent=self,
                )
        if added:
            self.status_label.setText(self.tr(f"Added {added} file(s) via drag & drop"))
        event.accept()

    # ── Context menu ───────────────────────────────────────────────────────

    def _show_context_menu(self, pos) -> None:
        rows = self._selected_rows()
        if not rows:
            return
        menu = RoundMenu(parent=self)
        menu.addAction(Action(FIF.DOWNLOAD, self.tr("Download Selected"),
                              triggered=lambda: self._download_selected_rows(rows)))
        menu.addSeparator()
        menu.addAction(Action(FIF.REMOVE, self.tr("Remove"),
                              triggered=lambda: self.model.remove_selected(rows)))
        menu.exec(self.task_table.viewport().mapToGlobal(pos))

    def _download_selected_rows(self, rows: List[int]) -> None:
        tasks = [t for i in rows if (t := self.model.get_task(i)) is not None]
        if tasks:
            self.download_requested.emit(tasks)

    # ── Helpers ────────────────────────────────────────────────────────────

    def _selected_rows(self) -> List[int]:
        return sorted({idx.row() for idx in self.task_table.selectedIndexes()})

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key_Delete:  # type: ignore
            rows = self._selected_rows()
            if rows:
                self.model.remove_selected(rows)
            event.accept()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event: QCloseEvent) -> None:
        super().closeEvent(event)
