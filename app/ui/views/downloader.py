"""Downloader view: single, bulk, and selective download with HD/4K/Photo formats."""

import re
from datetime import datetime

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    BodyLabel,
    CardWidget,
    ComboBox,
    FluentIcon,
    IndeterminateProgressBar,
    LineEdit,
    PlainTextEdit,
    ProgressBar,
    PrimaryPushButton,
    PushButton,
    StrongBodyLabel,
    SubtitleLabel,
    SwitchButton,
    TableWidget,
    TransparentPushButton,
)

from app.common.paths import DOWNLOADS_DIR
from app.common.state import add_log_entry
from app.config import load_settings
from app.core.download import SUPPORTED_DOMAINS
from app.core.manager import DownloadJob, DownloadManager
from app.core.scraper import PlaylistFetchWorker, fmt_duration, fmt_date
from app.ui.components import CardHeader, StatusTable

from .base import BaseView

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

_PLATFORM_CHIPS = [
    ("YouTube",    "https://youtube.com/"),
    ("TikTok",     "https://tiktok.com/"),
    ("Douyin",     "https://www.douyin.com/video/"),
    ("Kuaishou",   "https://www.kuaishou.com/"),
    ("Instagram",  "https://instagram.com/"),
    ("Facebook",   "https://facebook.com/"),
    ("Pinterest",  "https://pinterest.com/"),
    ("Twitter/X",  "https://x.com/"),
    ("ok.ru",      "https://ok.ru/video/"),
    ("VK",         "https://vk.com/video/"),
    ("Twitch",     "https://twitch.tv/"),
    ("Vimeo",      "https://vimeo.com/"),
]

_FORMATS = [
    "Best (video+audio)",
    "HD 1080p",
    "HD 720p",
    "4K / 2160p",
    "Best video",
    "Best audio",
    "Video (mp4)",
    "Audio (mp3)",
    "Photo / Image",
]


def _strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text)


