"""Clear Old Tasks dialog — shown before starting a new download batch."""
from __future__ import annotations

from qfluentwidgets import (
    BodyLabel,
    MessageBoxBase,
    SubtitleLabel,
)


class ClearOldTasksDialog(MessageBoxBase):
    """Shown when the queue still contains completed/failed tasks before a new batch."""

    def __init__(self, done_count: int, parent=None):
        super().__init__(parent)
        self._build(done_count)
        self.yesButton.setText(self.tr("Clear & Start"))
        self.cancelButton.setText(self.tr("Start Anyway"))
        self.widget.setMinimumWidth(420)

    # ── Build ──────────────────────────────────────────────────────────────

    def _build(self, done_count: int) -> None:
        self.viewLayout.addWidget(SubtitleLabel(self.tr("Old tasks in queue"), self))
        self.viewLayout.addWidget(
            BodyLabel(
                self.tr(
                    "{count} completed/failed task(s) are still in the queue.\n"
                    "Remove them before starting the new batch?"
                ).format(count=done_count),
                self,
            )
        )
        self.viewLayout.setSpacing(8)
