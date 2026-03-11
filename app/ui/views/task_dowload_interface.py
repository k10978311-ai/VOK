from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from PyQt5.QtCore import Qt, QTimer, QUrl, pyqtSignal
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
from qfluentwidgets import (
    Action,
    CommandBar,
    BodyLabel,
    PrimaryPushButton,
    ProgressBar,
    PushButton,
    RoundMenu,
    TableView,
)
from qfluentwidgets import FluentIcon as FIF
from qfluentwidgets import InfoBarPosition

from app.common.concurrent import MetaFetchWorker, HostIconFetchWorker
from app.config.store import load_settings, save_settings
from app.core.download import check_unsupported_url, normalize_url
from app.core.clipboard_service import get_video_urls_to_add
from app.core.task_queue import (
    SUPPORTED_EXTENSIONS,
    is_issue_task,
    is_invalid_url_task,
    prepare_url_task_row,
    metadata_updates_from_info,
    extract_filesize_from_info,
    resolve_task_path,
    resolve_task_title,
    dir_for_path,
)
from app.ui.components.download_task_model import (
    DownloadTaskModel,
    COL_IDX, COL_TITLE, COL_HOST, COL_STATUS, COL_SIZE, COL_PROGRESS,
    _STATUS_PENDING, _STATUS_RUNNING, _STATUS_DONE, _STATUS_ERROR, _STATUS_CANCELED,
)
from app.ui.dialogs import (
    AddLinkDialog,
    ClipboardSettingsDialog,
    ClearOldTasksDialog,
    DownloadSettingsDialog,
)
from app.ui.utils import format_size

INFOBAR_MS_SUCCESS = 3000
INFOBAR_MS_ERROR   = 5000
INFOBAR_MS_WARNING = 4000
INFOBAR_MS_INFO    = 3000


# ── Main widget ────────────────────────────────────────────────────────────────

