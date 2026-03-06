# coding: utf-8
import os
from datetime import datetime

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    CardWidget,
    FluentIcon,
    IconWidget,
    IndeterminateProgressBar,
    LargeTitleLabel,
    ProgressBar,
    SegmentedWidget,
    SubtitleLabel,
    ToolButton,
)

from app.common.signal_bus import signal_bus
from .base import BaseView


# ── Shared card base ───────────────────────────────────────────────────────────

class _TaskCardBase(CardWidget):
    """Common layout for a single task row: icon | name+sub | status badge | open-folder btn."""

    _STATUS_COLORS = {
        "Downloading": ("rgba(33,150,243,0.14)",  "#64B5F6"),
        "Enhancing":   ("rgba(255,190,0,0.14)",   "#FFD54F"),
        "Finished":    ("rgba(0,200,120,0.14)",   "#4DB6AC"),
        "Failed":      ("rgba(255,80,80,0.14)",   "#EF9A9A"),
    }

    def __init__(
        self,
        job_id: str,
        title: str,
        task_type: str = "download",
        output_path: str = "",
        size_bytes: int = -1,
        status: str = "Downloading",
        parent=None,
    ):
        super().__init__(parent)
        self.job_id = job_id
        self.task_type = task_type
        self.output_path = output_path

        self.setFixedHeight(72)
        self._icon_widget = self._make_icon()

        self._name_label = BodyLabel(title or "—")
        self._name_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self._name_label.setMaximumWidth(9999)  # let layout constrain, text will clip naturally

        self._sub_label = CaptionLabel(self._sub_text(size_bytes))
        self._sub_label.setTextColor("#888", "#666")

        # Vertical text column — subclasses may append rows before layout is locked
        self._text_col = QVBoxLayout()
        self._text_col.setSpacing(2)
        self._text_col.setContentsMargins(0, 0, 0, 0)
        self._text_col.addWidget(self._name_label)
        self._text_col.addWidget(self._sub_label)

        self._status_label = QLabel(status)
        self._status_label.setAlignment(Qt.AlignCenter)
        self._status_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self._status_label.setStyleSheet(self._status_style(status))
        self._status_label.adjustSize()

        self._open_btn = ToolButton(FluentIcon.FOLDER)
        self._open_btn.setToolTip("Open folder")
        self._open_btn.setFixedSize(32, 32)
        self._open_btn.clicked.connect(self._open_folder)

        h = QHBoxLayout(self)
        h.setContentsMargins(16, 0, 16, 0)
        h.setSpacing(12)
        h.addWidget(self._icon_widget)
        h.addLayout(self._text_col, 1)
        h.addWidget(self._status_label)
        h.addWidget(self._open_btn)

    def _make_icon(self) -> QWidget:
        ico = IconWidget(FluentIcon.VIDEO, self)
        ico.setFixedSize(32, 32)
        return ico

    def _open_folder(self) -> None:
        path = self.output_path
        if path and os.path.isfile(path):
            os.startfile(os.path.dirname(path))
        elif path and os.path.isdir(path):
            os.startfile(path)

    @staticmethod
    def _sub_text(size_bytes: int) -> str:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        if size_bytes <= 0:
            return ts
        n = float(size_bytes)
        for unit in ("B", "KB", "MB", "GB"):
            if n < 1024:
                return f"{ts}  ·  {n:.1f} {unit}"
            n /= 1024
        return f"{ts}  ·  {n:.1f} TB"

    @classmethod
    def _status_style(cls, status: str) -> str:
        bg, fg = cls._STATUS_COLORS.get(status, ("rgba(150,150,150,0.12)", "#999"))
        return (
            f"QLabel {{ background: {bg}; color: {fg}; border-radius: 8px; "
            f"font-size: 10px; font-weight: 700; letter-spacing: 0.3px;"
            f" padding: 3px 10px; }}"
        )

    def set_status(self, status: str) -> None:
        self._status_label.setText(status)
        self._status_label.setStyleSheet(self._status_style(status))
        self._status_label.adjustSize()


# ── Download card ──────────────────────────────────────────────────────────────

