import os
import re
import shutil
import subprocess
import sys
from datetime import datetime

from PyQt5.QtCore import Qt, QPoint, QTimer
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QSizePolicy,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    Action,
    BodyLabel,
    CardWidget,
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
    ScrollArea,
    StateToolTip,
    SwitchButton,
    SegmentedWidget,
    TableWidget,
)

from app.common.paths import get_default_downloads_dir
from app.common.signal_bus import signal_bus
from app.common.sound import play_download_sound
from app.common.state import add_log_entry
from app.config import load_settings
from app.core.download import detect_platform
from app.common.concurrent import EnhancePostProcessWorker, PlaylistFetchWorker
from app.core.ffmpeg.manager import ffmpeg_available
from app.core.manager import DownloadJob, DownloadManager
from app.core.scraper import fmt_duration, fmt_date
from app.ui.components import (
    CardHeader,
    DownloadConfigCard,
    DownloadEnhanceFeature,
    DownloadPathPanel,
    DownloadTableCard,
    EnhanceOptions,
)
from app.ui.helpers import DOWNLOAD_FORMATS, host_icon
from app.ui.utils import format_size, strip_ansi

from .base import BaseView

# Limits to avoid UI freeze and crashes with huge lists
MAX_BULK_URLS = 2000
MAX_PLAYLIST_DISPLAY = 1500
PROGRESS_THROTTLE_MS = 120
# Skip per-row log text updates when job count exceeds this (avoids UI flood)
LOG_TABLE_UPDATE_MAX_JOBS = 80

def _sanitize_folder_name(name: str) -> str:
    """Replace path-unsafe chars so the name can be used as a folder name."""
    s = re.sub(r'[<>:"/\\|?*]', "_", name)
    return s.strip(". ") or "video"


URL_PLACEHOLDER_SINGLE = (
    "https://  —  YouTube, TikTok, Douyin, Kuaishou, Instagram, Facebook, Pinterest, Twitter/X …"
)
URL_PLACEHOLDER_SELECTIVE = (
    "https://  —  Playlist or channel URL (preview to select which videos to download) …"
)


