from __future__ import annotations

from typing import Any, Dict, List, Optional

from PyQt5.QtCore import QAbstractTableModel, QModelIndex, Qt

# Table column indices
COL_IDX      = 0
COL_TITLE    = 1
COL_HOST     = 2
COL_STATUS   = 3
COL_SIZE     = 4
COL_PROGRESS = 5

_COL_HEADERS = ["#", "Title", "Host", "Status", "Size", "Progress %"]

_STATUS_PENDING  = "Pending"
_STATUS_RUNNING  = "Downloading"
_STATUS_DONE     = "Done"
_STATUS_ERROR    = "Error"
_STATUS_CANCELED = "Canceled"


class DownloadTaskModel(QAbstractTableModel):
    """Model holding a list of download task rows."""

    def __init__(self) -> None:
        super().__init__()
        self._rows: List[Dict[str, Any]] = []

    # ── QAbstractTableModel interface ────────────────────────────────────────

    def rowCount(self, parent: Optional[QModelIndex] = None) -> int:
        return len(self._rows)

    def columnCount(self, parent: Optional[QModelIndex] = None) -> int:
        return len(_COL_HEADERS)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:  # type: ignore
        if not index.isValid():
            return None
        row = self._rows[index.row()]
        col = index.column()

        if role == Qt.DecorationRole:  # type: ignore
            if col == COL_HOST:
                from app.ui.helpers.downloader import host_icon
                return host_icon(row.get("host", ""))

        if role == Qt.DisplayRole:  # type: ignore
            if col == COL_IDX:
                return str(index.row() + 1)
            if col == COL_TITLE:
                return row.get("title", "")
            if col == COL_HOST:
                return row.get("host", "")
            if col == COL_STATUS:
                return row.get("status", _STATUS_PENDING)
            if col == COL_SIZE:
                return row.get("size", "—")
            if col == COL_PROGRESS:
                p = row.get("progress", 0)
                return f"{p}%" if isinstance(p, int) else "—"

        if role == Qt.TextAlignmentRole:  # type: ignore
            if col in (COL_IDX, COL_HOST, COL_STATUS, COL_SIZE, COL_PROGRESS):
                return Qt.AlignCenter  # type: ignore
        return None

    def headerData(self, section: int, orientation: Qt.Orientation,
                   role: int = Qt.DisplayRole) -> Any:  # type: ignore
        if role == Qt.DisplayRole:  # type: ignore
            if orientation == Qt.Horizontal:  # type: ignore
                return _COL_HEADERS[section] if section < len(_COL_HEADERS) else None
            if orientation == Qt.Vertical:  # type: ignore
                return str(section + 1)
        if role == Qt.TextAlignmentRole:  # type: ignore
            return Qt.AlignCenter  # type: ignore
        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        if not index.isValid():
            return Qt.NoItemFlags  # type: ignore
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable  # type: ignore

    # ── Mutations ────────────────────────────────────────────────────────────

    def add_task(self, title: str, host: str = "", fmt: str = "",
                 path: str = "", url: str = "") -> int:
        """Append a new pending task; returns its row index."""
        row_idx = len(self._rows)
        self.beginInsertRows(QModelIndex(), row_idx, row_idx)
        self._rows.append({
            "title":    title,
            "host":     host,
            "format":   fmt,
            "status":   _STATUS_PENDING,
            "size":     "\u2014",
            "progress": 0,
            "path":     path,
            "url":      url or path,
        })
        self.endInsertRows()
        return row_idx

    def update_task(self, row_idx: int, **kwargs: Any) -> None:
        if 0 <= row_idx < len(self._rows):
            self._rows[row_idx].update(kwargs)
            self.dataChanged.emit(
                self.index(row_idx, 0),
                self.index(row_idx, len(_COL_HEADERS) - 1),
                [Qt.DisplayRole, Qt.DecorationRole],  # type: ignore
            )

    def remove_selected(self, rows: List[int]) -> None:
        for row_idx in sorted(rows, reverse=True):
            if 0 <= row_idx < len(self._rows):
                self.beginRemoveRows(QModelIndex(), row_idx, row_idx)
                self._rows.pop(row_idx)
                self.endRemoveRows()

    def retry_rows(self, rows: List[int]) -> None:
        """Reset Error/Canceled rows back to Pending so they can be re-queued."""
        for row_idx in rows:
            if 0 <= row_idx < len(self._rows):
                row = self._rows[row_idx]
                if row.get("status") in (_STATUS_ERROR, _STATUS_CANCELED):
                    row["status"] = _STATUS_PENDING
                    row["progress"] = 0
                    row["size"] = "—"
                    self.dataChanged.emit(
                        self.index(row_idx, 0),
                        self.index(row_idx, len(_COL_HEADERS) - 1),
                        [Qt.DisplayRole],  # type: ignore
                    )

    def clear(self) -> None:
        self.beginResetModel()
        self._rows.clear()
        self.endResetModel()

    def get_task(self, row_idx: int) -> Optional[Dict[str, Any]]:
        if 0 <= row_idx < len(self._rows):
            return self._rows[row_idx]
        return None

    def find_url(self, url: str) -> int:
        """Return the row index of the first task with this URL, or -1 if not found."""
        for i, row in enumerate(self._rows):
            if row.get("url") == url:
                return i
        return -1