class DownloaderView(BaseView):
    """Multi-job downloader: single URL, bulk URL list, and selective playlist download."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Downloader")

        self._manager = DownloadManager(parent=self)
        self._manager.log_line.connect(lambda _jid, msg: self._log_append(msg))
        self._manager.progress.connect(self._on_progress)
        self._manager.job_finished.connect(self._on_job_finished)
        self._active_jobs: set[str] = set()
        self._playlist_worker: PlaylistFetchWorker | None = None

        self._build_url_card()
        self._build_bulk_card()
        self._build_selective_card()
        self._build_format_card()
        self._build_progress()
        self._build_log_card()

        self._layout.addStretch(1)

        # Start with bulk / selective hidden
        self._bulk_card.setVisible(False)
        self._selective_card.setVisible(False)

    # ── Card builders ─────────────────────────────────────────────────────

    def _build_url_card(self):
        card = CardWidget(self)
        lay = QVBoxLayout(card)
        lay.setSpacing(10)
        lay.addWidget(CardHeader(FluentIcon.LINK, "Video URL & output", card))

        url_row = QHBoxLayout()
        url_row.addWidget(BodyLabel("URL", card))
        self._url_edit = LineEdit(card)
        self._url_edit.setPlaceholderText(
            "https://  —  YouTube, TikTok, Douyin, Kuaishou, Instagram, Facebook, Pinterest, Twitter/X …"
        )
        self._url_edit.setClearButtonEnabled(True)
        url_row.addWidget(self._url_edit, 1)
        lay.addLayout(url_row)

        chips_row = QHBoxLayout()
        chips_row.setSpacing(4)
        chips_row.addWidget(BodyLabel("Platforms:", card))
        for label, hint_url in _PLATFORM_CHIPS:
            btn = TransparentPushButton(label, card)
            btn.setFixedHeight(24)
            btn.clicked.connect(lambda _=False, u=hint_url: self._url_edit.setPlaceholderText(u))
            chips_row.addWidget(btn)
        chips_row.addStretch(1)
        lay.addLayout(chips_row)

        path_row = QHBoxLayout()
        path_row.addWidget(BodyLabel("Output folder", card))
        self._path_edit = LineEdit(card)
        self._path_edit.setPlaceholderText(str(DOWNLOADS_DIR))
        self._path_edit.setText(load_settings().get("download_path", str(DOWNLOADS_DIR)))
        browse_btn = PushButton("Browse…", card)
        browse_btn.clicked.connect(self._browse_output)
        path_row.addWidget(self._path_edit, 1)
        path_row.addWidget(browse_btn)
        lay.addLayout(path_row)

        mode_row = QHBoxLayout()
        mode_row.addWidget(BodyLabel("Single video only (no playlist)", card))
        self._single_switch = SwitchButton(card)
        self._single_switch.setChecked(load_settings().get("single_video_default", True))
        mode_row.addStretch(1)
        mode_row.addWidget(self._single_switch)
        lay.addLayout(mode_row)

        bulk_row = QHBoxLayout()
        bulk_row.addWidget(BodyLabel("Bulk mode (multiple URLs)", card))
        self._bulk_switch = SwitchButton(card)
        self._bulk_switch.setChecked(False)
        self._bulk_switch.checkedChanged.connect(self._on_bulk_toggled)
        bulk_row.addStretch(1)
        bulk_row.addWidget(self._bulk_switch)
        lay.addLayout(bulk_row)

        sel_row = QHBoxLayout()
        sel_row.addWidget(BodyLabel("Selective download (preview playlist)", card))
        self._selective_switch = SwitchButton(card)
        self._selective_switch.setChecked(False)
        self._selective_switch.checkedChanged.connect(self._on_selective_toggled)
        sel_row.addStretch(1)
        sel_row.addWidget(self._selective_switch)
        lay.addLayout(sel_row)

        self._layout.addWidget(card)

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
        self._format_combo.addItems(_FORMATS)
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
        self._progress_indet = IndeterminateProgressBar(self)
        self._progress_indet.setVisible(False)
        self._layout.addWidget(self._progress_indet)

        self._progress = ProgressBar(self)
        self._progress.setVisible(False)
        self._layout.addWidget(self._progress)

    def _build_log_card(self):
        card = CardWidget(self)
        lay = QVBoxLayout(card)
        lay.setSpacing(10)

        hdr = QHBoxLayout()
        hdr.addWidget(CardHeader(FluentIcon.HISTORY, "Download log", card))
        clear_btn = PushButton("Clear", card)
        clear_btn.setIcon(FluentIcon.DELETE)
        clear_btn.clicked.connect(lambda: self._process_table.setRowCount(0))
        hdr.addWidget(clear_btn)
        lay.addLayout(hdr)

        self._process_table = StatusTable(card)
        self._process_table.setMinimumHeight(220)
        lay.addWidget(self._process_table)
        self._layout.addWidget(card)

    # ── Mode toggles ──────────────────────────────────────────────────────

    def _on_bulk_toggled(self, checked: bool):
        self._bulk_card.setVisible(checked)
        if checked:
            self._selective_switch.setChecked(False)

    def _on_selective_toggled(self, checked: bool):
        self._selective_card.setVisible(checked)
        if checked:
            self._bulk_switch.setChecked(False)

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
        self._preview_progress.setVisible(True)
        self._preview_btn.setEnabled(False)
        self._sel_status.setText("Fetching playlist…")
        self._playlist_worker.start()

    def _on_entries_ready(self, entries: list):
        self._sel_entries = entries
        self._sel_table.setRowCount(0)
        for entry in entries:
            row = self._sel_table.rowCount()
            self._sel_table.insertRow(row)
            chk = QTableWidgetItem()
            chk.setCheckState(Qt.Checked)
            self._sel_table.setItem(row, 0, chk)
            self._sel_table.setItem(row, 1, QTableWidgetItem(entry.get("title", "")))
            self._sel_table.setItem(row, 2, QTableWidgetItem(entry.get("uploader", "")))
            self._sel_table.setItem(row, 3, QTableWidgetItem(fmt_duration(entry.get("duration"))))
            self._sel_table.setItem(row, 4, QTableWidgetItem(fmt_date(entry.get("upload_date", ""))))
        self._dl_selected_btn.setEnabled(bool(entries))

    def _on_preview_done(self, success: bool, msg: str):
        self._preview_progress.setVisible(False)
        self._preview_btn.setEnabled(True)
        self._sel_status.setText(msg)

    def _set_all_checks(self, state: bool):
        for row in range(self._sel_table.rowCount()):
            item = self._sel_table.item(row, 0)
            if item:
                item.setCheckState(Qt.Checked if state else Qt.Unchecked)

    def _download_selected(self):
        s = load_settings()
        fmt = self._format_combo.currentText()
        out = self._path_edit.text().strip() or str(DOWNLOADS_DIR)
        cookies = s.get("cookies_file", "")
        queued = 0
        for row in range(self._sel_table.rowCount()):
            chk = self._sel_table.item(row, 0)
            if chk and chk.checkState() == Qt.Checked and row < len(self._sel_entries):
                entry = self._sel_entries[row]
                url = entry.get("url", "")
                if url:
                    job = DownloadJob(url=url, output_dir=out, format_key=fmt,
                                      single_video=True, cookies_file=cookies)
                    self._active_jobs.add(job.job_id)
                    self._manager.enqueue(job)
                    queued += 1
        if queued:
            self._log_append(f"Queued {queued} selected item(s) for download.")
            self._progress_indet.setVisible(True)
            self._progress.setVisible(False)
            self._update_controls()

    # ── Helpers ───────────────────────────────────────────────────────────

    def _browse_output(self):
        path = QFileDialog.getExistingDirectory(self, "Output folder", self._path_edit.text())
        if path:
            self._path_edit.setText(path)

    def _log_append(self, text: str):
        clean = _strip_ansi(text.strip())
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
        time_str = datetime.now().strftime("%H:%M:%S")
        self._process_table.append_row(time_str, status, clean)
        add_log_entry(status, clean)

    def _update_controls(self):
        count = len(self._active_jobs)
        self._stop_btn.setEnabled(count > 0)
        self._jobs_label.setText(f"{count} active" if count else "")

    # ── Download control ──────────────────────────────────────────────────

    def _start_download(self):
        s = load_settings()
        fmt = self._format_combo.currentText()
        out = self._path_edit.text().strip() or str(DOWNLOADS_DIR)
        cookies = s.get("cookies_file", "")

        if self._bulk_switch.isChecked():
            # Bulk mode: queue every non-empty line
            text = self._bulk_edit.toPlainText()
            urls = [ln.strip() for ln in text.splitlines() if ln.strip()]
            if not urls:
                self._log_append("Enter at least one URL in the bulk list.")
                return
            for url in urls:
                job = DownloadJob(url=url, output_dir=out, format_key=fmt,
                                  single_video=True, cookies_file=cookies)
                self._active_jobs.add(job.job_id)
                self._log_append(f"Queued: {url}")
                self._manager.enqueue(job)
        else:
            url = self._url_edit.text().strip()
            if not url:
                self._log_append("Enter a URL first.")
                return
            job = DownloadJob(
                url=url,
                output_dir=out,
                format_key=fmt,
                single_video=self._single_switch.isChecked(),
                cookies_file=cookies,
            )
            self._active_jobs.add(job.job_id)
            self._log_append(f"Queued: {url}")
            self._manager.enqueue(job)

        self._progress_indet.setVisible(True)
        self._progress.setVisible(False)
        self._update_controls()

    def _on_progress(self, job_id: str, value: float):
        self._progress_indet.setVisible(False)
        self._progress.setVisible(True)
        if value < 0:
            self._progress.setRange(0, 0)
        else:
            self._progress.setRange(0, 100)
            self._progress.setValue(int(value * 100))

    def _stop_all(self):
        self._manager.cancel_all()
        self._log_append("Cancelling all active downloads…")

    def _on_job_finished(self, job_id: str, success: bool, message: str):
        self._active_jobs.discard(job_id)
        self._log_append(message)
        if not self._active_jobs:
            self._progress_indet.setVisible(False)
            self._progress.setVisible(False)
        self._update_controls()