class _DownloadCard(_TaskCardBase):
    """Card for a download task; includes an inline progress bar while active."""

    def __init__(
        self,
        job_id: str,
        url: str,
        output_path: str = "",
        size_bytes: int = -1,
        status: str = "Downloading",
        parent=None,
    ):
        name = self._name_from_url(url)
        super().__init__(
            job_id, name,
            task_type="download",
            output_path=output_path,
            size_bytes=size_bytes,
            status=status,
            parent=parent,
        )
        self._url = url
        self._is_active = (status == "Downloading")

        # Thin progress bar appended below the text column
        self._progress = ProgressBar(self)
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setFixedHeight(3)
        self._progress.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._progress.setVisible(self._is_active)
        self._text_col.addWidget(self._progress)

        if self._is_active:
            self.setFixedHeight(80)

    def _make_icon(self) -> QWidget:
        ico = IconWidget(FluentIcon.DOWNLOAD, self)
        ico.setFixedSize(32, 32)
        return ico

    def set_progress(self, value: float) -> None:
        self._progress.setValue(int(max(0.0, min(1.0, value)) * 100))

    def mark_finished(self, success: bool, filepath: str, size_bytes: int) -> None:
        self.output_path = filepath
        self._is_active = False
        self.set_status("Finished" if success else "Failed")
        self._progress.setVisible(False)
        self.setFixedHeight(72)
        if filepath:
            self._name_label.setText(os.path.basename(filepath))
        self._sub_label.setText(self._sub_text(size_bytes))

    @staticmethod
    def _name_from_url(url: str) -> str:
        if not url:
            return "—"
        seg = url.rstrip("/").split("/")
        return (seg[-1] or url)[:80]


# ── Enhance card ───────────────────────────────────────────────────────────────

class _EnhanceCard(_TaskCardBase):
    """Card for an enhance post-processing task with an indeterminate spinner."""

    def __init__(
        self,
        job_id: str,
        filename: str,
        output_path: str = "",
        size_bytes: int = -1,
        status: str = "Enhancing",
        parent=None,
    ):
        super().__init__(
            job_id, filename or "—",
            task_type="enhance",
            output_path=output_path,
            size_bytes=size_bytes,
            status=status,
            parent=parent,
        )
        # Indeterminate bar while enhancing
        self._spinner = IndeterminateProgressBar(self)
        self._spinner.setFixedHeight(3)
        self._spinner.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._spinner.setVisible(status == "Enhancing")
        self._text_col.addWidget(self._spinner)

        if status == "Enhancing":
            self.setFixedHeight(80)

    def _make_icon(self) -> QWidget:
        ico = IconWidget(FluentIcon.SPEED_HIGH, self)
        ico.setFixedSize(32, 32)
        return ico

    def mark_finished(self, success: bool, output_path: str, size_bytes: int) -> None:
        self.output_path = output_path
        self.set_status("Finished" if success else "Failed")
        self._spinner.setVisible(False)
        self.setFixedHeight(72)
        if output_path:
            self._name_label.setText(os.path.basename(output_path))
        self._sub_label.setText(self._sub_text(size_bytes))


# ── Empty-state placeholder ───────────────────────────────────────────────────

