"""Home interface: URL Download and Tasks tabs."""

import os
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QSizePolicy, QStackedWidget, QVBoxLayout, QWidget
from qfluentwidgets import SegmentedWidget, InfoBar, InfoBarPosition

from app.common.database.entity import QueueTask
from app.common.database.entity.queue_task import (
    QUEUE_STATUS_PENDING,
    QUEUE_STATUS_RUNNING,
    QUEUE_STATUS_DONE,
    QUEUE_STATUS_ERROR,
    QUEUE_STATUS_CANCELED,
)
from app.common.database.service import QueueTaskService
from app.common.paths import get_default_downloads_dir
from app.common.signal_bus import signal_bus
from app.common.sound import play_download_sound
from app.common.state import add_log_entry
from app.config.store import load_settings
from app.core.download import check_unsupported_url, detect_platform, normalize_url
from app.core.manager import DownloadJob, DownloadManager
from app.ui.utils import format_size

from app.common.concurrent import HostIconFetchWorker, MetaFetchWorker

from .url_dowload_interface import UrlDownloadInterface
from .task_dowload_interface import TaskDownloadInterface

# Centralized message durations (ms)
INFOBAR_MS_SUCCESS = 3000
INFOBAR_MS_ERROR = 5000
INFOBAR_MS_WARNING = 4000
INFOBAR_MS_INFO = 3000


