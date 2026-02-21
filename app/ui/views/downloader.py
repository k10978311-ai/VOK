"""Downloader view: full UI for video/download with yt-dlp."""

import os

from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtWidgets import QFileDialog, QGridLayout, QGroupBox, QHBoxLayout, QVBoxLayout
from qfluentwidgets import (
    BodyLabel,
    ComboBox,
    LineEdit,
    PlainTextEdit,
    PrimaryPushButton,
    ProgressBar,
    PushButton,
    SubtitleLabel,
)

from app.common.paths import DOWNLOADS_DIR

from .base import BaseView


class DownloadWorker(QThread):
    """Runs yt-dlp in a thread and emits log lines and progress."""
    log_line = pyqtSignal(str)
    progress = pyqtSignal(float)  # 0.0..1.0 or -1 for indeterminate
    finished_signal = pyqtSignal(bool, str)  # success, message

    def __init__(self, url: str, output_dir: str, format_key: str, parent=None):
        super().__init__(parent)
        self.url = url.strip()
        self.output_dir = output_dir or str(DOWNLOADS_DIR)
        self.format_key = format_key
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        if not self.url:
            self.finished_signal.emit(False, "No URL provided.")
            return
        try:
            import yt_dlp
        except ImportError:
            self.finished_signal.emit(False, "yt-dlp not installed.")
            return

        os.makedirs(self.output_dir, exist_ok=True)
        out_tmpl = os.path.join(self.output_dir, "%(title)s.%(ext)s")

        format_map = {
            "Best (video+audio)": "best",
            "Best video": "bestvideo",
            "Best audio": "bestaudio",
            "Video (mp4)": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "Audio (mp3)": "bestaudio[ext=m4a]/bestaudio/best",
        }
        fkey = format_map.get(self.format_key, "best")

        def progress_hook(d):
            if self._cancelled:
                raise yt_dlp.utils.DownloadCancelled()
            if d.get("status") == "downloading" and "total_bytes" in d:
                total = d.get("total_bytes") or 1
                done = d.get("downloaded_bytes", 0)
                self.progress.emit(done / total if total else 0.0)
            elif d.get("status") == "finished":
                self.progress.emit(1.0)

        class LogLogger:
            def __init__(self, emit):
                self.emit = emit

            def debug(self, msg):
                if msg.startswith("[download]"):
                    self.emit(msg)

            def info(self, msg):
                self.emit(msg)

            def warning(self, msg):
                self.emit(msg)

            def error(self, msg):
                self.emit(msg)

        def log_emit(msg):
            self.log_line.emit(msg)

        opts = {
            "outtmpl": out_tmpl,
            "format": fkey,
            "progress_hooks": [progress_hook],
            "logger": LogLogger(log_emit),
            "noprogress": False,
        }

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([self.url])
            if self._cancelled:
                self.finished_signal.emit(False, "Cancelled.")
            else:
                self.finished_signal.emit(True, "Download completed.")
        except yt_dlp.utils.DownloadCancelled:
            self.finished_signal.emit(False, "Cancelled.")
        except Exception as e:
            self.log_line.emit(str(e))
            self.finished_signal.emit(False, str(e))


class DownloaderView(BaseView):
    """Full download tools: URL, path, format, start/stop, progress, log."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Downloader")
        self._worker: DownloadWorker | None = None

        # Card: URL & path
        card_input = QGroupBox("Video URL & output")
        layout_input = QGridLayout(card_input)
        self._url_edit = LineEdit(self)
        self._url_edit.setPlaceholderText("https://...")
        self._url_edit.setClearButtonEnabled(True)
        self._path_edit = LineEdit(self)
        self._path_edit.setPlaceholderText(str(DOWNLOADS_DIR))
        self._path_edit.setText(str(DOWNLOADS_DIR))
        browse_btn = PushButton("Browse...")
        browse_btn.clicked.connect(self._browse_output)
        layout_input.addWidget(BodyLabel("URL"), 0, 0)
        layout_input.addWidget(self._url_edit, 0, 1, 1, 2)
        layout_input.addWidget(BodyLabel("Output folder"), 1, 0)
        layout_input.addWidget(self._path_edit, 1, 1)
        layout_input.addWidget(browse_btn, 1, 2)
        self._layout.addWidget(card_input)

        # Card: Format & actions
        card_format = QGroupBox("Format & actions")
        layout_fmt = QHBoxLayout(card_format)
        self._format_combo = ComboBox(self)
        self._format_combo.addItems([
            "Best (video+audio)",
            "Best video",
            "Best audio",
            "Video (mp4)",
            "Audio (mp3)",
        ])
        layout_fmt.addWidget(SubtitleLabel("Format"))
        layout_fmt.addWidget(self._format_combo)
        layout_fmt.addStretch(1)
        self._start_btn = PrimaryPushButton("Start download")
        self._start_btn.clicked.connect(self._start_download)
        self._stop_btn = PushButton("Stop")
        self._stop_btn.clicked.connect(self._stop_download)
        self._stop_btn.setEnabled(False)
        layout_fmt.addWidget(self._start_btn)
        layout_fmt.addWidget(self._stop_btn)
        self._layout.addWidget(card_format)

        # Progress
        self._progress = ProgressBar(self)
        self._progress.setVisible(False)
        self._layout.addWidget(self._progress)

        # Log
        card_log = QGroupBox("Log")
        log_layout = QVBoxLayout(card_log)
        self._log = PlainTextEdit(self)
        self._log.setReadOnly(True)
        self._log.setMinimumHeight(200)
        log_layout.addWidget(self._log)
        self._layout.addWidget(card_log)

        self._layout.addStretch(1)

    def _browse_output(self):
        path = QFileDialog.getExistingDirectory(self, "Output folder", self._path_edit.text())
        if path:
            self._path_edit.setText(path)

    def _log_append(self, text: str):
        self._log.appendPlainText(text)
        scrollbar = self._log.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _start_download(self):
        url = self._url_edit.text().strip()
        if not url:
            self._log_append("Enter a URL first.")
            return
        self._log.clear()
        self._log_append(f"Starting: {url}")
        self._progress.setVisible(True)
        self._progress.setRange(0, 0)  # indeterminate
        self._start_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)

        self._worker = DownloadWorker(
            url,
            self._path_edit.text().strip() or str(DOWNLOADS_DIR),
            self._format_combo.currentText(),
        )
        self._worker.log_line.connect(self._log_append)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished_signal.connect(self._on_finished)
        self._worker.start()

    def _on_progress(self, value: float):
        if value < 0:
            self._progress.setRange(0, 0)
        else:
            self._progress.setRange(0, 100)
            self._progress.setValue(int(value * 100))

    def _stop_download(self):
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self._log_append("Cancelling...")

    def _on_finished(self, success: bool, message: str):
        self._progress.setVisible(False)
        self._start_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._worker = None
        self._log_append(message)
