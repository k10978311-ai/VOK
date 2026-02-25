"""Downloader view: single, bulk, and selective download with HD/4K/Photo formats."""

import os
import subprocess
import sys
from datetime import datetime

from PyQt5.QtCore import Qt, QPoint, QTimer
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QHBoxLayout,
    QHeaderView,
    QSizePolicy,
    QTableWidgetItem,
    QVBoxLayout,
)
from qfluentwidgets import (
    Action,
    BodyLabel,
    CardWidget,
    ComboBox,
    FluentIcon,
    InfoBar,
    InfoBarPosition,
    IndeterminateProgressBar,
    LineEdit,
    PlainTextEdit,
    ProgressBar,
    PrimaryPushButton,
    PushButton,
    RoundMenu,
    SwitchButton,
    SegmentedWidget,
    TableWidget,
)

from app.common.paths import get_default_downloads_dir
from app.common.state import add_log_entry
from app.config import load_settings
from app.core.download import detect_platform
from app.core.manager import DownloadJob, DownloadManager
from app.core.scraper import PlaylistFetchWorker, fmt_duration, fmt_date
from app.ui.components import CardHeader, DownloadPathPanel, DownloadTableCard
from app.ui.helpers import DOWNLOAD_FORMATS, host_icon
from app.ui.utils import format_size, strip_ansi

from .base import BaseView

# Limits to avoid UI freeze and crashes with huge lists
MAX_BULK_URLS = 2000
MAX_PLAYLIST_DISPLAY = 1500
PROGRESS_THROTTLE_MS = 120
# Skip per-row log text updates when job count exceeds this (avoids UI flood)
LOG_TABLE_UPDATE_MAX_JOBS = 80