class HomeInterface(QWidget):
    """Tabbed download home: URL Download (enter URL) | Tasks (table)."""

    _TAB_URL = "url_download"
    _TAB_TASKS = "tasks"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("HomeInterface")

        self.pivot = SegmentedWidget(self)
        self.pivot.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)

        self.stackedWidget = QStackedWidget(self)

        self.url_interface = UrlDownloadInterface(self)
        self.task_interface = TaskDownloadInterface(self)

        self._add_tab(self.url_interface, self._TAB_URL, self.tr("URL Download"))
        self._add_tab(self.task_interface, self._TAB_TASKS, self.tr("Tasks"))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        layout.addWidget(self.pivot)
        layout.addWidget(self.stackedWidget)

        self.stackedWidget.currentChanged.connect(self._on_index_changed)
        self.stackedWidget.setCurrentWidget(self.url_interface)
        self.pivot.setCurrentItem(self._TAB_URL)

        # ── Download engine ───────────────────────────────────────────────
        self._manager = DownloadManager(parent=self)
        self._active_jobs: set[str] = set()
        self._job_to_row: dict[str, int] = {}   # job_id → task model row index
        self._job_errors: set[str] = set()       # job_ids that ended with error
        # db_id (QueueTask.id) per row — used to update / delete persisted records
        self._row_to_db_id: dict[int, str] = {}  # row_idx → QueueTask.id
        self._queue_service: QueueTaskService | None = None  # cached for persistence
        self._icon_workers: list = []  # HostIconFetchWorker instances
        self._meta_workers: list = []  # MetaFetchWorker instances (title/size from URL tab)

        # URL tab → task table
        self.url_interface.finished.connect(self._on_url_submitted)
        self.url_interface.bulk_finished.connect(self._on_bulk_submitted)

        # Tasks tab download button → start jobs
        self.task_interface.download_requested.connect(self._on_tasks_download_requested)

        # Tasks tab cancel button → cancel all running jobs
        self.task_interface.cancel_requested.connect(self._on_cancel_all)

        # Intercept row removal to keep DB in sync
        self.task_interface.model.rowsAboutToBeRemoved.connect(self._on_rows_about_to_be_removed)

        # Centralized messages from both tabs
        self.url_interface.message_requested.connect(self._show_message)
        self.task_interface.message_requested.connect(self._show_message)

        # Manager feedback → per-row updates
        self._manager.progress.connect(self._on_download_progress)
        self._manager.job_progress_detail.connect(self._on_download_progress_detail)
        self._manager.job_finished.connect(self._on_download_job_finished)

        # Restore incomplete tasks from previous session
        self._restore_queue()

    # ── Helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _resolve_host(url: str) -> str:
        """Return a clean platform/host name for a URL."""
        platform = detect_platform(url)
        if platform and platform != "Unknown":
            return platform
        try:
            return urlparse(url).netloc.replace("www.", "")
        except Exception:
            return ""

    def _refresh_host_icon_for_url(self, url: str) -> None:
        """Refresh the host column for the row with this URL (after icon cache updated)."""
        from app.ui.components.download_task_model import COL_HOST
        model = self.task_interface.model
        row = model.find_url(url)
        if row >= 0:
            idx = model.index(row, COL_HOST)
            model.dataChanged.emit(idx, idx, [Qt.DecorationRole])

    def _start_host_icon_fetch(self, url: str) -> None:
        """Start background fetch of host icon for URL; refresh row when done."""
        if not url or not url.startswith(("http://", "https://")):
            return
        worker = HostIconFetchWorker(url, parent=self)
        worker.icon_fetched.connect(self._refresh_host_icon_for_url)

        def _cleanup():
            if worker in self._icon_workers:
                self._icon_workers.remove(worker)
        worker.finished.connect(_cleanup)
        self._icon_workers.append(worker)
        worker.start()

    def _start_metadata_fetch(self, url: str, cookies_file: str = "") -> None:
        """Start background metadata fetch (title, size) for URL tab tasks; update row when done."""
        if not url or not url.startswith(("http://", "https://")):
            return
        worker = MetaFetchWorker(url=url, cookies_file=cookies_file or "", parent=self)
        worker.data_ready.connect(self._on_metadata_ready)

        def _cleanup():
            if worker in self._meta_workers:
                self._meta_workers.remove(worker)
        worker.finished_signal.connect(lambda *a: _cleanup())
        self._meta_workers.append(worker)
        worker.start()

    def _on_metadata_ready(self, info: dict) -> None:
        """Update task row with title, host, and size from yt-dlp metadata (URL tab flow)."""
        url = info.get("webpage_url") or info.get("url") or ""
        if not url:
            return
        model = self.task_interface.model
        row = model.find_url(url)
        if row < 0:
            return
        title = info.get("title") or info.get("fulltitle") or ""
        uploader = (
            info.get("uploader") or info.get("channel")
            or info.get("artist") or ""
        )
        fs = info.get("filesize") or info.get("filesize_approx")
        size_str = format_size(fs) if (fs is not None and fs > 0) else None
        kwargs = {}
        if title:
            kwargs["title"] = title
        if uploader:
            task = model.get_task(row)
            if task and not task.get("host"):
                kwargs["host"] = uploader
        if size_str:
            kwargs["size"] = size_str
        if kwargs:
            model.update_task(row, **kwargs)

    # ── Tab helpers ───────────────────────────────────────────────────────

    def _add_tab(self, widget: QWidget, route_key: str, text: str):
        widget.setObjectName(route_key)
        self.stackedWidget.addWidget(widget)
        self.pivot.addItem(
            routeKey=route_key,
            text=text,
            onClick=lambda: self.stackedWidget.setCurrentWidget(widget),
        )

    def _on_index_changed(self, index: int):
        widget = self.stackedWidget.widget(index)
        if widget:
            self.pivot.setCurrentItem(widget.objectName())
        # When switching to Tasks tab, auto-remove rows with invalid URLs (e.g. pasted plain text)
        if widget is self.task_interface:
            removed = self.task_interface._remove_issue_tasks(include_failed_metadata=False)
            if removed:
                self._show_message(
                    "info",
                    self.tr("Invalid links removed"),
                    self.tr("Removed {} invalid link(s) (not video URLs).").format(removed),
                    INFOBAR_MS_INFO,
                )

    def _show_message(
        self,
        level: str,
        title: str,
        message: str,
        duration: int = INFOBAR_MS_INFO,
        position=None,
    ) -> None:
        """Show an InfoBar from either URL or Tasks tab; parent is always home for consistent placement."""
        kwargs = {"duration": duration, "parent": self}
        if position is not None:
            kwargs["position"] = position
        if level == "success":
            InfoBar.success(title, message, **kwargs)
        elif level == "warning":
            InfoBar.warning(title, message, **kwargs)
        elif level == "error":
            InfoBar.error(title, message, **kwargs)
        else:
            InfoBar.info(title, message, **kwargs)

    # ── Public navigation ─────────────────────────────────────────────────

    def switch_to_url(self):
        """Navigate to the URL Download tab."""
        self.stackedWidget.setCurrentWidget(self.url_interface)
        self.pivot.setCurrentItem(self._TAB_URL)

    def switch_to_tasks(self):
        """Navigate to the Tasks table tab."""
        self.stackedWidget.setCurrentWidget(self.task_interface)
        self.pivot.setCurrentItem(self._TAB_TASKS)

    # ── Persistence helpers ──────────────────────────────────────────

    def _get_queue_service(self) -> QueueTaskService | None:
        """Return QueueTaskService for the open DB; cached for the window lifetime."""
        if self._queue_service is not None:
            return self._queue_service
        from PyQt5.QtSql import QSqlDatabase
        from app.common.database.db_initializer import DBInitializer
        db = QSqlDatabase.database(DBInitializer.CONNECTION_NAME)
        if not db.isOpen():
            return None
        self._queue_service = QueueTaskService(db)
        return self._queue_service

    def _get_download_config(self) -> dict[str, Any]:
        """Load settings once and return download-related keys for this flow."""
        s = load_settings()
        return {
            "download_path": s.get("download_path", str(get_default_downloads_dir())),
            "download_format": s.get("download_format", "Best (video+audio)"),
            "cookies_file": s.get("cookies_file", ""),
            "concurrent_downloads": int(s.get("concurrent_downloads", 2)),
            "concurrent_fragments": int(s.get("concurrent_fragments", 4)),
        }

    def _restore_queue(self) -> None:
        """On startup: reload Pending/Downloading rows, reset Downloading → Pending."""
        svc = self._get_queue_service()
        if not svc:
            return
        rows = svc.list_recoverable()
        if not rows:
            return
        for qt in rows:
            if qt.status == QUEUE_STATUS_RUNNING:
                svc.update_status(qt.id, QUEUE_STATUS_PENDING)
                qt.status = QUEUE_STATUS_PENDING
            row_idx = self.task_interface.model.add_task(
                title=qt.title or qt.url,
                host=qt.host,
                fmt=qt.format_key,
                path=qt.output_dir,
                url=qt.url,
            )
            self._row_to_db_id[row_idx] = qt.id
        if rows:
            self.switch_to_tasks()

    def _build_task_dict(
        self,
        url: str,
        title: str = "",
        host: str = "",
        path: str = "",
    ) -> dict[str, Any]:
        """Build a task dict for the task model and persistence (single source of shape)."""
        return {
            "title": title or url,
            "url": url,
            "host": host,
            "path": path or str(get_default_downloads_dir()),
        }

    def _persist_task(self, row_idx: int, task: dict) -> None:
        """Insert a new QueueTask row for the given task dict and remember its id."""
        svc = self._get_queue_service()
        if not svc:
            return
        cfg = self._get_download_config()
        qt = QueueTask(
            url=task.get("url", ""),
            title=task.get("title", ""),
            host=task.get("host", ""),
            format_key=cfg["download_format"],
            output_dir=task.get("path", ""),
            cookies_file=cfg.get("cookies_file", ""),
            status=QUEUE_STATUS_PENDING,
            create_time=datetime.now(timezone.utc).isoformat(),
        )
        svc.add(qt)
        self._row_to_db_id[row_idx] = qt.id

    def _db_update_status(self, row_idx: int, status: str, job_id: str = "") -> None:
        """Update persisted row status (and optionally job_id)."""
        db_id = self._row_to_db_id.get(row_idx)
        if not db_id:
            return
        svc = self._get_queue_service()
        if not svc:
            return
        svc.update_status(db_id, status)
        if job_id:
            svc.update_job_id(db_id, job_id)

    def _output_dir_for_task(self, task: dict, default_dir: str) -> str:
        """Resolve output directory for a task (file parent, dir path, or default)."""
        save_path = task.get("path", "")
        if os.path.isfile(save_path):
            return os.path.dirname(save_path)
        if os.path.isdir(save_path):
            return save_path
        return default_dir

    def _resolve_row_for_task(self, task: dict) -> int | None:
        """Resolve model row index for this task (identity first, then URL fallback)."""
        model = self.task_interface.model
        for i in range(model.rowCount()):
            if model.get_task(i) is task:
                return i
        url = task.get("url") or task.get("title", "")
        if url:
            idx = model.find_url(url)
            if idx >= 0:
                return idx
        return None

    def _build_job(
        self,
        task: dict,
        output_dir: str,
        format_key: str,
        cookies_file: str,
    ) -> DownloadJob:
        """Build a DownloadJob from a task dict and config."""
        url = task.get("url") or task.get("title", "")
        return DownloadJob(
            url=url,
            output_dir=output_dir,
            format_key=format_key,
            single_video=True,
            cookies_file=cookies_file,
        )

    def _db_delete_rows(self, row_indices: list[int]) -> None:
        """Delete persisted records for the given row indices."""
        ids = [self._row_to_db_id.pop(i, None) for i in row_indices]
        ids = [i for i in ids if i]
        if not ids:
            return
        svc = self._get_queue_service()
        if svc:
            svc.remove_batch(ids)
        # Remap remaining indices after removal (rows shift down)
        sorted_removed = sorted(row_indices, reverse=True)
        new_map: dict[int, str] = {}
        for idx, db_id in self._row_to_db_id.items():
            shift = sum(1 for r in sorted_removed if r < idx)
            new_map[idx - shift] = db_id
        self._row_to_db_id = new_map

    def _on_rows_about_to_be_removed(self, parent, first: int, last: int) -> None:
        """Connected to model.rowsAboutToBeRemoved — delete DB rows synchronously."""
        self._db_delete_rows(list(range(first, last + 1)))

    # ── URL / Bulk submissions ──────────────────────────────────────────

    def _on_url_submitted(self, url_or_path: str) -> None:
        """Single URL or file path from URL tab → add to task table, switch."""
        cfg = self._get_download_config()
        save = cfg["download_path"]
        host = ""
        if url_or_path.startswith(("http://", "https://")):
            errmsg = check_unsupported_url(url_or_path)
            if errmsg:
                self._show_message("warning", "Unsupported URL", errmsg, duration=5000)
                return
            url_or_path, _note = normalize_url(url_or_path)
            host = self._resolve_host(url_or_path)
        path = url_or_path if os.path.isfile(url_or_path) else save
        task_dict = self._build_task_dict(url_or_path, url_or_path, host, path)
        self.task_interface.set_task(task_dict)
        row_idx = self.task_interface.model.rowCount() - 1
        self._persist_task(row_idx, task_dict)
        if url_or_path.startswith(("http://", "https://")):
            self._start_host_icon_fetch(url_or_path)
            self._start_metadata_fetch(url_or_path, cfg.get("cookies_file", ""))
        self.switch_to_tasks()

    def _on_bulk_submitted(self, items: list) -> None:
        """Multiple URLs/entry-dicts from URL tab → add all to task table, switch."""
        cfg = self._get_download_config()
        save = cfg["download_path"]
        for item in items:
            if isinstance(item, dict):
                url = item.get("url", "")
                title = item.get("title") or url
                host = item.get("host", "")
            else:
                url = item
                title = url
                host = ""
            if url.startswith(("http://", "https://")):
                if check_unsupported_url(url):
                    continue
                url, _ = normalize_url(url)
                if not host:
                    host = self._resolve_host(url)
            task_dict = self._build_task_dict(url, title, host, save)
            self.task_interface.set_task(task_dict)
            row_idx = self.task_interface.model.rowCount() - 1
            self._persist_task(row_idx, task_dict)
            if url.startswith(("http://", "https://")):
                self._start_host_icon_fetch(url)
                self._start_metadata_fetch(url, cfg.get("cookies_file", ""))
        self.switch_to_tasks()

    # ── Download engine ───────────────────────────────────────────────────

    def _on_tasks_download_requested(self, tasks: list) -> None:
        """Create and enqueue a DownloadJob for each task from the Tasks tab."""
        cfg = self._get_download_config()
        out = cfg["download_path"]
        fmt = cfg["download_format"]
        cookies = cfg["cookies_file"]
        self._manager.set_max_workers(cfg["concurrent_downloads"])
        self._manager.set_concurrent_fragments(cfg["concurrent_fragments"])

        enqueued = 0
        for task in tasks:
            url = task.get("url") or task.get("title", "")
            if not url:
                continue

            output_dir = self._output_dir_for_task(task, out)
            job = self._build_job(task, output_dir, fmt, cookies)
            row_idx = self._resolve_row_for_task(task)

            self._active_jobs.add(job.job_id)
            if row_idx is not None:
                self._job_to_row[job.job_id] = row_idx
                self.task_interface.update_task_progress(row_idx, 0, status=QUEUE_STATUS_RUNNING)
                self._db_update_status(row_idx, QUEUE_STATUS_RUNNING, job_id=job.job_id)

            self._manager.enqueue(job)
            enqueued += 1

        if enqueued:
            self.task_interface.set_progress(
                0, self.tr(f"Queued {enqueued} job(s) — downloading…")
            )

    def _on_cancel_all(self) -> None:
        """Cancel all running jobs, mark rows as Canceled, and reset UI."""
        for job_id, row in list(self._job_to_row.items()):
            self._db_update_status(row, QUEUE_STATUS_CANCELED)
            self.task_interface.update_task_progress(row, 0, status=QUEUE_STATUS_CANCELED)
        self._job_to_row.clear()
        self._active_jobs.clear()
        self._job_errors.clear()
        self._manager.cancel_all()

    def _on_download_progress(self, job_id: str, value: float) -> None:
        signal_bus.download_progress.emit(job_id, max(0.0, min(1.0, value)))

    def _on_download_progress_detail(
        self, job_id: str, pct: float, speed: str, eta: str, cur: str, tot: str
    ) -> None:
        signal_bus.download_progress_detail.emit(job_id, pct, speed, eta, cur, tot)
        row = self._job_to_row.get(job_id)
        if row is not None:
            size_str = tot if (tot and tot != "?") else cur
            progress_pct = int(max(0.0, min(1.0, pct)) * 100)
            self.task_interface.update_task_progress(
                row, progress_pct, status=QUEUE_STATUS_RUNNING, size=size_str
            )
        # Update overall progress bar = average of all active rows
        if self._job_to_row:
            avg_pct = sum(
                (self.task_interface.model.get_task(r) or {}).get("progress", 0)
                for r in self._job_to_row.values()
            ) // max(1, len(self._job_to_row))
            active = len(self._active_jobs)
            self.task_interface.set_progress(
                avg_pct,
                f"{speed}  ETA {eta}  ({active} active)",
            )

    def _on_download_job_finished(
        self, job_id: str, success: bool, message: str, filepath: str, size_bytes: int
    ) -> None:
        self._active_jobs.discard(job_id)
        row = self._job_to_row.pop(job_id, None)

        s = load_settings()
        if success and s.get("sound_alert_on_complete", True):
            play_download_sound(success=True)
        elif not success and s.get("sound_alert_on_error", True):
            play_download_sound(success=False)

        add_log_entry("info" if success else "error", message)
        signal_bus.download_finished.emit(job_id, success, message, filepath, size_bytes)

        if row is not None:
            final_size = format_size(size_bytes) if size_bytes > 0 else ""
            final_status = QUEUE_STATUS_DONE if success else QUEUE_STATUS_ERROR
            self.task_interface.update_task_progress(
                row,
                100 if success else 0,
                status=final_status,
                size=final_size,
            )
            self._db_update_status(row, final_status)

        if not success:
            self._job_errors.add(job_id)

        # When the last queued job finishes, update overall UI state
        if not self._active_jobs:
            had_errors = bool(self._job_errors)
            self._job_errors.clear()
            if had_errors:
                self.task_interface.on_error("Some downloads failed — check individual rows.")
            else:
                self.task_interface.on_finished(filepath, filepath)