class _EmptyState(QWidget):
    """Centered icon + title + caption shown when a list has no cards."""

    def __init__(self, icon: FluentIcon, title: str, caption: str, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

        ico = IconWidget(icon, self)
        ico.setFixedSize(48, 48)
        _op = QGraphicsOpacityEffect(ico)
        _op.setOpacity(0.35)
        ico.setGraphicsEffect(_op)

        lbl_title = SubtitleLabel(title, self)
        lbl_title.setAlignment(Qt.AlignCenter)
        lbl_title.setStyleSheet("color: rgba(150,150,150,0.9);")

        lbl_cap = CaptionLabel(caption, self)
        lbl_cap.setAlignment(Qt.AlignCenter)
        lbl_cap.setStyleSheet("color: rgba(120,120,120,0.7);")

        v = QVBoxLayout(self)
        v.setSpacing(8)
        v.setContentsMargins(24, 0, 24, 0)
        v.addStretch(1)
        v.addWidget(ico, 0, Qt.AlignHCenter)
        v.addWidget(lbl_title, 0, Qt.AlignHCenter)
        v.addWidget(lbl_cap, 0, Qt.AlignHCenter)
        v.addStretch(1)


# ── Scrollable card list ───────────────────────────────────────────────────────

_EMPTY_CONFIGS = {
    "downloading": (FluentIcon.DOWNLOAD,   "No active downloads",     "Downloads will appear here"),
    "enhancing":   (FluentIcon.SPEED_HIGH, "No active enhance tasks",  "Enhance jobs will appear here"),
    "finished":    (FluentIcon.COMPLETED,  "Nothing finished yet",    "Completed tasks will appear here"),
    "failed":      (FluentIcon.INFO,       "No failed tasks",          "Failed tasks will appear here"),
}


class _CardListWidget(QScrollArea):
    """Scrollable list of task cards with a rich empty-state placeholder."""

    def __init__(self, tab_key: str = "", parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QScrollArea.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        self._inner = QWidget()
        self._inner.setStyleSheet("background: transparent;")
        self._vbox = QVBoxLayout(self._inner)
        self._vbox.setContentsMargins(0, 4, 0, 4)
        self._vbox.setSpacing(8)

        icon, title, caption = _EMPTY_CONFIGS.get(
            tab_key, (FluentIcon.INFO, "No tasks yet", "")
        )
        self._empty = _EmptyState(icon, title, caption, self._inner)
        self._empty.setMinimumHeight(260)
        self._vbox.addWidget(self._empty)
        self._vbox.addStretch(1)

        self.setWidget(self._inner)
        self._cards: list = []
        self._has_cards: bool = False   # track manually — isVisible() unreliable in QStackedWidget

    def add_card(self, card: _TaskCardBase) -> None:
        if not self._has_cards:
            self._empty.hide()
            self._has_cards = True
        # Insert before the trailing stretch
        self._vbox.insertWidget(self._vbox.count() - 1, card)
        self._cards.append(card)

    def find_card(self, job_id: str):
        return next((c for c in self._cards if c.job_id == job_id), None)

    def remove_card(self, card: _TaskCardBase) -> None:
        if card in self._cards:
            self._cards.remove(card)
        self._vbox.removeWidget(card)
        card.hide()
        card.deleteLater()
        if not self._cards:
            self._empty.show()
            self._has_cards = False

    def count(self) -> int:
        return len(self._cards)


# ── Active-jobs badge ──────────────────────────────────────────────────────────

class _ActiveBadge(QLabel):
    """Small circular pill showing active job count; hidden when zero."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setFixedSize(22, 22)
        self.hide()

    def set_count(self, n: int) -> None:
        if n > 0:
            self.setText(str(n))
            self.setStyleSheet(
                "QLabel { background: #FF5252; color: white; border-radius: 11px; "
                "font-size: 10px; font-weight: 700; }"
            )
            self.show()
        else:
            self.hide()


# ── Main interface ─────────────────────────────────────────────────────────────

class TaskInterface(BaseView):
    """Unified job tracker: Downloading / Enhancing / Finished / Failed tabs."""

    _TAB_DL       = "downloading"
    _TAB_ENHANCE  = "enhancing"
    _TAB_FINISHED = "finished"
    _TAB_FAILED   = "failed"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TaskInterface")
        self._build_ui()
        self._connect_signals()

    # ── UI construction ────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        hdr = QWidget()
        hdr.setStyleSheet("background: transparent;")
        hdr_row = QHBoxLayout(hdr)
        hdr_row.setContentsMargins(0, 0, 0, 0)
        hdr_row.setSpacing(8)
        hdr_row.addWidget(LargeTitleLabel("Tasks"))
        self._active_badge = _ActiveBadge(hdr)
        hdr_row.addWidget(self._active_badge)
        hdr_row.addStretch(1)

        self._pivot = SegmentedWidget()
        self._pivot.addItem(self._TAB_DL,       "Downloading", lambda: self._stack.setCurrentIndex(0))
        self._pivot.addItem(self._TAB_ENHANCE,  "Enhancing",   lambda: self._stack.setCurrentIndex(1))
        self._pivot.addItem(self._TAB_FINISHED, "Finished",    lambda: self._stack.setCurrentIndex(2))
        self._pivot.addItem(self._TAB_FAILED,   "Failed",      lambda: self._stack.setCurrentIndex(3))
        self._pivot.setCurrentItem(self._TAB_DL)

        self._stack = QStackedWidget()
        self._dl_view       = _CardListWidget("downloading")
        self._enhance_view  = _CardListWidget("enhancing")
        self._finished_view = _CardListWidget("finished")
        self._failed_view   = _CardListWidget("failed")
        self._stack.addWidget(self._dl_view)
        self._stack.addWidget(self._enhance_view)
        self._stack.addWidget(self._finished_view)
        self._stack.addWidget(self._failed_view)

        self._layout.addWidget(hdr)
        self._layout.addWidget(self._pivot)
        self._layout.addWidget(self._stack, 1)

    # ── Signal wiring ──────────────────────────────────────────────────────

    def _connect_signals(self) -> None:
        signal_bus.download_started.connect(self._on_download_started)
        signal_bus.download_progress.connect(self._on_download_progress)
        signal_bus.download_finished.connect(self._on_download_finished)
        signal_bus.enhance_started.connect(self._on_enhance_started)
        signal_bus.enhance_finished.connect(self._on_enhance_finished)

    # ── Download handlers ──────────────────────────────────────────────────

    def _on_download_started(self, job_id: str, url: str, output_dir: str) -> None:
        card = _DownloadCard(
            job_id, url,
            output_path=output_dir,
            status="Downloading",
            parent=self._dl_view,
        )
        self._dl_view.add_card(card)
        self._refresh_badge()

    def _on_download_progress(self, job_id: str, progress: float) -> None:
        card = self._dl_view.find_card(job_id)
        if isinstance(card, _DownloadCard):
            card.set_progress(progress)

    def _on_download_finished(
        self, job_id: str, success: bool, url: str, filepath: str, size_bytes: int
    ) -> None:
        card = self._dl_view.find_card(job_id)
        if card:
            self._dl_view.remove_card(card)

        target = self._finished_view if success else self._failed_view
        done_card = _DownloadCard(
            job_id, filepath or url,
            output_path=filepath,
            size_bytes=size_bytes,
            status="Finished" if success else "Failed",
            parent=target,
        )
        done_card.mark_finished(success, filepath, size_bytes)
        target.add_card(done_card)
        self._refresh_badge()

    # ── Enhance handlers ───────────────────────────────────────────────────

    def _on_enhance_started(self, job_id: str, filename: str) -> None:
        # Enhance mode: download card transitions to enhance tab
        dl_card = self._dl_view.find_card(job_id)
        if dl_card:
            self._dl_view.remove_card(dl_card)

        card = _EnhanceCard(
            job_id, filename,
            status="Enhancing",
            parent=self._enhance_view,
        )
        self._enhance_view.add_card(card)
        self._refresh_badge()

    def _on_enhance_finished(
        self, job_id: str, success: bool, filename: str, output_path: str, size_bytes: int
    ) -> None:
        card = self._enhance_view.find_card(job_id)
        if card:
            self._enhance_view.remove_card(card)

        name = os.path.basename(output_path) if output_path else filename
        target = self._finished_view if success else self._failed_view
        done_card = _EnhanceCard(
            job_id, name,
            output_path=output_path,
            size_bytes=size_bytes,
            status="Finished" if success else "Failed",
            parent=target,
        )
        target.add_card(done_card)
        self._refresh_badge()

    # ── Tab navigation ─────────────────────────────────────────────────────

    def _refresh_badge(self) -> None:
        """Update header badge: total active (downloading + enhancing) jobs."""
        self._active_badge.set_count(
            self._dl_view.count() + self._enhance_view.count()
        )

    # ── Public navigation helpers ──────────────────────────────────────────

    def switch_to_downloading(self) -> None:
        self._pivot.setCurrentItem(self._TAB_DL)
        self._stack.setCurrentIndex(0)

    def switch_to_enhancing(self) -> None:
        self._pivot.setCurrentItem(self._TAB_ENHANCE)
        self._stack.setCurrentIndex(1)

    def switch_to_finished(self) -> None:
        self._pivot.setCurrentItem(self._TAB_FINISHED)
        self._stack.setCurrentIndex(2)

    def switch_to_failed(self) -> None:
        self._pivot.setCurrentItem(self._TAB_FAILED)
        self._stack.setCurrentIndex(3)

    # Legacy alias
    def switch_to_active(self) -> None:
        self.switch_to_downloading()
