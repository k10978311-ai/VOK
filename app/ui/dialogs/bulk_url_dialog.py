"""Bulk URL dialog: multiple URLs, one per line."""
from __future__ import annotations

from qfluentwidgets import BodyLabel, MessageBoxBase, PlainTextEdit

from app.core.task_queue import is_http_url


class BulkUrlDialog(MessageBoxBase):
    """Dialog for entering multiple URLs (one per line)."""

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
            if not url or url in seen or not is_http_url(url):
                continue
            seen.add(url)
            result.append(url)
        return result
