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
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtCore import QUrl
from qfluentwidgets import (
    Action,
    BodyLabel,
    CommandBar,
    InfoBar,
    InfoBarPosition,
    LineEdit,
    MessageBoxBase,
    PrimaryPushButton,
    ProgressBar,
    PushButton,
    RoundMenu,
    TableView,
)
from qfluentwidgets import FluentIcon as FIF

from app.common.concurrent import MetaFetchWorker
from app.config.store import load_settings
from app.core.download import check_unsupported_url, detect_platform, normalize_url
from app.ui.components.download_task_model import (
    DownloadTaskModel,
    COL_IDX, COL_TITLE, COL_HOST, COL_STATUS, COL_SIZE, COL_PROGRESS,
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
    cancel_requested   = pyqtSignal()        # user pressed Cancel
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
        # Track running MetaFetchWorker instances so they can be cancelled on close
        self._info_workers: list = []

        self._init_ui()

    # ── UI setup ───────────────────────────────────────────────────────────

    def _init_ui(self) -> None:
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(12)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self._setup_toolbar()
        self._setup_table()
        self._setup_footer()
        # Disable enhance action without overwriting the default status label
        self._enhance_settings_action.setEnabled(False)

    # ── Toolbar ────────────────────────────────────────────────────────────

    def _setup_toolbar(self) -> None:
        top = QHBoxLayout()
        top.setSpacing(6)
        top.setContentsMargins(0, 8, 0, 0)  # padding top for command bar

        self.command_bar = CommandBar(self)
        self.command_bar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)  # type: ignore
        top.addWidget(self.command_bar, 1)

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
        self.command_bar.addSeparator()
        
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

        # Add Link — type/paste a URL, fetch video info then add to queue
        self._add_link_action = Action(
            FIF.ADD,
            self.tr("Add Link"),
            triggered=self._on_add_link,
        )
        self._add_link_action.setToolTip(self.tr("Add a video URL and analyze its info (Ctrl+V)"))
        self.command_bar.addAction(self._add_link_action)

        # Clear all
        self.command_bar.addAction(
            Action(FIF.DELETE, self.tr("Clear"), triggered=self._on_clear)
        )

        

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
        hdr.setSectionResizeMode(COL_IDX,   QHeaderView.Fixed)
        hdr.setSectionResizeMode(COL_HOST,  QHeaderView.Fixed)
        self.task_table.setColumnWidth(COL_IDX,  40)
        self.task_table.setColumnWidth(COL_HOST, 80)

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
        self._analyze_and_add_url(url)

    def _on_enhance_configure(self) -> None:
        from app.ui.dialogs.enhance_setting_dialog import EnhanceSettingDialog
        dlg = EnhanceSettingDialog(self)
        dlg.exec_()

    def _on_clear(self) -> None:
        self.model.clear()
        self.status_label.setText(self.tr("Queue cleared"))

    def _on_add_link(self) -> None:
        dlg = _AddLinkDialog(self)
        if dlg.exec_():
            url = dlg.get_url()
            if url:
                self._analyze_and_add_url(url)

    def _analyze_and_add_url(self, url: str) -> None:
        """Validate, normalize, add row immediately, then fetch video info in background."""
        url = url.strip()
        if not url.startswith(("http://", "https://")):
            InfoBar.warning(
                self.tr("Invalid URL"),
                self.tr("Only http/https URLs are supported."),
                duration=INFOBAR_MS_WARNING, parent=self,
            )
            return
        errmsg = check_unsupported_url(url)
        if errmsg:
            InfoBar.warning(
                self.tr("Unsupported URL"), self.tr(errmsg),
                duration=INFOBAR_MS_WARNING, parent=self,
            )
            return
        canonical, note = normalize_url(url)
        if note:
            InfoBar.info(
                self.tr("URL rewritten"), self.tr(note),
                duration=INFOBAR_MS_INFO, parent=self,
            )
        # Duplicate check (after normalisation so variants map to the same URL)
        existing = self.model.find_url(canonical)
        if existing != -1:
            self.task_table.selectRow(existing)
            InfoBar.warning(
                self.tr("Duplicate URL"),
                self.tr("This URL is already in the queue (row {}).").format(existing + 1),
                duration=INFOBAR_MS_WARNING, parent=self,
            )
            return
        platform = detect_platform(canonical)
        host = platform if platform != "Unknown" else ""
        if not host:
            from urllib.parse import urlparse
            try:
                host = urlparse(canonical).netloc.replace("www.", "")
            except Exception:
                host = ""
        # Add row immediately with URL as placeholder title
        title_placeholder = canonical[:60] + ("…" if len(canonical) > 60 else "")
        row_idx = self.model.add_task(
            title=title_placeholder, host=host, fmt="", path="", url=canonical
        )
        self.status_label.setText(self.tr(f"Analyzing: {host or canonical}…"))
        # Spawn background worker to fetch real title + uploader
        cookies = load_settings().get("cookies_file", "")
        worker = MetaFetchWorker(url=canonical, cookies_file=cookies, parent=self)

        def _on_data(info: dict, r=row_idx) -> None:
            title = info.get("title") or info.get("fulltitle") or ""
            uploader = (
                info.get("uploader") or info.get("channel")
                or info.get("artist") or ""
            )
            if title:
                self.model.update_task(r, title=title)
            task = self.model.get_task(r)
            if uploader and task and not task.get("host"):
                self.model.update_task(r, host=uploader)

        def _on_finished(success: bool, msg: str, r=row_idx, w=worker) -> None:
            task = self.model.get_task(r)
            short = (task or {}).get("title", canonical)[:50]
            self.status_label.setText(
                self.tr(f"Ready: {short}") if success
                else self.tr(f"Added (unverified): {short}")
            )
            if w in self._info_workers:
                self._info_workers.remove(w)

        worker.data_ready.connect(_on_data)
        worker.finished_signal.connect(_on_finished)
        self._info_workers.append(worker)
        worker.start()

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
        # Update own UI immediately; parent handles manager cancellation
        self.start_button.setEnabled(True)
        self.cancel_button.hide()
        self.progress_bar.setValue(0)
        self.status_label.setText(self.tr("Cancelled"))
        InfoBar.warning(
            self.tr("Cancelled"), self.tr("Download cancelled."),
            duration=INFOBAR_MS_WARNING, parent=self,
        )
        self.cancel_requested.emit()

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
        global_pos = self.task_table.viewport().mapToGlobal(pos)

        if not rows:
            self._show_table_menu(global_pos)
            return

        tasks = [self.model.get_task(i) for i in rows]
        tasks = [t for t in tasks if t is not None]

        has_pending   = any(t.get("status") == _STATUS_PENDING  for t in tasks)
        has_retryable = any(t.get("status") in (_STATUS_ERROR, _STATUS_CANCELED) for t in tasks)
        first_url     = next((t.get("url", "") for t in tasks if t.get("url")), "")
        first_path    = next((t.get("path", "") for t in tasks if t.get("path")), "")

        menu = RoundMenu(parent=self)

        menu.addAction(Action(
            FIF.ADD, self.tr("Add Link"),
            triggered=self._on_add_link,
        ))
        menu.addSeparator()

        if has_pending:
            menu.addAction(Action(
                FIF.DOWNLOAD, self.tr("Download Selected"),
                triggered=lambda: self._download_selected_rows(rows),
            ))

        if has_retryable:
            menu.addAction(Action(
                FIF.SYNC, self.tr("Retry"),
                triggered=lambda: self._retry_rows(rows),
            ))

        if has_pending or has_retryable:
            menu.addSeparator()

        if first_url:
            menu.addAction(Action(
                FIF.COPY, self.tr("Copy URL"),
                triggered=lambda: QApplication.clipboard().setText(first_url),
            ))
            if first_url.startswith(("http://", "https://")):
                menu.addAction(Action(
                    FIF.LINK, self.tr("Open in Browser"),
                    triggered=lambda u=first_url: QDesktopServices.openUrl(QUrl(u)),
                ))

        if first_path:
            folder = os.path.dirname(first_path) if os.path.isfile(first_path) else first_path
            if os.path.isdir(folder):
                menu.addAction(Action(
                    FIF.FOLDER, self.tr("Open Folder"),
                    triggered=lambda _, f=folder: QDesktopServices.openUrl(
                        QUrl.fromLocalFile(f)
                    ),
                ))

        menu.addSeparator()
        menu.addAction(Action(
            FIF.CHECKBOX, self.tr("Select All"),
            triggered=self.task_table.selectAll,
        ))
        menu.addSeparator()
        menu.addAction(Action(
            FIF.REMOVE, self.tr("Remove Selected"),
            triggered=lambda: self.model.remove_selected(rows),
        ))

        menu.exec(global_pos)

    def _show_table_menu(self, global_pos) -> None:
        """Context menu shown when right-clicking on empty table area (no row selected)."""
        has_rows    = self.model.rowCount() > 0
        has_pending = any(
            (self.model.get_task(i) or {}).get("status") == _STATUS_PENDING
            for i in range(self.model.rowCount())
        )
        has_retryable = any(
            (self.model.get_task(i) or {}).get("status") in (_STATUS_ERROR, _STATUS_CANCELED)
            for i in range(self.model.rowCount())
        )
        clipboard_url = QApplication.clipboard().text().strip()
        clipboard_is_url = clipboard_url.startswith(("http://", "https://"))

        menu = RoundMenu(parent=self)

        menu.addAction(Action(
            FIF.ADD, self.tr("Add Link"),
            triggered=self._on_add_link,
        ))
        if clipboard_is_url:
            menu.addAction(Action(
                FIF.PASTE, self.tr("Paste from Clipboard"),
                triggered=lambda: self._analyze_and_add_url(clipboard_url),
            ))
        menu.addSeparator()

        if has_pending:
            menu.addAction(Action(
                FIF.DOWNLOAD, self.tr("Download All Pending"),
                triggered=self._on_download_clicked,
            ))

        if has_retryable:
            all_retryable = [
                i for i in range(self.model.rowCount())
                if (self.model.get_task(i) or {}).get("status") in (_STATUS_ERROR, _STATUS_CANCELED)
            ]
            menu.addAction(Action(
                FIF.SYNC, self.tr("Retry All Failed"),
                triggered=lambda rows=all_retryable: self.model.retry_rows(rows),
            ))

        if has_pending or has_retryable:
            menu.addSeparator()

        if has_rows:
            menu.addAction(Action(
                FIF.CHECKBOX, self.tr("Select All"),
                triggered=self.task_table.selectAll,
            ))
            menu.addSeparator()
            menu.addAction(Action(
                FIF.DELETE, self.tr("Clear All"),
                triggered=self._on_clear,
            ))

        if not menu.actions():
            return

        menu.exec(global_pos)

    def _download_selected_rows(self, rows: List[int]) -> None:
        tasks = [t for i in rows if (t := self.model.get_task(i)) is not None]
        if tasks:
            self.download_requested.emit(tasks)

    def _retry_rows(self, rows: List[int]) -> None:
        self.model.retry_rows(rows)

    # ── Helpers ────────────────────────────────────────────────────────────

    def _selected_rows(self) -> List[int]:
        return sorted({idx.row() for idx in self.task_table.selectedIndexes()})

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key_Delete:  # type: ignore
            rows = self._selected_rows()
            if rows:
                self.model.remove_selected(rows)
            event.accept()
        elif event.key() == Qt.Key_V and event.modifiers() & Qt.ControlModifier:  # type: ignore
            text = QApplication.clipboard().text().strip()
            if text:
                self._analyze_and_add_url(text)
            event.accept()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event: QCloseEvent) -> None:
        for w in list(self._info_workers):
            if w.isRunning():
                w.quit()
                w.wait(500)
        self._info_workers.clear()
        super().closeEvent(event)


# ── Add Link dialog ────────────────────────────────────────────────────────────

class _AddLinkDialog(MessageBoxBase):
    """Single-URL input dialog with auto-filled clipboard and Analyze & Add action."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.viewLayout.addWidget(BodyLabel(self.tr("Add Video URL"), self))

        self._input = LineEdit(self)
        self._input.setPlaceholderText(self.tr("https://youtube.com/watch?v=…"))
        self._input.setFixedHeight(40)
        self._input.setMinimumWidth(460)
        self._input.setClearButtonEnabled(True)

        # Pre-fill with clipboard if it looks like a URL
        clip = QApplication.clipboard().text().strip()
        if clip.startswith(("http://", "https://")):
            self._input.setText(clip)

        self.viewLayout.addWidget(self._input)
        self.viewLayout.setSpacing(10)
        self.yesButton.setText(self.tr("Analyze & Add"))
        self.cancelButton.setText(self.tr("Cancel"))

    def get_url(self) -> str:
        return self._input.text().strip()
