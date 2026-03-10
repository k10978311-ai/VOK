"""Home interface: URL Download and Tasks tabs."""

import os
from datetime import datetime, timezone
from urllib.parse import urlparse

from PyQt5.QtWidgets import QSizePolicy, QStackedWidget, QVBoxLayout, QWidget
from qfluentwidgets import SegmentedWidget

from app.common.database.entity import QueueTask
from app.common.database.service import QueueTaskService
from app.common.paths import get_default_downloads_dir
from app.common.signal_bus import signal_bus
from app.common.sound import play_download_sound
from app.common.state import add_log_entry
from app.config.store import load_settings
from app.core.download import check_unsupported_url, detect_platform, normalize_url
from app.core.manager import DownloadJob, DownloadManager
from app.ui.utils import format_size

from .url_dowload_interface import UrlDownloadInterface
from .task_dowload_interface import TaskDownloadInterface

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

        # URL tab → task table
        self.url_interface.finished.connect(self._on_url_submitted)
        self.url_interface.bulk_finished.connect(self._on_bulk_submitted)

        # Tasks tab download button → start jobs
        self.task_interface.download_requested.connect(self._on_tasks_download_requested)

        # Tasks tab cancel button → cancel all running jobs
        self.task_interface.cancel_requested.connect(self._on_cancel_all)

        # Intercept row removal to keep DB in sync
        self.task_interface.model.rowsAboutToBeRemoved.connect(self._on_rows_about_to_be_removed)

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
        """Return a direct (synchronous) QueueTaskService for the open DB connection."""
        from PyQt5.QtSql import QSqlDatabase
        from app.common.database.db_initializer import DBInitializer
        db = QSqlDatabase.database(DBInitializer.CONNECTION_NAME)
        if not db.isOpen():
            return None
        return QueueTaskService(db)

    def _restore_queue(self) -> None:
        """On startup: reload Pending/Downloading rows, reset Downloading → Pending."""
        svc = self._get_queue_service()
        if not svc:
            return
        rows = svc.list_recoverable()
        if not rows:
            return
        for qt in rows:
            # Reset stuck "Downloading" tasks back to Pending
            if qt.status == "Downloading":
                svc.update_status(qt.id, "Pending")
                qt.status = "Pending"
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

    def _persist_task(self, row_idx: int, task: dict) -> None:
        """Insert a new QueueTask row for the given task dict and remember its id."""
        svc = self._get_queue_service()
        if not svc:
            return
        fmt = load_settings().get("download_format", "Best (video+audio)")
        qt = QueueTask(
            url=task.get("url", ""),
            title=task.get("title", ""),
            host=task.get("host", ""),
            format_key=fmt,
            output_dir=task.get("path", ""),
            cookies_file=task.get("cookies_file", ""),
            status="Pending",
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
        s = load_settings()
        save = s.get("download_path", str(get_default_downloads_dir()))
        host = ""
        if url_or_path.startswith(("http://", "https://")):
            # fast-fail known-unsupported patterns
            errmsg = check_unsupported_url(url_or_path)
            if errmsg:
                from qfluentwidgets import InfoBar
                InfoBar.warning("Unsupported URL", errmsg, duration=5000, parent=self)
                return
            # normalise embed/modal URLs before storing
            url_or_path, _note = normalize_url(url_or_path)
            host = self._resolve_host(url_or_path)
        task_dict = {
            "title":  url_or_path,
            "url":    url_or_path,
            "host":   host,
            "path":   url_or_path if os.path.isfile(url_or_path) else save,
        }
        self.task_interface.set_task(task_dict)
        row_idx = self.task_interface.model.rowCount() - 1
        self._persist_task(row_idx, task_dict)
        self.switch_to_tasks()

    def _on_bulk_submitted(self, items: list) -> None:
        """Multiple URLs/entry-dicts from URL tab → add all to task table, switch."""
        s = load_settings()
        save = s.get("download_path", str(get_default_downloads_dir()))
        for item in items:
            if isinstance(item, dict):
                url   = item.get("url", "")
                title = item.get("title") or url
                host  = item.get("host", "")
            else:
                url = item
                title = url
                host = ""
            if url.startswith(("http://", "https://")):
                if check_unsupported_url(url):
                    continue  # silently skip; URL tab already warned on individual adds
                url, _ = normalize_url(url)
                if not host:
                    host = self._resolve_host(url)
            task_dict = {
                "title":  title,
                "url":    url,
                "host":   host,
                "path":   save,
            }
            self.task_interface.set_task(task_dict)
            row_idx = self.task_interface.model.rowCount() - 1
            self._persist_task(row_idx, task_dict)
        self.switch_to_tasks()

    # ── Download engine ───────────────────────────────────────────────────

    def _on_tasks_download_requested(self, tasks: list) -> None:
        """Create and enqueue a DownloadJob for each task from the Tasks tab."""
        s = load_settings()
        out = s.get("download_path", str(get_default_downloads_dir()))
        fmt = s.get("download_format", "Best (video+audio)")
        cookies = s.get("cookies_file", "")
        self._manager.set_max_workers(int(s.get("concurrent_downloads", 2)))
        self._manager.set_concurrent_fragments(int(s.get("concurrent_fragments", 4)))

        enqueued = 0
        for task in tasks:
            # Use stored url field; fall back to title (for manually-typed tasks)
            url = task.get("url") or task.get("title", "")
            if not url:
                continue

            # For local files the output dir is the file's parent; otherwise use setting
            save_path = task.get("path", "")
            if os.path.isfile(save_path):
                output_dir = os.path.dirname(save_path)
            elif os.path.isdir(save_path):
                output_dir = save_path
            else:
                output_dir = out

            job = DownloadJob(
                url=url,
                output_dir=output_dir,
                format_key=fmt,
                single_video=True,
                cookies_file=cookies,
            )

            # Resolve row index by object identity (get_task returns the actual dict)
            row_idx: int | None = None
            for i in range(self.task_interface.model.rowCount()):
                if self.task_interface.model.get_task(i) is task:
                    row_idx = i
                    break

            self._active_jobs.add(job.job_id)
            if row_idx is not None:
                self._job_to_row[job.job_id] = row_idx
                self.task_interface.update_task_progress(row_idx, 0, status="Downloading")
                self._db_update_status(row_idx, "Downloading", job_id=job.job_id)

            self._manager.enqueue(job)
            enqueued += 1

        if enqueued:
            self.task_interface.set_progress(
                0, self.tr(f"Queued {enqueued} job(s) — downloading…")
            )

    def _on_cancel_all(self) -> None:
        """Cancel all running jobs, mark rows as Canceled, and reset UI."""
        for job_id, row in list(self._job_to_row.items()):
            self._db_update_status(row, "Canceled")
            self.task_interface.update_task_progress(row, 0, status="Canceled")
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
                row, progress_pct, status="Downloading", size=size_str
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
            final_status = "Done" if success else "Error"
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
