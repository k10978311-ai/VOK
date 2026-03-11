"""URL Download Interface: centered URL/file input, drag-and-drop, progress."""

from pathlib import Path

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QPixmap
from PyQt5.QtWidgets import QApplication, QHBoxLayout, QLabel, QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel,
    FluentIcon,
    IndeterminateProgressBar,
    LineEdit,
    ProgressBar,
    ToolButton,
    themeColor,
)

from app.common.concurrent import PlaylistFetchWorker
from app.common.paths import RESOURCES_DIR
from app.config.store import load_settings
from app.core.download import detect_collection_url
from app.core.task_queue import (
    SUPPORTED_EXTENSIONS,
    is_http_url,
    build_playlist_task_entries,
)
from app.ui.dialogs import BulkUrlDialog

LOGO_PATH = RESOURCES_DIR / "logo.png"

INFOBAR_MS_SUCCESS = 3000
INFOBAR_MS_ERROR = 5000
INFOBAR_MS_WARNING = 4000
INFOBAR_MS_INFO = 3000


class UrlDownloadInterface(QWidget):
    """Centered URL / file-path input with drag-and-drop and progress feedback."""

    finished = pyqtSignal(str)          # single URL / file path
    bulk_finished = pyqtSignal(list)    # list[str] of validated URLs
    message_requested = pyqtSignal(str, str, str, int, object)  # level, title, message, duration, position

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("UrlDownloadInterface")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAcceptDrops(True)

        self._fetch_worker: PlaylistFetchWorker | None = None

        self._setup_ui()
        self._setup_signals()

    # ── UI ────────────────────────────────────────────────────────────────

    def _setup_ui(self):
        self._layout = QVBoxLayout(self)
        self._layout.setSpacing(50)
        self._layout.addSpacing(120)
        self._build_logo()
        self._build_search_row()
        self._build_status_row()

    def _build_logo(self):
        self._logo_label = QLabel(self)
        if LOGO_PATH.exists():
            pixmap = QPixmap(str(LOGO_PATH)).scaled(
                150, 150,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            self._logo_label.setPixmap(pixmap)
        self._logo_label.setAlignment(Qt.AlignCenter)
        self._layout.addWidget(self._logo_label)
        self._layout.addSpacing(10)

    def _build_search_row(self):
        row = QHBoxLayout()
        row.setContentsMargins(80, 0, 80, 0)
        row.setSpacing(8)

        self._url_input = LineEdit(self)
        self._url_input.setPlaceholderText(
            self.tr("https://  —  Paste video URL, then configure options below …")
        )
        self._url_input.setFixedHeight(44)
        self._url_input.setClearButtonEnabled(True)
        # Override ALL LineEdit / QLineEdit states so the fluent orange underline
        # never shows — we own the full rounded border instead.
        self._url_input.setStyleSheet("""
            LineEdit, QLineEdit {
                border-radius: 22px;
                padding: 0 16px;
                background-color: transparent;
                border: 1px solid rgba(128,128,128,0.25);
                outline: none;
            }
            LineEdit:focus, QLineEdit:focus {
                border: 1.5px solid rgba(128,128,128,0.55);
            }
            LineEdit:hover, QLineEdit:hover {
                border: 1px solid rgba(128,128,128,0.40);
            }
        """)

        _aux_ss = "QToolButton { border: none; border-radius: 20px; background-color: rgba(128,128,128,0.18); } QToolButton:hover { background-color: rgba(128,128,128,0.28); }"

        self._paste_btn = ToolButton(FluentIcon.PASTE, self)
        self._paste_btn.setFixedSize(40, 40)
        self._paste_btn.setToolTip(self.tr("Paste from clipboard"))
        self._paste_btn.setStyleSheet(_aux_ss)

        self._bulk_btn = ToolButton(FluentIcon.COPY, self)
        self._bulk_btn.setFixedSize(40, 40)
        self._bulk_btn.setToolTip(self.tr("Bulk URLs — enter multiple URLs at once"))
        self._bulk_btn.setStyleSheet(_aux_ss)

        self._action_btn = ToolButton(FluentIcon.DOWNLOAD, self)
        self._action_btn.setFixedSize(40, 40)
        self._apply_primary_btn_style()

        row.addWidget(self._url_input)
        row.addWidget(self._paste_btn)
        row.addWidget(self._bulk_btn)
        row.addWidget(self._action_btn)
        self._layout.addLayout(row)
        self._layout.addSpacing(100)

    def _apply_primary_btn_style(self):
        """Style the download button using the current theme primary colour."""
        c: QColor = themeColor()
        h = c.name()                                    # e.g. "#0078d4"
        hover = QColor(c).darker(115).name()
        pressed = QColor(c).darker(130).name()
        self._action_btn.setStyleSheet(
            self._action_btn.styleSheet() + f"""
            QToolButton         {{ border-radius: 20px; border: none; background-color: {h}; }}
            QToolButton:hover   {{ background-color: {hover}; }}
            QToolButton:pressed {{ background-color: {pressed}; }}
            """
        )

    def _build_status_row(self):
        status_layout = QVBoxLayout()
        status_layout.setContentsMargins(50, 0, 30, 5)
        status_layout.setAlignment(Qt.AlignBottom | Qt.AlignHCenter)

        self._status_label = BodyLabel(self.tr("Ready"), self)
        self._status_label.setStyleSheet("font-size: 14px; color: #888888;")
        self._status_label.hide()
        status_layout.addWidget(self._status_label, 0, Qt.AlignCenter)

        self._progress_bar = ProgressBar(self)
        self._progress_bar.setFixedWidth(300)
        self._progress_bar.hide()
        status_layout.addWidget(self._progress_bar, 0, Qt.AlignCenter)

        # Indeterminate spinner shown while extracting a playlist/channel
        self._fetch_progress = IndeterminateProgressBar(self)
        self._fetch_progress.setFixedWidth(300)
        self._fetch_progress.hide()
        status_layout.addWidget(self._fetch_progress, 0, Qt.AlignCenter)

        # Cancel extraction button
        self._cancel_fetch_btn = ToolButton(FluentIcon.CANCEL, self)
        self._cancel_fetch_btn.setToolTip(self.tr("Cancel extraction"))
        self._cancel_fetch_btn.hide()
        self._cancel_fetch_btn.clicked.connect(self._cancel_extraction)
        status_layout.addWidget(self._cancel_fetch_btn, 0, Qt.AlignCenter)

        self._layout.addStretch(1)
        self._layout.addLayout(status_layout)

    # ── Signals ───────────────────────────────────────────────────────────

    def _setup_signals(self):
        self._action_btn.clicked.connect(self._on_action_clicked)
        self._paste_btn.clicked.connect(self._on_paste_clicked)
        self._bulk_btn.clicked.connect(self._on_bulk_clicked)
        self._url_input.textChanged.connect(self._on_text_changed)

    # ── Slots ─────────────────────────────────────────────────────────────

    def _on_text_changed(self):
        self._action_btn.setIcon(FluentIcon.DOWNLOAD)

    def _on_paste_clicked(self):
        text = QApplication.clipboard().text().strip()
        if text:
            self._url_input.setText(text)

    def _on_bulk_clicked(self):
        dialog = BulkUrlDialog(self)
        if dialog.exec_():
            urls = dialog.get_urls()
            if urls:
                self.bulk_finished.emit(urls)
                self._emit_message(
                    "success", self.tr("Bulk queued"),
                    self.tr(f"{len(urls)} URL(s) sent to download queue."),
                    INFOBAR_MS_SUCCESS,
                )
            else:
                self._emit_message(
                    "warning", self.tr("No valid URLs"),
                    self.tr("Please enter at least one valid http/https URL."),
                    INFOBAR_MS_WARNING,
                )

    def _on_action_clicked(self):
        self._submit()

    def _submit(self):
        text = self._url_input.text().strip()
        if not text:
            self._emit_message(
                "warning", self.tr("Empty input"),
                self.tr("Please enter a URL or drop a media file first."),
                INFOBAR_MS_WARNING,
            )
            return
        path = Path(text)
        if path.is_file():
            self.finished.emit(text)
        elif is_http_url(text):
            if detect_collection_url(text):
                self._start_extraction(text)
            else:
                self.finished.emit(text)
                self._emit_message(
                    "success", self.tr("Queued"),
                    self.tr("URL sent to download queue."), INFOBAR_MS_SUCCESS,
                )
        else:
            self._emit_message(
                "error", self.tr("Invalid input"),
                self.tr("Enter a valid file path or video URL."), INFOBAR_MS_ERROR,
            )

    # ── Playlist / channel / profile extraction ───────────────────────────

    def _emit_message(self, level: str, title: str, message: str, duration: int, position=None) -> None:
        self.message_requested.emit(level, title, message, duration, position)

    def _reset_extraction_ui(self) -> None:
        """Hide progress, cancel button; re-enable action button."""
        self._fetch_progress.stop()
        self._fetch_progress.hide()
        self._cancel_fetch_btn.hide()
        self._action_btn.setEnabled(True)

    def _start_extraction(self, url: str) -> None:
        """Start PlaylistFetchWorker to extract all video entries from a collection URL."""
        # Cancel any previous worker still running
        if self._fetch_worker and self._fetch_worker.isRunning():
            self._fetch_worker.cancel()
            self._fetch_worker.wait()

        cookies = load_settings().get("cookies_file", "")

        self._fetch_worker = PlaylistFetchWorker(url=url, cookies_file=cookies, parent=self)
        self._fetch_worker.entries_ready.connect(self._on_entries_ready)
        self._fetch_worker.finished_signal.connect(self._on_extraction_finished)
        self._fetch_worker.log_line.connect(
            lambda msg: self._status_label.setText(msg[:80])
        )

        self._action_btn.setEnabled(False)
        self._fetch_progress.show()
        self._fetch_progress.start()
        self._cancel_fetch_btn.show()
        self._status_label.setText(self.tr("Extracting playlist / channel…"))
        self._status_label.show()

        self._fetch_worker.start()

        self.message_requested.emit(
            "info",
            self.tr("Extracting"),
            self.tr("Fetching video list from collection URL…"),
            INFOBAR_MS_INFO,
            None,
        )

    def _on_entries_ready(self, entries: list) -> None:
        tasks = build_playlist_task_entries(entries)
        if tasks:
            self.bulk_finished.emit(tasks)

    def _on_extraction_finished(self, success: bool, message: str) -> None:
        self._reset_extraction_ui()
        if success:
            self._status_label.setText(message)
            self._emit_message("success", self.tr("Extraction complete"), message, INFOBAR_MS_SUCCESS)
        else:
            self._status_label.setText(self.tr("Extraction failed"))
            self._emit_message("error", self.tr("Extraction failed"), message, INFOBAR_MS_ERROR)

    def _cancel_extraction(self) -> None:
        if self._fetch_worker and self._fetch_worker.isRunning():
            self._fetch_worker.cancel()
        self._reset_extraction_ui()
        self._status_label.setText(self.tr("Extraction cancelled"))
        self._emit_message(
            "warning", self.tr("Cancelled"),
            self.tr("Playlist extraction was cancelled."), INFOBAR_MS_WARNING,
        )

    # ── Drag & drop ───────────────────────────────────────────────────────

    def dragEnterEvent(self, event):
        event.accept() if event.mimeData().hasUrls() else event.ignore()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            path_str = url.toLocalFile()
            if not path_str:
                continue
            path = Path(path_str)
            if not path.is_file():
                continue
            ext = path.suffix.lstrip(".").lower()
            if ext in SUPPORTED_EXTENSIONS:
                self._url_input.setText(path_str)
                self._emit_message("success", self.tr("File imported"), path_str, INFOBAR_MS_SUCCESS)
            else:
                self._emit_message(
                    "error", self.tr(f"Unsupported format: .{ext}"),
                    self.tr("Drop a video or audio file."), INFOBAR_MS_ERROR,
                )
            break

    # ── Progress feedback (called externally) ─────────────────────────────

    def set_progress(self, value: int, status: str = ""):
        self._progress_bar.show()
        self._status_label.show()
        self._progress_bar.setValue(value)
        if status:
            self._status_label.setText(status)

    def reset_progress(self):
        self._progress_bar.hide()
        self._status_label.hide()
        self._progress_bar.setValue(0)

    # ── Helpers ───────────────────────────────────────────────────────────

    def get_url(self) -> str:
        return self._url_input.text().strip()

    def set_url(self, text: str):
        self._url_input.setText(text)