class DownloaderView(BaseView):
    """Multi-job downloader: single URL, bulk URL list, and selective playlist download."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Downloader")

        self._manager = DownloadManager(parent=self)
        self._manager.log_line.connect(self._on_job_log)
        self._manager.progress.connect(self._on_progress)
        self._manager.job_finished.connect(self._on_job_finished)
        self._active_jobs: set[str] = set()
        self._job_to_row: dict[str, int] = {}
        self._job_progress: dict[str, float] = {}  # job_id -> 0.0..1.0 for overall header bar
        self._playlist_worker: PlaylistFetchWorker | None = None
        self._direct_playlist_worker: PlaylistFetchWorker | None = None  # for profile/playlist → N jobs
        self._progress_timer = QTimer(self)
        self._progress_timer.setSingleShot(True)
        self._progress_timer.timeout.connect(self._flush_progress_ui)
        self._progress_flush_pending = False

        self._build_mode_bar()
        self._build_url_card()
        self._build_bulk_card()
        self._build_selective_card()
        self._build_enhance_card()
        self._build_path_panel()
        self._build_format_card()
        self._build_progress()
        self._build_log_card()

        self._layout.addStretch(1)

        # Start with Single mode: only URL card visible
        self._bulk_card.setVisible(False)
        self._selective_card.setVisible(False)
        self._enhance_card.setVisible(False)

    # ── Card builders ─────────────────────────────────────────────────────

    def _build_mode_bar(self):
        """Top segmented bar: Single | Bulk | Selective | Enhance."""
        self._mode_segmented = SegmentedWidget(self)
        self._mode_segmented.insertItem(0, "single", "Single", self._on_download_mode_changed)
        self._mode_segmented.insertItem(1, "bulk", "Bulk", self._on_download_mode_changed)
        self._mode_segmented.insertItem(2, "selective", "Selective", self._on_download_mode_changed)
        self._mode_segmented.insertItem(3, "enhance", "Enhance", self._on_download_mode_changed)
        self._mode_segmented.setCurrentItem("single")
        self._layout.addWidget(self._mode_segmented)

    def _build_url_card(self):
        self._url_card = CardWidget(self)
        lay = QVBoxLayout(self._url_card)
        lay.setSpacing(10)
        lay.addWidget(CardHeader(FluentIcon.LINK, "Video URL", self._url_card))

        url_row = QHBoxLayout()
        url_row.addWidget(BodyLabel("URL", self._url_card))
        self._url_edit = LineEdit(self._url_card)
        self._url_edit.setPlaceholderText(
            "https://  —  YouTube, TikTok, Douyin, Kuaishou, Instagram, Facebook, Pinterest, Twitter/X …"
        )
        self._url_edit.setClearButtonEnabled(True)
        url_row.addWidget(self._url_edit, 1)
        lay.addLayout(url_row)

        self._layout.addWidget(self._url_card)

    def _build_path_panel(self):
        """Path panel component: current download folder + Open folder."""
        self._path_panel = DownloadPathPanel(self)
        self._layout.addWidget(self._path_panel)

    def _build_bulk_card(self):
        self._bulk_card = CardWidget(self)
        lay = QVBoxLayout(self._bulk_card)
        lay.setSpacing(10)
        lay.addWidget(CardHeader(FluentIcon.COPY, "Bulk URLs", self._bulk_card))
        lay.addWidget(BodyLabel("Paste one URL per line:", self._bulk_card))
        self._bulk_edit = PlainTextEdit(self._bulk_card)
        self._bulk_edit.setPlaceholderText("https://youtube.com/watch?v=…\nhttps://tiktok.com/@user/video/…\n…")
        self._bulk_edit.setMinimumHeight(120)
        lay.addWidget(self._bulk_edit)
        self._layout.addWidget(self._bulk_card)

    def _build_enhance_card(self):
        """Placeholder card for Enhance mode: Coming soon."""
        self._enhance_card = CardWidget(self)
        lay = QVBoxLayout(self._enhance_card)
        lay.setSpacing(10)
        lay.addWidget(CardHeader(FluentIcon.SYNC, "Enhance", self._enhance_card))
        coming = BodyLabel("Coming soon!", self._enhance_card)
        coming.setStyleSheet("font-size: 16px; padding: 24px 0;")
        lay.addWidget(coming, 0, Qt.AlignCenter)
        self._layout.addWidget(self._enhance_card)

    def _build_selective_card(self):
        self._selective_card = CardWidget(self)
        lay = QVBoxLayout(self._selective_card)
        lay.setSpacing(10)

        hdr = QHBoxLayout()
        hdr.addWidget(CardHeader(FluentIcon.CHECKBOX, "Selective Download — Preview Playlist", self._selective_card))
        self._preview_btn = PushButton("Preview Playlist", self._selective_card)
        self._preview_btn.setIcon(FluentIcon.SEARCH)
        self._preview_btn.clicked.connect(self._preview_playlist)
        hdr.addWidget(self._preview_btn)
        lay.addLayout(hdr)

        self._preview_progress = IndeterminateProgressBar(self._selective_card)
        self._preview_progress.setVisible(False)
        lay.addWidget(self._preview_progress)

        self._sel_status = BodyLabel("", self._selective_card)
        lay.addWidget(self._sel_status)

        # Checkable playlist table
        self._sel_table = TableWidget(self._selective_card)
        self._sel_table.setColumnCount(5)
        self._sel_table.setHorizontalHeaderLabels(["✓", "Title", "Uploader", "Duration", "Date"])
        hdr_view = self._sel_table.horizontalHeader()
        hdr_view.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hdr_view.setSectionResizeMode(1, QHeaderView.Stretch)
        hdr_view.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        hdr_view.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        hdr_view.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self._sel_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._sel_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._sel_table.setAlternatingRowColors(True)
        self._sel_table.verticalHeader().setVisible(False)
        self._sel_table.setMinimumHeight(180)
        lay.addWidget(self._sel_table)

        sel_acts = QHBoxLayout()
        sel_all_btn = PushButton("Select All", self._selective_card)
        sel_all_btn.clicked.connect(lambda: self._set_all_checks(True))
        desel_btn = PushButton("Deselect All", self._selective_card)
        desel_btn.clicked.connect(lambda: self._set_all_checks(False))
        self._dl_selected_btn = PrimaryPushButton("Download Selected", self._selective_card)
        self._dl_selected_btn.setIcon(FluentIcon.DOWNLOAD)
        self._dl_selected_btn.clicked.connect(self._download_selected)
        self._dl_selected_btn.setEnabled(False)
        sel_acts.addWidget(sel_all_btn)
        sel_acts.addWidget(desel_btn)
        sel_acts.addStretch(1)
        sel_acts.addWidget(self._dl_selected_btn)
        lay.addLayout(sel_acts)

        self._sel_entries: list[dict] = []
        self._layout.addWidget(self._selective_card)

    def _build_format_card(self):
        card = CardWidget(self)
        lay = QVBoxLayout(card)
        lay.setSpacing(10)
        lay.addWidget(CardHeader(FluentIcon.MEDIA, "Format & actions", card))

        fmt_row = QHBoxLayout()
        fmt_row.addWidget(BodyLabel("Format", card))
        self._format_combo = ComboBox(card)
        self._format_combo.addItems(DOWNLOAD_FORMATS)
        fmt_row.addWidget(self._format_combo)
        fmt_row.addStretch(1)
        self._jobs_label = BodyLabel("", card)
        fmt_row.addWidget(self._jobs_label)
        self._start_btn = PrimaryPushButton("Download", card)
        self._start_btn.setIcon(FluentIcon.DOWNLOAD)
        self._start_btn.clicked.connect(self._start_download)
        self._stop_btn = PushButton("Stop all", card)
        self._stop_btn.setIcon(FluentIcon.CANCEL)
        self._stop_btn.clicked.connect(self._stop_all)
        self._stop_btn.setEnabled(False)
        fmt_row.addWidget(self._start_btn)
        fmt_row.addWidget(self._stop_btn)
        lay.addLayout(fmt_row)
        self._layout.addWidget(card)

    def _build_progress(self):
        """Top progress bar removed; per-row progress in table only."""
        self._progress_indet = None
        self._progress = None
        self._progress_pct_label = None

    def _build_log_card(self):
        card = DownloadTableCard(self)
        card.clear_btn.clicked.connect(self._clear_download_table)
        self._process_table = card.table
        self._process_table.customContextMenuRequested.connect(self._on_process_table_context_menu)
        self._layout.addWidget(card)

    def showEvent(self, event):
        """Refresh path panel when view is shown (e.g. after returning from Settings)."""
        super().showEvent(event)
        if hasattr(self, "_path_panel"):
            self._path_panel.refresh_path()

    # ── Mode switch (segmented) ──────────────────────────────────────────

    def _on_download_mode_changed(self):
        key = self._mode_segmented.currentRouteKey()
        is_enhance = key == "enhance"
        # Hide URL card in Bulk (paste URLs in bulk list) and in Enhance (coming soon)
        self._url_card.setVisible(not is_enhance and key != "bulk")
        self._bulk_card.setVisible(key == "bulk")
        self._selective_card.setVisible(key == "selective")
        self._enhance_card.setVisible(is_enhance)

    # ── Selective download helpers ─────────────────────────────────────────

    def _preview_playlist(self):
        url = self._url_edit.text().strip()
        if not url:
            self._sel_status.setText("Enter a URL first.")
            return
        if self._playlist_worker and self._playlist_worker.isRunning():
            return

        s = load_settings()
        self._playlist_worker = PlaylistFetchWorker(
            url, cookies_file=s.get("cookies_file", ""), parent=self
        )
        self._playlist_worker.log_line.connect(self._log_append)
        self._playlist_worker.entries_ready.connect(self._on_entries_ready)
        self._playlist_worker.finished_signal.connect(self._on_preview_done)
        self._preview_progress.setVisible(False)
        self._preview_btn.setEnabled(False)
        self._sel_status.setText("Fetching playlist…")
        self._playlist_worker.start()

    def _on_entries_ready(self, entries: list):
        total = len(entries)
        if total > MAX_PLAYLIST_DISPLAY:
            display_entries = entries[:MAX_PLAYLIST_DISPLAY]
            self._sel_status.setText(
                f"Showing first {MAX_PLAYLIST_DISPLAY} of {total} entries. Use Select All / Deselect All then Download."
            )
        else:
            display_entries = entries
            self._sel_status.setText("")
        self._sel_entries = display_entries
        self._sel_table.setUpdatesEnabled(False)
        try:
            self._sel_table.setRowCount(len(display_entries))
            for row, entry in enumerate(display_entries):
                chk = QTableWidgetItem()
                chk.setCheckState(Qt.Checked)
                self._sel_table.setItem(row, 0, chk)
                self._sel_table.setItem(row, 1, QTableWidgetItem(entry.get("title", "")))
                self._sel_table.setItem(row, 2, QTableWidgetItem(entry.get("uploader", "")))
                self._sel_table.setItem(row, 3, QTableWidgetItem(fmt_duration(entry.get("duration"))))
                self._sel_table.setItem(row, 4, QTableWidgetItem(fmt_date(entry.get("upload_date", ""))))
        finally:
            self._sel_table.setUpdatesEnabled(True)
        self._dl_selected_btn.setEnabled(bool(display_entries))

    def _on_preview_done(self, success: bool, msg: str):
        self._preview_progress.setVisible(False)
        self._preview_btn.setEnabled(True)
        self._sel_status.setText(msg)
        if not success:
            title = "Not supported" if "not supported" in msg.lower() else "Preview failed"
            InfoBar.warning(
                title=title,
                content=msg[:200] + ("…" if len(msg) > 200 else ""),
                isClosable=True,
                duration=6000,
                position=InfoBarPosition.TOP_RIGHT,
                parent=self,
            )

    def _set_all_checks(self, state: bool):
        self._sel_table.setUpdatesEnabled(False)
        try:
            for row in range(self._sel_table.rowCount()):
                item = self._sel_table.item(row, 0)
                if item:
                    item.setCheckState(Qt.Checked if state else Qt.Unchecked)
        finally:
            self._sel_table.setUpdatesEnabled(True)

    def _download_selected(self):
        s = load_settings()
        fmt = self._format_combo.currentText()
        out = s.get("download_path", str(get_default_downloads_dir()))
        cookies = s.get("cookies_file", "")
        jobs_and_entries: list[tuple[DownloadJob, dict]] = []
        for row in range(self._sel_table.rowCount()):
            chk = self._sel_table.item(row, 0)
            if chk and chk.checkState() == Qt.Checked and row < len(self._sel_entries):
                entry = self._sel_entries[row]
                url = entry.get("url", "")
                if url:
                    job = DownloadJob(url=url, output_dir=out, format_key=fmt,
                                      single_video=True, cookies_file=cookies)
                    jobs_and_entries.append((job, entry))
        if not jobs_and_entries:
            return
        for job, entry in jobs_and_entries:
            self._active_jobs.add(job.job_id)
        rows_data = [
            (j.job_id, entry.get("title", j.url), out, entry.get("url", ""))
            for j, entry in jobs_and_entries
        ]
        self._add_download_rows_batch(rows_data)
        for job, _ in jobs_and_entries:
            self._manager.enqueue(job)
        add_log_entry("info", f"Queued {len(jobs_and_entries)} selected item(s) for download.")
        if self._progress_indet is not None:
            self._progress_indet.setVisible(False)
        if self._progress is not None:
            self._progress.setVisible(False)
        if self._progress_pct_label is not None:
            self._progress_pct_label.setVisible(False)
        self._update_controls()

    def _start_download_from_playlist(self, url: str, out: str, fmt: str, cookies: str) -> None:
        """Phase 1: one extract job (fetch playlist/profile). Phase 2: N separate download jobs."""
        if self._direct_playlist_worker and self._direct_playlist_worker.isRunning():
            return
        self._direct_playlist_worker = PlaylistFetchWorker(url, cookies_file=cookies, parent=self)
        self._direct_playlist_worker.log_line.connect(self._log_append)
        self._direct_playlist_worker.entries_ready.connect(
            lambda entries: self._on_direct_playlist_entries(entries, out, fmt, cookies)
        )
        self._direct_playlist_worker.finished_signal.connect(self._on_direct_playlist_finished)
        self._set_profile_extract_controls(False)
        self._start_btn.setEnabled(False)
        self._log_append("[info] Phase 1: Extracting video list from profile/playlist…")
        self._direct_playlist_worker.start()

    def _on_direct_playlist_entries(
        self, entries: list, output_dir: str, format_key: str, cookies: str
    ) -> None:
        """Phase 2: enqueue one download job per entry; failed jobs are skipped and next continues."""
        jobs_and_entries: list[tuple[DownloadJob, dict]] = []
        for entry in entries:
            url = entry.get("url", "").strip()
            if not url:
                continue
            job = DownloadJob(
                url=url,
                output_dir=output_dir,
                format_key=format_key,
                single_video=True,
                cookies_file=cookies,
            )
            jobs_and_entries.append((job, entry))
        if not jobs_and_entries:
            self._log_append("No video URLs in playlist/profile.")
            return
        for job, _ in jobs_and_entries:
            self._active_jobs.add(job.job_id)
        rows_data = [
            (j.job_id, entry.get("title", j.url), output_dir, entry.get("url", ""))
            for j, entry in jobs_and_entries
        ]
        self._add_download_rows_batch(rows_data)
        for job, _ in jobs_and_entries:
            self._manager.enqueue(job)
        add_log_entry(
            "info",
            f"Phase 2: Queued {len(jobs_and_entries)} download(s); up to {self._manager.max_workers} in parallel. Errors skip to next.",
        )
        self._update_controls()

    def _on_direct_playlist_finished(self, success: bool, msg: str) -> None:
        self._direct_playlist_worker = None
        self._set_profile_extract_controls(True)
        if not success:
            self._log_append(msg)
            title = "Not supported" if "not supported" in msg.lower() else "Extract failed"
            InfoBar.warning(
                title=title,
                content=msg[:200] + ("…" if len(msg) > 200 else ""),
                isClosable=True,
                duration=6000,
                position=InfoBarPosition.TOP_RIGHT,
                parent=self,
            )
        self._update_controls()

    # ── Download table helpers ─────────────────────────────────────────────

    def _add_download_row(
        self, job_id: str, message: str, output_dir: str = "", url: str = "", scroll: bool = True
    ) -> None:
        """Add a row for a new download job with a progress bar. Path shows output_dir until finished."""
        row = self._process_table.rowCount()
        self._process_table.insertRow(row)
        time_str = datetime.now().strftime("%H:%M:%S")
        time_item = QTableWidgetItem(time_str)
        time_item.setData(Qt.UserRole, job_id)
        self._process_table.setItem(row, 0, time_item)
        platform = detect_platform(url) if url else "Unknown"
        host_item = QTableWidgetItem()
        host_item.setIcon(host_icon(platform))
        host_item.setToolTip(platform)
        self._process_table.setItem(row, 1, host_item)
        self._process_table.setItem(row, 2, QTableWidgetItem("Downloading"))
        self._process_table.setItem(row, 3, QTableWidgetItem(message[:200] or job_id[:200]))
        self._process_table.setItem(row, 4, QTableWidgetItem(output_dir or "—"))
        self._process_table.setItem(row, 5, QTableWidgetItem("—"))
        bar = ProgressBar(self._process_table)
        bar.setRange(0, 100)
        bar.setValue(0)
        bar.setFixedHeight(20)
        bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        bar.setMinimumWidth(80)
        self._process_table.setCellWidget(row, 6, bar)
        self._job_to_row[job_id] = row
        self._job_progress[job_id] = 0.0
        if scroll:
            self._process_table.scrollToBottom()

    def _add_download_rows_batch(
        self, rows_data: list[tuple[str, str, str, str]]
    ) -> None:
        """Add many download rows in one go without repainting each time. Each item: (job_id, message, output_dir, url)."""
        if not rows_data:
            return
        self._process_table.setUpdatesEnabled(False)
        try:
            for job_id, message, output_dir, url in rows_data:
                self._add_download_row(job_id, message, output_dir, url, scroll=False)
            self._process_table.scrollToBottom()
        finally:
            self._process_table.setUpdatesEnabled(True)

    def _clear_download_table(self) -> None:
        self._process_table.setRowCount(0)
        self._job_to_row.clear()

    def _on_process_table_context_menu(self, pos: QPoint) -> None:
        """Show right-click RoundMenu for the row: Copy path, Open folder, Cancel job, Remove row."""
        row = self._process_table.indexAt(pos).row()
        if row < 0:
            return
        item0 = self._process_table.item(row, 0)
        job_id = item0.data(Qt.UserRole) if item0 else None
        if not job_id:
            return
        path_item = self._process_table.item(row, 4)
        path = (path_item.text() or "").strip().replace("—", "").strip() or None
        is_active = job_id in self._active_jobs

        menu = RoundMenu(title="", parent=self)
        copy_act = Action(FluentIcon.COPY, "Copy path", triggered=lambda: self._copy_path_and_log(path))
        copy_act.setEnabled(bool(path))
        menu.addAction(copy_act)

        open_act = Action(FluentIcon.FOLDER, "Open folder", triggered=lambda: self._open_path_in_explorer(path))
        open_act.setEnabled(bool(path))
        menu.addAction(open_act)

        menu.addSeparator()

        cancel_act = Action(
            FluentIcon.CANCEL,
            "Cancel this job",
            triggered=lambda: self._cancel_job_and_log(job_id),
        )
        cancel_act.setEnabled(is_active)
        menu.addAction(cancel_act)

        remove_act = Action(
            FluentIcon.DELETE,
            "Remove row",
            triggered=lambda: self._remove_download_row(row, job_id),
        )
        menu.addAction(remove_act)

        menu.exec_(self._process_table.viewport().mapToGlobal(pos))

    def _copy_path_and_log(self, path: str) -> None:
        if path:
            QApplication.instance().clipboard().setText(path)
            add_log_entry("info", "Path copied to clipboard.")

    def _cancel_job_and_log(self, job_id: str) -> None:
        self._manager.cancel_job(job_id)
        add_log_entry("info", "Job cancelled.")

    def _open_path_in_explorer(self, path: str) -> None:
        """Open the path in the system file manager (folder or file's parent)."""
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
            add_log_entry("error", f"Could not open folder: {target}")

    def _remove_download_row(self, row: int, job_id: str) -> None:
        """Remove one row and update job maps; cancel job if running."""
        if job_id in self._active_jobs:
            self._manager.cancel_job(job_id)
        self._active_jobs.discard(job_id)
        self._job_progress.pop(job_id, None)
        self._process_table.removeRow(row)
        self._job_to_row.pop(job_id, None)
        for jid in list(self._job_to_row):
            if self._job_to_row[jid] > row:
                self._job_to_row[jid] -= 1
        self._update_controls()

    def _on_job_log(self, job_id: str, text: str) -> None:
        clean = strip_ansi(text.strip())
        if not clean:
            return
        tl = clean.lower()
        if tl.startswith("[error]") or "error:" in tl:
            status = "error"
        elif "[download]" in tl:
            status = "download"
        elif "[warning]" in tl:
            status = "warning"
        else:
            status = "info"
        add_log_entry(status, clean)
        if len(self._active_jobs) <= LOG_TABLE_UPDATE_MAX_JOBS:
            row = self._job_to_row.get(job_id)
            if row is not None and row < self._process_table.rowCount():
                msg_item = self._process_table.item(row, 3)
                if msg_item:
                    msg_item.setText(clean[:500] if len(clean) > 500 else clean)

    def _progress_col(self) -> int:
        return 6

    def _log_append(self, text: str) -> None:
        """Append a generic log line (e.g. from playlist preview); no job row."""
        clean = strip_ansi(text.strip())
        if not clean:
            return
        tl = clean.lower()
        if tl.startswith("[error]") or "error:" in tl:
            status = "error"
        elif "[download]" in tl:
            status = "download"
        elif "[warning]" in tl:
            status = "warning"
        else:
            status = "info"
        add_log_entry(status, clean)

    def _is_extracting(self) -> bool:
        """True while profile/playlist extract (one job) is running."""
        return (
            self._direct_playlist_worker is not None
            and self._direct_playlist_worker.isRunning()
        )

    def _set_profile_extract_controls(self, enabled: bool) -> None:
        """Enable/disable URL and mode controls during profile extract phase."""
        self._url_edit.setEnabled(enabled)
        self._mode_segmented.setEnabled(enabled)
        self._format_combo.setEnabled(enabled)

    def _update_controls(self):
        count = len(self._active_jobs)
        self._stop_btn.setEnabled(count > 0)
        self._jobs_label.setText(f"{count} active" if count else "")
        # Disable Download while extracting or while any download jobs are active
        self._start_btn.setEnabled(
            count == 0 and not self._is_extracting() and self._mode_segmented.currentRouteKey() != "enhance"
        )

    # ── Download control ──────────────────────────────────────────────────

    def _start_download(self):
        s = load_settings()
        fmt = self._format_combo.currentText()
        out = s.get("download_path", str(get_default_downloads_dir()))
        cookies = s.get("cookies_file", "")

        if self._mode_segmented.currentRouteKey() == "bulk":
            # Bulk mode: dedupe, cap size, batch-add rows then enqueue
            text = self._bulk_edit.toPlainText()
            raw = [ln.strip() for ln in text.splitlines() if ln.strip()]
            urls = list(dict.fromkeys(raw))  # preserve order, remove duplicates
            if not urls:
                self._log_append("Enter at least one URL in the bulk list.")
                return
            if len(urls) > MAX_BULK_URLS:
                self._log_append(
                    f"Bulk list capped at {MAX_BULK_URLS} URLs (had {len(urls)}). "
                    "Split into multiple runs for more."
                )
                urls = urls[:MAX_BULK_URLS]
            if len(raw) != len(urls):
                self._log_append(f"Removed {len(raw) - len(urls)} duplicate URL(s).")
            jobs_and_urls = [
                (DownloadJob(url=url, output_dir=out, format_key=fmt, single_video=True, cookies_file=cookies), url)
                for url in urls
            ]
            rows_data = [(j.job_id, url, out, url) for j, url in jobs_and_urls]
            for j, _ in jobs_and_urls:
                self._active_jobs.add(j.job_id)
            self._add_download_rows_batch(rows_data)
            for j, _ in jobs_and_urls:
                self._manager.enqueue(j)
        else:
            url = self._url_edit.text().strip()
            if not url:
                self._log_append("Enter a URL first.")
                return
            single_video = s.get("single_video_default", True)
            if not single_video and not (self._direct_playlist_worker and self._direct_playlist_worker.isRunning()):
                # Profile/playlist URL: fetch entries then enqueue one job per video (uses concurrent_downloads)
                self._start_download_from_playlist(url, out, fmt, cookies)
            else:
                job = DownloadJob(
                    url=url,
                    output_dir=out,
                    format_key=fmt,
                    single_video=single_video,
                    cookies_file=cookies,
                )
                self._active_jobs.add(job.job_id)
                self._add_download_row(job.job_id, url, out, url=job.url)
                self._manager.enqueue(job)

        if self._progress_indet is not None:
            self._progress_indet.setVisible(True)
        if self._progress is not None:
            self._progress.setVisible(False)
        if self._progress_pct_label is not None:
            self._progress_pct_label.setVisible(False)
        self._update_controls()

    def _update_header_progress(self) -> None:
        """Update header progress bar and percentage label from all active jobs (no-op if removed)."""
        if not self._job_progress or self._progress is None or self._progress_pct_label is None:
            return
        total = sum(self._job_progress.values())
        n = len(self._job_progress)
        pct = int((total / n) * 100) if n else 0
        self._progress.setRange(0, 100)
        self._progress.setValue(min(100, pct))
        self._progress_pct_label.setText(f"{pct}%")

    def _flush_progress_ui(self) -> None:
        """Apply stored progress to per-row bars only (top bar removed)."""
        self._progress_flush_pending = False
        if self._progress_indet is not None:
            self._progress_indet.setVisible(False)
        if self._progress is not None:
            self._progress.setVisible(True)
        if self._progress_pct_label is not None:
            self._progress_pct_label.setVisible(True)
        self._update_header_progress()
        for job_id, row in list(self._job_to_row.items()):
            if row < self._process_table.rowCount():
                value = self._job_progress.get(job_id, 0.0)
                bar = self._process_table.cellWidget(row, self._progress_col())
                if isinstance(bar, ProgressBar):
                    bar.setRange(0, 100)
                    bar.setValue(int(max(0.0, min(1.0, value)) * 100))

    def _on_progress(self, job_id: str, value: float) -> None:
        """Store progress and schedule a single UI update to avoid flooding."""
        self._job_progress[job_id] = max(0.0, min(1.0, value)) if value >= 0 else 0.0
        if not self._progress_flush_pending:
            self._progress_flush_pending = True
            QTimer.singleShot(PROGRESS_THROTTLE_MS, self._flush_progress_ui)

    def _stop_all(self):
        self._manager.cancel_all()
        self._log_append("Cancelling all active downloads…")

    def _on_job_finished(
        self, job_id: str, success: bool, message: str, filepath: str, size_bytes: int
    ) -> None:
        self._active_jobs.discard(job_id)
        self._job_progress.pop(job_id, None)
        add_log_entry("info" if success else "error", message)
        if not success:
            add_log_entry("info", "Skipped (error), continuing with next job.")
            title = "Not supported" if "not supported" in message.lower() else "Download failed"
            InfoBar.error(
                title=title,
                content=message[:200] + ("…" if len(message) > 200 else ""),
                isClosable=True,
                duration=6000,
                position=InfoBarPosition.TOP_RIGHT,
                parent=self,
            )
        row = self._job_to_row.get(job_id)
        if row is not None and row < self._process_table.rowCount():
            status_item = self._process_table.item(row, 2)
            if status_item:
                status_item.setText("Done" if success else "Skipped")
            msg_item = self._process_table.item(row, 3)
            if msg_item:
                msg_item.setText(message[:500] if len(message) > 500 else message)
            path_item = self._process_table.item(row, 4)
            if path_item and filepath:
                path_item.setText(filepath)
            size_item = self._process_table.item(row, 5)
            if size_item:
                size_item.setText(format_size(size_bytes))
            bar = self._process_table.cellWidget(row, self._progress_col())
            if isinstance(bar, ProgressBar):
                if success:
                    bar.setVisible(False)
                else:
                    bar.setRange(0, 100)
                    bar.setValue(0)
        if not self._active_jobs:
            if self._progress_indet is not None:
                self._progress_indet.setVisible(False)
            if self._progress is not None:
                self._progress.setVisible(False)
            if self._progress_pct_label is not None:
                self._progress_pct_label.setVisible(False)
        else:
            self._update_header_progress()
        self._update_controls()
