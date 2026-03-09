from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QCloseEvent, QDragEnterEvent, QDropEvent, QKeyEvent
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QApplication,
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

from app.ui.components.download_task_model import (
    DownloadTaskModel,
    COL_IDX, COL_TITLE, COL_HOST, COL_FORMAT, COL_STATUS, COL_SIZE, COL_PROGRESS, COL_PATH,
    _STATUS_PENDING, _STATUS_RUNNING, _STATUS_DONE, _STATUS_ERROR, _STATUS_CANCELED,
)
from app.ui.dialogs import ClipboardSettingsDialog, ClearOldTasksDialog

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
        self._clipboard_last_text: str = ""
        self._clipboard_interval: int = 500  # ms
        self._clipboard_timer = QTimer(self)
        self._clipboard_timer.setInterval(self._clipboard_interval)
        self._clipboard_timer.timeout.connect(self._poll_clipboard)
        # Seed last text so the current clipboard isn't auto-added on enable
        self._clipboard_last_text = QApplication.clipboard().text()

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

        # Clipboard Observer — checkable; monitors clipboard for URLs
        self._clipboard_observer_action = Action(
            FIF.PASTE,
            self.tr("Clipboard Observer"),
            triggered=self._on_clipboard_observer_toggled,
            checkable=True,
        )
        self._clipboard_observer_action.setToolTip(
            self.tr("Enable or Disable Clipboard Observer")
        )
        self.command_bar.addAction(self._clipboard_observer_action)

        # Clipboard Observer Settings gear — enabled only when observer is active
        self._clipboard_settings_action = Action(
            FIF.SETTING,
            self.tr("Clipboard Observer Settings"),
            triggered=self._on_clipboard_observer_settings,
        )
        self._clipboard_settings_action.setToolTip(
            self.tr("Configure Clipboard Observer (interval, filters)")
        )
        self._clipboard_settings_action.setEnabled(False)
        self.command_bar.addAction(self._clipboard_settings_action)

        self.command_bar.addSeparator()

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

        self.command_bar.addSeparator()

        # Save Folder — pick output folder
        self._save_folder_action = Action(
            FIF.FOLDER,
            self.tr("Save Folder"),
            triggered=self._on_save_folder_clicked,
        )
        self._save_folder_action.setToolTip(self.tr("Set download output folder"))
        self.command_bar.addAction(self._save_folder_action)

        # Download Settings — configure format, concurrency, cookies, etc.
        self._download_settings_action = Action(
            FIF.SETTING,
            self.tr("Download Settings"),
            triggered=self._on_download_settings,
        )
        self._download_settings_action.setToolTip(self.tr("Configure download options"))
        self.command_bar.addAction(self._download_settings_action)

        # Start Download button
        self.start_button = PrimaryPushButton(self.tr("Start Download"), self, icon=FIF.DOWNLOAD)
        self.start_button.setFixedHeight(34)
        self.start_button.clicked.connect(self._on_download_clicked)
        top.addWidget(self.start_button)

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

    # ── Clipboard observer ─────────────────────────────────────────────────

    def _on_clipboard_observer_toggled(self, checked: bool) -> None:
        """Start or stop monitoring the clipboard for URLs."""
        if checked:
            # Seed with current clipboard so we don't immediately add it
            self._clipboard_last_text = QApplication.clipboard().text()
            self._clipboard_timer.setInterval(self._clipboard_interval)
            self._clipboard_timer.start()
            self._clipboard_settings_action.setEnabled(True)
            self.status_label.setText(self.tr("Clipboard Observer: ON"))
        else:
            self._clipboard_timer.stop()
            self._clipboard_settings_action.setEnabled(False)
            self.status_label.setText(self.tr("Clipboard Observer: OFF"))

    def _on_clipboard_observer_settings(self) -> None:
        dlg = ClipboardSettingsDialog(
            interval=self._clipboard_interval,
            url_filter=getattr(self, "_clipboard_url_filter", ""),
            parent=self,
        )
        if dlg.exec_():
            self._clipboard_interval = dlg.get_interval()
            self._clipboard_url_filter: str = dlg.get_filter()
            self._clipboard_timer.setInterval(self._clipboard_interval)
            InfoBar.success(
                self.tr("Settings saved"),
                self.tr("Interval: {}  |  Filter: {}").format(
                    f"{self._clipboard_interval} ms",
                    self._clipboard_url_filter or self.tr("all URLs"),
                ),
                duration=INFOBAR_MS_SUCCESS,
                parent=self,
            )

    def _poll_clipboard(self) -> None:
        """Called on each timer tick; adds any new URL found in the clipboard."""
        text = QApplication.clipboard().text().strip()
        if not text or text == self._clipboard_last_text:
            return
        self._clipboard_last_text = text
        if not text.startswith(("http://", "https://")):
            return
        # Apply optional domain filter
        url_filter: str = getattr(self, "_clipboard_url_filter", "")
        if url_filter:
            allowed = [d.strip().lower() for d in url_filter.split(",") if d.strip()]
            if not any(d in text.lower() for d in allowed):
                return
        self._add_url_task(text)
        InfoBar.info(
            self.tr("URL detected"),
            self.tr("Added from clipboard: {}").format(
                text[:60] + ("\u2026" if len(text) > 60 else "")
            ),
            duration=INFOBAR_MS_INFO,
            parent=self,
        )

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

    def _add_url_task(self, url: str) -> None:
        from urllib.parse import urlparse
        try:
            host = urlparse(url).netloc.replace("www.", "")
        except Exception:
            host = ""
        title = url[:60] + ("…" if len(url) > 60 else "")
        self.model.add_task(title=title, host=host, fmt="", path="", url=url)
        self.status_label.setText(self.tr(f"Added: {host or url}"))

    def _on_enhance_configure(self) -> None:
        from app.ui.dialogs.enhance_setting_dialog import EnhanceSettingDialog
        dlg = EnhanceSettingDialog(self)
        dlg.exec_()

    def _on_clear(self) -> None:
        self.model.clear()
        self.status_label.setText(self.tr("Queue cleared"))

    # ── Save Folder / Download Settings ───────────────────────────────────

    def _on_save_folder_clicked(self) -> None:
        from PyQt5.QtWidgets import QFileDialog
        from app.config.store import load_settings, save_settings
        settings = load_settings()
        current = settings.get("download_path", "")
        folder = QFileDialog.getExistingDirectory(
            self, self.tr("Select Save Folder"), current or ""
        )
        if folder:
            settings["download_path"] = folder
            save_settings(settings)
            self.status_label.setText(self.tr("Save folder: {}").format(folder))
            InfoBar.success(
                self.tr("Folder saved"),
                self.tr("Downloads will be saved to: {}").format(folder),
                duration=INFOBAR_MS_SUCCESS,
                parent=self,
            )

    def _on_download_settings(self) -> None:
        from app.ui.dialogs.download_settings_dialog import DownloadSettingsDialog
        DownloadSettingsDialog(self).exec_()

    # ── Download / Cancel ──────────────────────────────────────────────────

    def _on_download_clicked(self) -> None:
        if self.model.rowCount() == 0:
            InfoBar.warning(
                self.tr("Warning"), self.tr("Add at least one file or URL first."),
                duration=INFOBAR_MS_WARNING, parent=self,
            )
            return

        # If there are finished/failed rows, prompt to clear them first
        _FINISHED = {_STATUS_DONE, _STATUS_ERROR, _STATUS_CANCELED}
        done_rows = [
            i for i in range(self.model.rowCount())
            if (t := self.model.get_task(i)) and t.get("status") in _FINISHED
        ]
        if done_rows:
            dlg = ClearOldTasksDialog(len(done_rows), self)
            if dlg.exec_():  # "Clear & Start"
                self.model.remove_selected(done_rows)
            # "Start Anyway" or X → continue without clearing

        # Only dispatch pending tasks to the engine
        tasks_to_run = [
            t for i in range(self.model.rowCount())
            if (t := self.model.get_task(i)) is not None
            and t.get("status") == _STATUS_PENDING
        ]
        if not tasks_to_run:
            InfoBar.warning(
                self.tr("Nothing to download"),
                self.tr("No pending tasks. Add new URLs or clear completed ones first."),
                duration=INFOBAR_MS_WARNING, parent=self,
            )
            return

        self._enhance_enabled = self.optimize_button.isChecked()
        self.start_button.setEnabled(False)
        self.cancel_button.show()
        self.progress_bar.setValue(0)
        self.status_label.setText(self.tr("Starting download…"))
        InfoBar.info(
            self.tr("Download started"),
            self.tr("Queued {} task(s){}.")
            .format(
                len(tasks_to_run),
                self.tr(" with Enhance") if self._enhance_enabled else "",
            ),
            duration=INFOBAR_MS_INFO, parent=self,
        )
        self.download_requested.emit(tasks_to_run)

    def _on_cancel(self) -> None:
        self.start_button.setEnabled(True)
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
        url   = task.get("url") or path
        self.model.add_task(title=title, host=host, fmt=fmt, path=path, url=url)

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