class TaskDownloadInterface(QWidget):
    """Download queue: command bar + task table + progress bar."""

    download_requested = pyqtSignal(list)   # list[dict] of queued tasks
    cancel_requested   = pyqtSignal()        # user pressed Cancel
    finished           = pyqtSignal(str, str)
    message_requested  = pyqtSignal(str, str, str, int, object)  # level, title, message, duration, position

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
        self._icon_workers: list = []

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
            self.message_requested.emit(
                "success",
                self.tr("Settings saved"),
                self.tr("Interval: {}  |  Filter: {}").format(
                    f"{self._clipboard_interval} ms",
                    self._clipboard_url_filter or self.tr("all URLs"),
                ),
                INFOBAR_MS_SUCCESS,
                None,
            )

    def _poll_clipboard(self) -> None:
        """Called on each timer tick; adds new video URLs from clipboard (no playlist/profile, no duplicates)."""
        text = QApplication.clipboard().text().strip()
        if not text or text == self._clipboard_last_text:
            return
        self._clipboard_last_text = text
        existing = self._get_existing_task_urls()
        url_filter: str = getattr(self, "_clipboard_url_filter", "")
        to_add = get_video_urls_to_add(text, existing, domain_filter=url_filter)
        if not to_add:
            return
        added = 0
        for url in to_add:
            self._analyze_and_add_url(url)
            added += 1
        self.message_requested.emit(
            "info",
            self.tr("URL(s) from clipboard"),
            self.tr("Added {} link(s) to the queue.").format(added),
            INFOBAR_MS_INFO,
            None,
        )

    def _get_existing_task_urls(self) -> set[str]:
        """Return set of all task URLs in the model (for duplicate check)."""
        out = set()
        for i in range(self.model.rowCount()):
            task = self.model.get_task(i)
            if task:
                u = task.get("url") or ""
                if u:
                    out.add(u)
        return out

    def _remove_issue_tasks(self, include_failed_metadata: bool = True) -> int:
        """Remove issue rows (invalid URLs; optionally failed metadata). Returns count removed."""
        to_remove = []
        for i in range(self.model.rowCount()):
            t = self.model.get_task(i)
            if is_invalid_url_task(t):
                to_remove.append(i)
            elif include_failed_metadata and is_issue_task(t):
                to_remove.append(i)
        if to_remove:
            self.model.remove_selected(to_remove)
        return len(to_remove)

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

    def _paste_clipboard_urls(self, text: str) -> None:
        """Parse clipboard text into video-only URLs (no playlist/profile), skip duplicates, add to queue."""
        existing = self._get_existing_task_urls()
        url_filter: str = getattr(self, "_clipboard_url_filter", "")
        to_add = get_video_urls_to_add(text, existing, domain_filter=url_filter)
        if not to_add:
            self.message_requested.emit(
                "warning",
                self.tr("Paste from clipboard"),
                self.tr(
                    "No new video links to add. Only single-video URLs are allowed; "
                    "playlists and profiles are skipped. Duplicates are ignored."
                ),
                INFOBAR_MS_WARNING,
                None,
            )
            return
        for url in to_add:
            self._analyze_and_add_url(url)
        if len(to_add) == 1:
            self.message_requested.emit(
                "info",
                self.tr("Link added"),
                self.tr("Added 1 link to the queue."),
                INFOBAR_MS_INFO,
                None,
            )
        else:
            self.message_requested.emit(
                "info",
                self.tr("Links added"),
                self.tr("Added {} links to the queue.").format(len(to_add)),
                INFOBAR_MS_INFO,
                None,
            )

    def _on_enhance_configure(self) -> None:
        from app.ui.dialogs.enhance_setting_dialog import EnhanceSettingDialog
        dlg = EnhanceSettingDialog(self)
        dlg.exec_()

    def _on_clear(self) -> None:
        self.model.clear()
        self.status_label.setText(self.tr("Queue cleared"))

    def _refresh_host_icon_for_url(self, url: str) -> None:
        """Refresh the host column for the row with this URL (after icon cache updated)."""
        row = self.model.find_url(url)
        if row >= 0:
            idx = self.model.index(row, COL_HOST)
            self.model.dataChanged.emit(idx, idx, [Qt.DecorationRole])

    def _emit_message(self, level: str, title: str, message: str, duration: int = INFOBAR_MS_INFO, position=None) -> None:
        """Emit message_requested with level, title, message, duration, position."""
        self.message_requested.emit(level, title, message, duration, position)

    def _on_add_link(self) -> None:
        dlg = AddLinkDialog(self)
        if dlg.exec_():
            url = dlg.get_url()
            if url:
                self._analyze_and_add_url(url)

    def _analyze_and_add_url(self, url: str) -> None:
        """Validate URL, normalize, add row, then fetch metadata and icon in background."""
        url = url.strip()
        if not url.startswith(("http://", "https://")):
            self._emit_message(
                "warning", self.tr("Invalid URL"),
                self.tr("Only http/https URLs are supported."), INFOBAR_MS_WARNING,
            )
            return
        errmsg = check_unsupported_url(url)
        if errmsg:
            self._emit_message("warning", self.tr("Unsupported URL"), self.tr(errmsg), INFOBAR_MS_WARNING)
            return
        canonical, note = normalize_url(url)
        if note:
            self._emit_message("info", self.tr("URL rewritten"), self.tr(note), INFOBAR_MS_INFO)
        existing = self.model.find_url(canonical)
        if existing != -1:
            self.task_table.selectRow(existing)
            self._emit_message(
                "warning", self.tr("Duplicate URL"),
                self.tr("This URL is already in the queue (row {}).").format(existing + 1),
                INFOBAR_MS_WARNING,
            )
            return
        row_data = prepare_url_task_row(canonical, path="")
        row_idx = self.model.add_task(
            title=row_data["title"],
            host=row_data["host"],
            fmt=row_data["format"],
            path=row_data["path"],
            url=row_data["url"],
        )
        self.status_label.setText(self.tr(f"Analyzing: {row_data['host'] or canonical}…"))
        cookies = load_settings().get("cookies_file", "")
        worker = MetaFetchWorker(url=canonical, cookies_file=cookies, parent=self)

        def _on_data(info: dict, r=row_idx) -> None:
            updates = metadata_updates_from_info(info)
            if updates.get("title"):
                self.model.update_task(r, title=updates["title"])
            task = self.model.get_task(r)
            if updates.get("uploader") and task and not task.get("host"):
                self.model.update_task(r, host=updates["uploader"])
            fs = extract_filesize_from_info(info)
            if fs is not None and fs > 0:
                self.model.update_task(r, size=format_size(fs))

        def _on_finished(success: bool, msg: str, r=row_idx, w=worker) -> None:
            if not success:
                row_to_remove = self.model.find_url(canonical)
                if row_to_remove >= 0:
                    self.model.remove_selected([row_to_remove])
                if w in self._info_workers:
                    self._info_workers.remove(w)
                return
            task = self.model.get_task(r)
            short = (task or {}).get("title", canonical)[:50]
            self.status_label.setText(self.tr(f"Ready: {short}"))
            if w in self._info_workers:
                self._info_workers.remove(w)

        worker.data_ready.connect(_on_data)
        worker.finished_signal.connect(_on_finished)
        self._info_workers.append(worker)
        worker.start()

        icon_worker = HostIconFetchWorker(canonical, parent=self)
        icon_worker.icon_fetched.connect(self._refresh_host_icon_for_url)
        def _icon_done():
            if icon_worker in self._icon_workers:
                self._icon_workers.remove(icon_worker)
        icon_worker.finished.connect(_icon_done)
        self._icon_workers.append(icon_worker)
        icon_worker.start()

    # ── Save Folder / Download Settings ───────────────────────────────────

    def _on_save_folder_clicked(self) -> None:
        from PyQt5.QtWidgets import QFileDialog
        settings = load_settings()
        current = settings.get("download_path", "")
        folder = QFileDialog.getExistingDirectory(
            self, self.tr("Select Save Folder"), current or ""
        )
        if folder:
            settings["download_path"] = folder
            save_settings(settings)
            self.status_label.setText(self.tr("Save folder: {}").format(folder))
            self._emit_message(
                "success", self.tr("Folder saved"),
                self.tr("Downloads will be saved to: {}").format(folder),
                INFOBAR_MS_SUCCESS,
            )

    def _on_download_settings(self) -> None:
        from app.ui.dialogs.download_settings_dialog import DownloadSettingsDialog
        DownloadSettingsDialog(self).exec_()

    # ── Download / Cancel ──────────────────────────────────────────────────

    def _on_download_clicked(self) -> None:
        if self.model.rowCount() == 0:
            self.message_requested.emit(
                "warning",
                self.tr("Warning"), self.tr("Add at least one file or URL first."),
                INFOBAR_MS_WARNING,
                None,
            )
            return

        # Auto-remove issue links (invalid URLs, failed metadata) before starting
        removed = self._remove_issue_tasks()
        if removed:
            self.message_requested.emit(
                "info",
                self.tr("Invalid links removed"),
                self.tr("Removed {} invalid or failed link(s) from the queue.").format(removed),
                INFOBAR_MS_INFO,
                None,
            )

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
            self.message_requested.emit(
                "warning",
                self.tr("Nothing to download"),
                self.tr("No pending tasks. Add new URLs or clear completed ones first."),
                INFOBAR_MS_WARNING,
                None,
            )
            return

        self._enhance_enabled = self.optimize_button.isChecked()
        self.start_button.setEnabled(False)
        self.cancel_button.show()
        self.progress_bar.setValue(0)
        self.status_label.setText(self.tr("Starting download…"))
        self.message_requested.emit(
            "info",
            self.tr("Download started"),
            self.tr("Queued {} task(s){}.")
            .format(
                len(tasks_to_run),
                self.tr(" with Enhance") if self._enhance_enabled else "",
            ),
            INFOBAR_MS_INFO,
            None,
        )
        self.download_requested.emit(tasks_to_run)

    def _on_cancel(self) -> None:
        # Update own UI immediately; parent handles manager cancellation
        self.start_button.setEnabled(True)
        self.cancel_button.hide()
        self.progress_bar.setValue(0)
        self.status_label.setText(self.tr("Cancelled"))
        self.message_requested.emit(
            "warning",
            self.tr("Cancelled"), self.tr("Download cancelled."),
            INFOBAR_MS_WARNING,
            None,
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
        self.message_requested.emit(
            "success",
            self.tr("Done"), self.tr("All downloads complete."),
            INFOBAR_MS_SUCCESS,
            InfoBarPosition.BOTTOM,
        )

    def on_error(self, error: str) -> None:
        self.start_button.setEnabled(True)
        self.cancel_button.hide()
        self.progress_bar.error()
        self.message_requested.emit(
            "error",
            self.tr("Error"), self.tr(error),
            INFOBAR_MS_ERROR,
            None,
        )

    # ── Public task API ────────────────────────────────────────────────────

    def set_task(self, task: dict) -> None:
        title = resolve_task_title(task)
        host = task.get("host", "")
        fmt = task.get("format", "")
        path = resolve_task_path(task.get("file_path"), task.get("path"))
        url = task.get("url") or path
        self.model.add_task(title=title, host=host, fmt=fmt, path=path, url=url)

    def add_url(self, url: str) -> None:
        self._add_url_task(url)

    # ── Drag & drop ────────────────────────────────────────────────────────

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        event.accept() if event.mimeData().hasUrls() else event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        added = 0
        for url in event.mimeData().urls():
            path_str = url.toLocalFile()
            if not path_str:
                continue
            path = Path(path_str)
            if not path.is_file():
                continue
            ext = path.suffix.lstrip(".").lower()
            if ext in SUPPORTED_EXTENSIONS:
                self.model.add_task(title=path.name, host="Local", fmt=ext, path=str(path))
                added += 1
            else:
                self._emit_message(
                    "warning", self.tr(f"Skipped: .{ext}"),
                    self.tr("Unsupported format — drop video/audio files only."),
                    INFOBAR_MS_WARNING,
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
            folder = dir_for_path(first_path)
            if folder is not None:
                menu.addAction(Action(
                    FIF.FOLDER, self.tr("Open Folder"),
                    triggered=lambda f=folder: QDesktopServices.openUrl(QUrl.fromLocalFile(str(f))),
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
                triggered=lambda: self._paste_clipboard_urls(clipboard_url),
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
                self._paste_clipboard_urls(text)
            event.accept()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event: QCloseEvent) -> None:
        for w in list(self._info_workers):
            if w.isRunning():
                w.quit()
                w.wait(500)
        self._info_workers.clear()
        for w in list(self._icon_workers):
            if w.isRunning():
                w.quit()
                w.wait(500)
        self._icon_workers.clear()
        super().closeEvent(event)


