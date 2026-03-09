"""URL Download Interface: centered URL/file input, drag-and-drop, progress."""

import os
from urllib.parse import urlparse

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QPixmap
from PyQt5.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    BodyLabel,
    FluentIcon,
    InfoBar,
    LineEdit,
    MessageBoxBase,
    PlainTextEdit,
    ProgressBar,
    ToolButton,
    themeColor,
)

from app.common.paths import PROJECT_ROOT

LOGO_PATH = PROJECT_ROOT / "resources" / "logo.png"

INFOBAR_MS_SUCCESS = 3000
INFOBAR_MS_ERROR = 5000
INFOBAR_MS_WARNING = 4000
INFOBAR_MS_INFO = 3000

VIDEO_EXTENSIONS = {
    "mp4", "mkv", "avi", "mov", "wmv", "flv", "webm", "m4v", "ts", "mpeg", "mpg",
}
AUDIO_EXTENSIONS = {
    "mp3", "aac", "wav", "flac", "ogg", "m4a", "opus", "wma",
}
SUPPORTED_EXTENSIONS = VIDEO_EXTENSIONS | AUDIO_EXTENSIONS


class UrlDownloadInterface(QWidget):
    """Centered URL / file-path input with drag-and-drop and progress feedback."""

    finished = pyqtSignal(str)          # single URL / file path
    bulk_finished = pyqtSignal(list)    # list[str] of validated URLs

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("UrlDownloadInterface")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAcceptDrops(True)

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
        dialog = _BulkUrlDialog(self)
        if dialog.exec_():
            urls = dialog.get_urls()
            if urls:
                self.bulk_finished.emit(urls)
                InfoBar.success(
                    self.tr("Bulk queued"),
                    self.tr(f"{len(urls)} URL(s) sent to download queue."),
                    duration=INFOBAR_MS_SUCCESS,
                    parent=self,
                )
            else:
                InfoBar.warning(
                    self.tr("No valid URLs"),
                    self.tr("Please enter at least one valid http/https URL."),
                    duration=INFOBAR_MS_WARNING,
                    parent=self,
                )

    def _on_action_clicked(self):
        self._submit()

    def _submit(self):
        text = self._url_input.text().strip()
        if not text:
            InfoBar.warning(
                self.tr("Empty input"),
                self.tr("Please enter a URL or drop a media file first."),
                duration=INFOBAR_MS_WARNING,
                parent=self,
            )
            return
        if os.path.isfile(text):
            self.finished.emit(text)
        elif self._is_valid_url(text):
            self.finished.emit(text)
            InfoBar.success(
                self.tr("Queued"),
                self.tr("URL sent to download queue."),
                duration=INFOBAR_MS_SUCCESS,
                parent=self,
            )
        else:
            InfoBar.error(
                self.tr("Invalid input"),
                self.tr("Enter a valid file path or video URL."),
                duration=INFOBAR_MS_ERROR,
                parent=self,
            )

    # ── Drag & drop ───────────────────────────────────────────────────────

    def dragEnterEvent(self, event):
        event.accept() if event.mimeData().hasUrls() else event.ignore()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if not os.path.isfile(path):
                continue
            ext = os.path.splitext(path)[1][1:].lower()
            if ext in SUPPORTED_EXTENSIONS:
                self._url_input.setText(path)
                InfoBar.success(
                    self.tr("File imported"),
                    path,
                    duration=INFOBAR_MS_SUCCESS,
                    parent=self,
                )
            else:
                InfoBar.error(
                    self.tr(f"Unsupported format: .{ext}"),
                    self.tr("Drop a video or audio file."),
                    duration=INFOBAR_MS_ERROR,
                    parent=self,
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

    @staticmethod
    def _is_valid_url(url: str) -> bool:
        try:
            r = urlparse(url)
            return r.scheme in ("http", "https") and bool(r.netloc)
        except ValueError:
            return False

    def get_url(self) -> str:
        return self._url_input.text().strip()

    def set_url(self, text: str):
        self._url_input.setText(text)


# ── Bulk URL dialog ────────────────────────────────────────────────────────────

class _BulkUrlDialog(MessageBoxBase):
    """Dialog for entering multiple URLs — one per line."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self.yesButton.setText(self.tr("Queue all"))
        self.cancelButton.setText(self.tr("Cancel"))

    def _setup_ui(self) -> None:
        self.viewLayout.addWidget(BodyLabel(self.tr("Bulk URL Download"), self))

        self._text_edit = PlainTextEdit(self)
        self._text_edit.setPlaceholderText(
            self.tr(
                "Paste one URL per line:\n\n"
                "https://youtube.com/watch?v=…\n"
                "https://tiktok.com/@user/video/…\n"
                "https://instagram.com/p/…\n\n"
                "Blank lines and duplicates are ignored automatically."
            )
        )
        self._text_edit.setMinimumWidth(480)
        self._text_edit.setMinimumHeight(320)

        self.viewLayout.addWidget(self._text_edit)
        self.viewLayout.setSpacing(10)

    def get_urls(self) -> list[str]:
        """Return deduplicated, validated http/https URLs from the text box."""
        seen: set[str] = set()
        result: list[str] = []
        for line in self._text_edit.toPlainText().splitlines():
            url = line.strip()
            if not url or url in seen:
                continue
            try:
                r = urlparse(url)
                if r.scheme in ("http", "https") and r.netloc:
                    seen.add(url)
                    result.append(url)
            except ValueError:
                pass
        return result
