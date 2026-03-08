"""BatchEnhanceTable — stacked empty-state + data table for the Batch Enhance view."""

from __future__ import annotations

from pathlib import Path

from PyQt5.QtCore import QEvent, Qt, pyqtSignal
from PyQt5.QtGui import QBrush, QColor
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QStackedWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    FluentIcon as FIF,
    IconWidget,
    TableWidget,
    setCustomStyleSheet,
)

from app.ui.utils import format_size

from app.common.utils import (
    ST_PENDING,
    ST_QUEUED,
    ST_RUNNING,
    ST_DONE,
    ST_ERROR,
    STATUS_COLOR,
    VIDEO_EXTENSIONS,
    PAGE_SIZE,
    fmt_duration,
    fmt_eta,
)


COL_IDX      = 0
COL_NAME     = 1
COL_SIZE     = 2
COL_RES      = 3
COL_DURATION = 4
COL_ETA      = 5
COL_STATUS   = 6
COL_PROGRESS = 7

COLS = ["#", "File Name", "Size", "Resolution", "Duration", "Est. Time", "Status", "Progress"]

TABLE_QSS = "QTableView::item { padding-left: 8px; padding-right: 8px; }"


# ── Widget ─────────────────────────────────────────────────────────────────────

class BatchEnhanceTable(QWidget):
    """Stacked widget: empty-state placeholder (index 0) + data TableWidget (index 1)."""

    #: Emitted with a list of absolute file paths when the user drops files/folders.
    filesDropped = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._stack = QStackedWidget(self)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self._stack)
        self._build_empty()
        self._build_table()

    # ── Build ──────────────────────────────────────────────────────────────────

    def _build_empty(self) -> None:
        empty = QWidget()
        lay = QVBoxLayout(empty)
        lay.setAlignment(Qt.AlignCenter)
        lay.setSpacing(8)

        icon_w = IconWidget(FIF.VIDEO, empty)
        icon_w.setFixedSize(48, 48)
        lay.addWidget(icon_w, 0, Qt.AlignCenter)

        title = BodyLabel("No videos loaded", empty)
        title.setAlignment(Qt.AlignCenter)
        lay.addWidget(title)

        hint = CaptionLabel("Use 'Add Files' or 'Add Folder' to get started", empty)
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet("color: gray;")
        lay.addWidget(hint)

        self._stack.addWidget(empty)

    def _build_table(self) -> None:
        self.table = TableWidget()
        self.table.setColumnCount(len(COLS))
        self.table.setHorizontalHeaderLabels(COLS)

        hdr = self.table.horizontalHeader()
        if hdr:
            hdr.setSectionResizeMode(COL_IDX,      QHeaderView.ResizeMode.Fixed)
            hdr.setSectionResizeMode(COL_NAME,     QHeaderView.ResizeMode.Stretch)
            hdr.setSectionResizeMode(COL_SIZE,     QHeaderView.ResizeMode.Fixed)
            hdr.setSectionResizeMode(COL_RES,      QHeaderView.ResizeMode.Fixed)
            hdr.setSectionResizeMode(COL_DURATION, QHeaderView.ResizeMode.Fixed)
            hdr.setSectionResizeMode(COL_ETA,      QHeaderView.ResizeMode.Fixed)
            hdr.setSectionResizeMode(COL_STATUS,   QHeaderView.ResizeMode.Fixed)
            hdr.setSectionResizeMode(COL_PROGRESS, QHeaderView.ResizeMode.Fixed)
            hdr.setSectionsClickable(True)

        self.table.setColumnWidth(COL_IDX,      40)
        self.table.setColumnWidth(COL_SIZE,     85)
        self.table.setColumnWidth(COL_RES,      100)
        self.table.setColumnWidth(COL_DURATION, 80)
        self.table.setColumnWidth(COL_ETA,      85)
        self.table.setColumnWidth(COL_STATUS,   90)
        self.table.setColumnWidth(COL_PROGRESS, 120)

        v = self.table.verticalHeader()
        if v:
            v.setVisible(False)

        self.table.setEditTriggers(TableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(TableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(TableWidget.SelectionMode.ExtendedSelection)
        self.table.setBorderVisible(True)
        self.table.setBorderRadius(8)
        setCustomStyleSheet(self.table, TABLE_QSS, TABLE_QSS)

        # Let the outer widget handle all drag-drop (disable native table DnD).
        self.table.setDragDropMode(TableWidget.DragDropMode.NoDragDrop)
        self.table.viewport().installEventFilter(self)

        self._stack.addWidget(self.table)

    # ── Drag-and-drop ──────────────────────────────────────────────────────────

    def eventFilter(self, source, event):
        """Forward drag-drop events from the table viewport to the outer widget."""
        if source is self.table.viewport():
            t = event.type()
            if t == QEvent.DragEnter:
                if event.mimeData().hasUrls():
                    event.acceptProposedAction()
                return True
            if t == QEvent.DragMove:
                if event.mimeData().hasUrls():
                    event.acceptProposedAction()
                return True
            if t == QEvent.Drop:
                self._process_drop(event)
                return True
        return super().eventFilter(source, event)

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        self._process_drop(event)

    def _process_drop(self, event) -> None:
        paths: list[str] = []
        for url in event.mimeData().urls():
            local = url.toLocalFile()
            if not local:
                continue
            p = Path(local)
            if p.is_file():
                if p.suffix.lower() in VIDEO_EXTENSIONS:
                    paths.append(str(p.resolve()))
            elif p.is_dir():
                for child in sorted(p.rglob("*")):
                    if child.is_file() and child.suffix.lower() in VIDEO_EXTENSIONS:
                        paths.append(str(child.resolve()))
        if paths:
            self.filesDropped.emit(paths)
        event.acceptProposedAction()

    # ── Public API ─────────────────────────────────────────────────────────────

    def show_empty(self) -> None:
        self._stack.setCurrentIndex(0)

    def show_table(self) -> None:
        self._stack.setCurrentIndex(1)

    def populate(
        self,
        page_items: list[tuple[str, str, int, str, float]],
        page_start: int,
        statuses: dict[str, tuple[str, str]],
    ) -> None:
        """Fill table rows from page_items, applying status colors."""
        self.table.setUpdatesEnabled(False)
        self.table.setRowCount(len(page_items))

        for row, (name, path, size, resolution, duration) in enumerate(page_items):
            # #
            num_item = QTableWidgetItem(str(page_start + row + 1))
            num_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, COL_IDX, num_item)

            # File name — full path in tooltip
            name_item = QTableWidgetItem(name)
            name_item.setToolTip(path)
            self.table.setItem(row, COL_NAME, name_item)

            # Size — right-aligned
            size_item = QTableWidgetItem(format_size(size))
            size_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, COL_SIZE, size_item)

            # Resolution
            res_item = QTableWidgetItem(resolution)
            res_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, COL_RES, res_item)

            # Duration
            dur_item = QTableWidgetItem(fmt_duration(duration))
            dur_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, COL_DURATION, dur_item)

            # Status — colored
            st, detail = statuses.get(path, (ST_PENDING, "—"))
            status_item = QTableWidgetItem(st)
            status_item.setTextAlignment(Qt.AlignCenter)
            status_item.setForeground(QBrush(QColor(STATUS_COLOR.get(st, "#888888"))))
            self.table.setItem(row, COL_STATUS, status_item)

            # Est. Time — shown only for pending/queued
            eta_item = QTableWidgetItem(fmt_eta(duration, st))
            eta_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, COL_ETA, eta_item)

            # Progress
            progress_item = QTableWidgetItem(detail if detail else "—")
            progress_item.setTextAlignment(Qt.AlignCenter)
            if st == ST_RUNNING:
                progress_item.setForeground(QBrush(QColor(STATUS_COLOR[ST_RUNNING])))
            elif st == ST_ERROR:
                progress_item.setForeground(QBrush(QColor(STATUS_COLOR[ST_ERROR])))
            self.table.setItem(row, COL_PROGRESS, progress_item)

        self.table.setUpdatesEnabled(True)
        self.show_table()
