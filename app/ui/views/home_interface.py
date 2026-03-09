"""Home interface: URL Download and Tasks tabs."""

import os
from urllib.parse import urlparse

from PyQt5.QtWidgets import QSizePolicy, QStackedWidget, QVBoxLayout, QWidget
from qfluentwidgets import SegmentedWidget

from app.common.paths import get_default_downloads_dir
from app.common.signal_bus import signal_bus
from app.common.sound import play_download_sound
from app.common.state import add_log_entry
from app.config.store import load_settings
from app.core.manager import DownloadJob, DownloadManager

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

        # URL tab → task table
        self.url_interface.finished.connect(self._on_url_submitted)
        self.url_interface.bulk_finished.connect(self._on_bulk_submitted)

        # Tasks tab download button → start jobs
        self.task_interface.download_requested.connect(self._on_tasks_download_requested)

        # Tasks tab cancel button → cancel all running jobs
        self.task_interface.cancel_button.clicked.connect(self._manager.cancel_all)

        # Manager feedback → per-row updates
        self._manager.progress.connect(self._on_download_progress)
        self._manager.job_progress_detail.connect(self._on_download_progress_detail)
        self._manager.job_finished.connect(self._on_download_job_finished)

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

    # ── URL / Bulk submissions ────────────────────────────────────────────

    def _on_url_submitted(self, url_or_path: str) -> None:
        """Single URL or file path from URL tab → add to task table, switch."""
        host = ""
        if url_or_path.startswith(("http://", "https://")):
            try:
                host = urlparse(url_or_path).netloc.replace("www.", "")
            except Exception:
                pass
        self.task_interface.set_task({
            "title": url_or_path,
            "url":   url_or_path,
            "host":  host,
            "path":  url_or_path if os.path.isfile(url_or_path) else "",
        })
        self.switch_to_tasks()

    def _on_bulk_submitted(self, urls: list) -> None:
        """Multiple URLs from URL tab → add all to task table, switch."""
        for url in urls:
            try:
                host = urlparse(url).netloc.replace("www.", "")
            except Exception:
                host = ""
            self.task_interface.set_task({"title": url, "url": url, "host": host})
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

            self._manager.enqueue(job)

    def _on_download_progress(self, job_id: str, value: float) -> None:
        row = self._job_to_row.get(job_id)
        if row is not None:
            pct = int(max(0.0, min(1.0, value)) * 100)
            self.task_interface.update_task_progress(row, pct)
        signal_bus.download_progress.emit(job_id, max(0.0, min(1.0, value)))

    def _on_download_progress_detail(
        self, job_id: str, pct: float, speed: str, eta: str, cur: str, tot: str
    ) -> None:
        signal_bus.download_progress_detail.emit(job_id, pct, speed, eta, cur, tot)
        row = self._job_to_row.get(job_id)
        if row is not None:
            size_str = tot or cur
            self.task_interface.update_task_progress(
                row, int(max(0.0, min(1.0, pct)) * 100), size=size_str
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
            self.task_interface.update_task_progress(
                row,
                100 if success else 0,
                status="Done" if success else "Error",
            )

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
