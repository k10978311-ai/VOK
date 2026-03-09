"""Clipboard Observer Settings dialog — poll interval and domain filter."""
from __future__ import annotations

from qfluentwidgets import (
    ComboBox,
    LineEdit,
    MessageBoxBase,
    SettingCard,
    SettingCardGroup,
    SubtitleLabel,
)
from qfluentwidgets import FluentIcon as FIF


class ClipboardSettingsDialog(MessageBoxBase):
    """Settings dialog for the clipboard observer (poll interval + domain filter)."""

    _INTERVALS = [200, 500, 1000, 2000, 5000]

    def __init__(self, interval: int, url_filter: str, parent=None):
        super().__init__(parent)
        self._build(interval, url_filter)
        self.yesButton.setText(self.tr("Save"))
        self.cancelButton.setText(self.tr("Cancel"))
        self.widget.setMinimumWidth(500)

    # ── Build ──────────────────────────────────────────────────────────────

    def _build(self, interval: int, url_filter: str) -> None:
        self.viewLayout.addWidget(SubtitleLabel(self.tr("Clipboard Observer Settings"), self))
        self.viewLayout.setSpacing(10)

        grp = SettingCardGroup(self.tr("Configuration"), self)

        self._interval_card = SettingCard(
            FIF.STOP_WATCH,
            self.tr("Poll interval"),
            self.tr("How often to check the clipboard for new URLs"),
        )
        self._interval_combo = ComboBox()
        for ms in self._INTERVALS:
            self._interval_combo.addItem(f"{ms} ms")
        closest = min(self._INTERVALS, key=lambda x: abs(x - interval))
        self._interval_combo.setCurrentIndex(self._INTERVALS.index(closest))
        self._interval_combo.setFixedWidth(100)
        self._interval_card.hBoxLayout.addWidget(self._interval_combo)
        self._interval_card.hBoxLayout.addSpacing(16)
        grp.addSettingCard(self._interval_card)

        self._filter_card = SettingCard(
            FIF.GLOBE,
            self.tr("Domain filter"),
            self.tr("Comma-separated domains to watch (blank = accept all URLs)"),
        )
        self._filter_edit = LineEdit()
        self._filter_edit.setText(url_filter)
        self._filter_edit.setPlaceholderText("youtube.com, tiktok.com")
        self._filter_edit.setMinimumWidth(220)
        self._filter_edit.setClearButtonEnabled(True)
        self._filter_card.hBoxLayout.addWidget(self._filter_edit)
        self._filter_card.hBoxLayout.addSpacing(16)
        grp.addSettingCard(self._filter_card)

        self.viewLayout.addWidget(grp)

    # ── Getters ────────────────────────────────────────────────────────────

    def get_interval(self) -> int:
        return self._INTERVALS[self._interval_combo.currentIndex()]

    def get_filter(self) -> str:
        return self._filter_edit.text().strip()