class DownloaderView(QFrame):
    """Multi-job downloader: single URL, bulk URL list, and selective playlist download."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DownloaderView")
        self.setFrameShape(QFrame.NoFrame)

        # ── Outer layout: scroll area + fixed footer ──────────────────────
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._scroll = ScrollArea(self)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._container = QWidget()
        self._container.setObjectName("DownloaderViewContainer")
        self._layout = QVBoxLayout(self._container)
        self._layout.setContentsMargins(24, 24, 24, 24)
        self._layout.setSpacing(16)
        self._scroll.setWidget(self._container)
        self._scroll.setStyleSheet(
            "QScrollArea, QWidget#DownloaderViewContainer"
            " { background: transparent; border: none; }"
        )
        outer.addWidget(self._scroll, 1)

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
        self._state_tooltip: StateToolTip | None = None
        self._tooltip_total: int = 0
        self._tooltip_done: int = 0
        self._enhance_job_options: dict[str, EnhanceOptions] = {}  # job_id -> options for post-process
        self._enhance_worker: EnhancePostProcessWorker | None = None
        self._enhance_job_id: str = ""  # job_id of the row we're enhancing (for row update on done)
        self._enhance_original_to_delete: dict[str, str] = {}  # job_id -> path to delete when not keep_original

        self._build_mode_bar()
        self._build_url_card()
        self._build_bulk_card()
        self._build_selective_card()
        self._build_enhance_card()
        # self._build_path_panel()
        self._build_download_config_card()
        self._build_progress()
        self._build_log_card()

        self._layout.addStretch(1)

        self._build_footer_bar(outer)

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
        lay.addWidget(CardHeader(FluentIcon.LINK, "Video & Profile URL", self._url_card))

        url_row = QHBoxLayout()
        url_row.addWidget(BodyLabel("URL", self._url_card))
        self._url_edit = LineEdit(self._url_card)
        self._url_edit.setPlaceholderText(URL_PLACEHOLDER_SINGLE)
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
        """Enhance mode: download with stream edit (logo, flip, color, speed)."""
        self._enhance_card = DownloadEnhanceFeature(self)
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

    def _build_download_config_card(self):
        self._dl_config_card = DownloadConfigCard(self)
        self._layout.addWidget(self._dl_config_card)

    def _build_footer_bar(self, outer_layout: QVBoxLayout) -> None:
        """Fixed footer bar with jobs count, Download and Stop all — always visible."""
        footer = QWidget(self)
        footer.setObjectName("FooterBar")
        footer.setFixedHeight(56)
        footer.setStyleSheet(
            "QWidget#FooterBar { border-top: 1px solid rgba(128,128,128,0.2); }"
        )
        row = QHBoxLayout(footer)
        row.setContentsMargins(24, 0, 24, 0)
        row.setSpacing(10)

        self._jobs_label = BodyLabel("", footer)
        row.addStretch(1)
        row.addWidget(self._jobs_label)

        self._start_btn = PrimaryPushButton("Download", footer)
        self._start_btn.setIcon(FluentIcon.DOWNLOAD)
        self._start_btn.setFixedHeight(36)
        self._start_btn.clicked.connect(self._start_download)

        self._stop_btn = PushButton("Stop all", footer)
        self._stop_btn.setIcon(FluentIcon.CANCEL)
        self._stop_btn.setFixedHeight(36)
        self._stop_btn.clicked.connect(self._stop_all)
        self._stop_btn.setEnabled(False)

        row.addWidget(self._start_btn)
        row.addWidget(self._stop_btn)
        outer_layout.addWidget(footer)

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
        """Refresh path panel and download config path when view is shown (e.g. after returning from Settings)."""
        super().showEvent(event)
        if hasattr(self, "_path_panel"):
            self._path_panel.refresh_path()
        if hasattr(self, "_dl_config_card"):
            self._dl_config_card._refresh_path_display()
            self._dl_config_card._refresh_performance_display()

    # ── Mode switch (segmented) ──────────────────────────────────────────

    def _on_download_mode_changed(self):
        key = self._mode_segmented.currentRouteKey()
        is_enhance = key == "enhance"
        # Hide URL card in Bulk (paste URLs in bulk list) and in Enhance (URL is inside enhance card)
        self._url_card.setVisible(not is_enhance and key != "bulk")
        self._bulk_card.setVisible(key == "bulk")
        self._selective_card.setVisible(key == "selective")
        self._enhance_card.setVisible(is_enhance)
        # Update URL placeholder: Selective mode = playlist/channel hint
        if key == "selective":
            self._url_edit.setPlaceholderText(URL_PLACEHOLDER_SELECTIVE)
        else:
            self._url_edit.setPlaceholderText(URL_PLACEHOLDER_SINGLE)

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
        self._show_state_tooltip("Playlist preview", "Fetching entries…")
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
        self._close_state_tooltip()
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
        self._manager.set_max_workers(self._dl_config_card.concurrent_downloads())
        self._manager.set_concurrent_fragments(self._dl_config_card.concurrent_fragments())
        s = load_settings()
        fmt = self._dl_config_card.format_combo.currentText()
        out = self._output_dir()
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
        self._tooltip_total += len(jobs_and_entries)
        self._tooltip_done = 0
        self._show_state_tooltip(
            "Downloading selected",
            f"0 / {len(jobs_and_entries)} complete",
        )
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
        self._show_state_tooltip("Extracting playlist", "Fetching video list…")
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
        self._tooltip_total += len(jobs_and_entries)
        self._tooltip_done = 0
        self._update_state_tooltip(
            f"Downloading {len(jobs_and_entries)} video(s)…"
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
        signal_bus.download_started.emit(job_id, url or message, output_dir or "")
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
        self._dl_config_card.setEnabled(enabled)

    # ── StateToolTip helpers ──────────────────────────────────────────────

    def _show_state_tooltip(self, title: str, content: str) -> None:
        """Create and show a new StateToolTip, dismissing any existing one."""
        self._close_state_tooltip()
        win = self.window()
        self._state_tooltip = StateToolTip(title, content, win)
        self._state_tooltip.move(win.width() - 300, 45)
        self._state_tooltip.show()

    def _update_state_tooltip(self, content: str) -> None:
        """Update the content of the current StateToolTip if visible."""
        if self._state_tooltip is not None:
            try:
                self._state_tooltip.setContent(content)
            except RuntimeError:
                self._state_tooltip = None

    def _close_state_tooltip(self) -> None:
        """Mark the StateToolTip as done (check-mark) and release reference."""
        if self._state_tooltip is not None:
            try:
                self._state_tooltip.setState(True)
            except RuntimeError:
                pass
            self._state_tooltip = None

    def _update_controls(self):
        count = len(self._active_jobs)
        self._stop_btn.setEnabled(count > 0)
        self._jobs_label.setText(f"{count} active" if count else "")
        # Disable Download while extracting or while any download jobs are active (enhance mode allowed)
        self._start_btn.setEnabled(count == 0 and not self._is_extracting())

    # ── Download control ──────────────────────────────────────────────────

    def _output_dir(self) -> str:
        """Output folder: card override if set, else default from Settings."""
        override = self._dl_config_card.output_dir()
        if override:
            return override
        s = load_settings()
        return s.get("download_path", str(get_default_downloads_dir()))

    def _start_download(self):
        self._manager.set_max_workers(self._dl_config_card.concurrent_downloads())
        self._manager.set_concurrent_fragments(self._dl_config_card.concurrent_fragments())
        s = load_settings()
        fmt = self._dl_config_card.format_combo.currentText()
        out = self._output_dir()
        cookies = s.get("cookies_file", "")

        if self._mode_segmented.currentRouteKey() == "enhance":
            url = self._enhance_card.url()
            if not url:
                self._log_append("Enter a URL in the Enhance card first.")
                return
            opts = self._enhance_card.get_options()
            if not opts.has_edits():
                self._log_append("Enable at least one edit (logo, flip, color, or speed) for Enhance mode.")
                return
            if not ffmpeg_available():
                InfoBar.warning(
                    title="Enhance",
                    content="ffmpeg is not installed. Install ffmpeg to use stream edit.",
                    isClosable=True,
                    duration=5000,
                    position=InfoBarPosition.TOP_RIGHT,
                    parent=self,
                )
                return
            job = DownloadJob(
                url=url,
                output_dir=out,
                format_key=fmt,
                single_video=True,
                cookies_file=cookies,
            )
            self._enhance_job_options[job.job_id] = opts
            self._active_jobs.add(job.job_id)
            self._add_download_row(job.job_id, url, out, url=job.url)
            self._manager.enqueue(job)
            self._tooltip_total = 1
            self._tooltip_done = 0
            self._show_state_tooltip("Enhance download", "Downloading, then applying edits…")
        elif self._mode_segmented.currentRouteKey() == "bulk":
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
            self._tooltip_total = len(jobs_and_urls)
            self._tooltip_done = 0
            self._show_state_tooltip(
                "Bulk download",
                f"0 / {len(jobs_and_urls)} complete",
            )
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
                self._tooltip_total = 1
                self._tooltip_done = 0
                self._show_state_tooltip("Downloading", "Starting download…")

        if self._progress_indet is not None:
            self._progress_indet.setVisible(True)
        if self._progress is not None:
            self._progress.setVisible(False)
        if self._progress_pct_label is not None:
            self._progress_pct_label.setVisible(False)

        if s.get("auto_reset_link_before_download", True):
            mode = self._mode_segmented.currentRouteKey()
            if mode == "bulk":
                self._bulk_edit.clear()
            elif mode == "enhance":
                self._enhance_card.set_url("")
            else:
                self._url_edit.clear()

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
        signal_bus.download_progress.emit(job_id, self._job_progress[job_id])
        if not self._progress_flush_pending:
            self._progress_flush_pending = True
            QTimer.singleShot(PROGRESS_THROTTLE_MS, self._flush_progress_ui)

    def _stop_all(self):
        self._manager.cancel_all()
        self._log_append("Cancelling all active downloads…")
        self._update_state_tooltip("Cancelled.")
        self._close_state_tooltip()

    def _on_enhance_finished(
        self, success: bool, message: str, output_path: str, size_bytes: int
    ) -> None:
        job_id = self._enhance_job_id
        self._enhance_worker = None
        self._enhance_job_id = ""
        to_delete = self._enhance_original_to_delete.pop(job_id, "")
        signal_bus.enhance_finished.emit(
            job_id, success,
            os.path.basename(to_delete or output_path),
            output_path, size_bytes
        )
        if success and to_delete and os.path.isfile(to_delete):
            try:
                os.remove(to_delete)
                add_log_entry("info", "Original file removed (Keep original was off).")
            except OSError:
                add_log_entry("warning", "Could not remove original file.")
        self._tooltip_done += 1
        add_log_entry("info" if success else "error", message)
        s = load_settings()
        if success and s.get("sound_alert_on_complete", True):
            play_download_sound(success=True)
        elif not success and s.get("sound_alert_on_error", True):
            play_download_sound(success=False)
        if not success:
            InfoBar.error(
                title="Enhance failed",
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
            if path_item and output_path:
                path_item.setText(output_path)
            size_item = self._process_table.item(row, 5)
            if size_item:
                size_item.setText(format_size(size_bytes) if size_bytes >= 0 else "—")
            bar = self._process_table.cellWidget(row, self._progress_col())
            if isinstance(bar, ProgressBar):
                bar.setVisible(False)
        if not self._active_jobs:
            self._update_state_tooltip(
                f"{self._tooltip_done} / {self._tooltip_total} complete"
            )
            self._close_state_tooltip()
            self._tooltip_total = 0
            self._tooltip_done = 0
        else:
            self._update_state_tooltip(
                f"{self._tooltip_done} / {self._tooltip_total} complete"
            )
        self._update_controls()

    def _on_job_finished(
        self, job_id: str, success: bool, message: str, filepath: str, size_bytes: int
    ) -> None:
        self._active_jobs.discard(job_id)
        self._job_progress.pop(job_id, None)
        opts = self._enhance_job_options.pop(job_id, None)
        if opts and success and filepath and opts.has_edits() and ffmpeg_available():
            if not os.path.isfile(filepath):
                # Final path was a merged file — try to find it by stripping fragment suffix
                import re as _re
                candidate = _re.sub(r'\.f\d+\.[a-z0-9]+$', '', filepath, flags=_re.IGNORECASE)
                if os.path.isfile(candidate):
                    filepath = candidate
                else:
                    self._tooltip_done += 1
                    add_log_entry("warning", f"Enhance skipped: output file not found ({filepath})")
                    return
            base, ext = os.path.splitext(filepath)
            # Always encode enhanced output to mp4 — libx264 is incompatible with
            # webm/flv/ts containers that yt-dlp may produce.
            ext = ".mp4"
            if opts.keep_original:
                dirname = os.path.dirname(filepath)
                base_name = os.path.basename(filepath)
                name_no_ext = os.path.splitext(base_name)[0]
                folder = os.path.join(dirname, _sanitize_folder_name(name_no_ext))
                os.makedirs(folder, exist_ok=True)
                new_input = os.path.join(folder, base_name)
                shutil.move(filepath, new_input)
                filepath = new_input
                out_path = os.path.join(folder, f"{name_no_ext}_enhanced{ext}")
                self._enhance_original_to_delete[job_id] = ""
            else:
                out_path = f"{base}_enhanced{ext}"
                self._enhance_original_to_delete[job_id] = filepath
            self._enhance_job_id = job_id
            self._enhance_worker = EnhancePostProcessWorker(
                filepath, out_path, opts, job_id=job_id, parent=self
            )
            self._enhance_worker.log_line.connect(
                lambda t, jid=job_id: self._on_job_log(jid, t)
            )
            self._enhance_worker.finished_signal.connect(self._on_enhance_finished)
            self._enhance_worker.start()
            signal_bus.enhance_started.emit(job_id, os.path.basename(filepath))
            row = self._job_to_row.get(job_id)
            if row is not None and row < self._process_table.rowCount():
                status_item = self._process_table.item(row, 2)
                if status_item:
                    status_item.setText("Enhancing...")
            self._update_controls()
            return
        signal_bus.download_finished.emit(job_id, success, message, filepath, size_bytes)
        self._tooltip_done += 1
        add_log_entry("info" if success else "error", message)
        s = load_settings()
        if success and s.get("sound_alert_on_complete", True):
            play_download_sound(success=True)
        elif not success and s.get("sound_alert_on_error", True):
            play_download_sound(success=False)
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
            self._update_state_tooltip(
                f"{self._tooltip_done} / {self._tooltip_total} complete"
            )
            self._close_state_tooltip()
            self._tooltip_total = 0
            self._tooltip_done = 0
        else:
            self._update_state_tooltip(
                f"{self._tooltip_done} / {self._tooltip_total} complete"
            )
            self._update_header_progress()
        self._update_controls()
