"""Dashboard section: 'Included Tools & Features' with a 2x2 grid of feature cards."""

from __future__ import annotations

from PyQt5.QtWidgets import QGridLayout, QWidget,QVBoxLayout
from qfluentwidgets import FluentIcon, SubtitleLabel

from .dashboard_feature_card import DashboardFeatureCard


GRID_SPACING = 14
GRID_MARGINS = 10

DEFAULT_FEATURES = (
    ("Multi-Source Support", "1000+ sites: YouTube, TikTok, Pinterest & more.", FluentIcon.GLOBE),
    ("Quality Selector", "Pick 4K, 1080p, 720p or audio-only (MP3/M4A).", FluentIcon.SETTING),
    ("Batch Download", "Paste multiple URLs or an entire playlist.", FluentIcon.ADD),
    ("Smart File Naming", "Files saved by title/channel automatically.", FluentIcon.EDIT),
)


class DashboardFeatureGrid(QWidget):
    """Section with a title and 2x2 grid of feature cards."""

    def __init__(
        self,
        section_title: str | None = None,
        features: tuple[tuple[str, str, object], ...] | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.setObjectName("DashboardFeatureGrid")

        _section_title = section_title or self.tr("Included Tools & Features")
        _features = features or (
            (self.tr("Multi-Source Support"), self.tr("1000+ sites: YouTube, TikTok, Pinterest & more."), FluentIcon.GLOBE),
            (self.tr("Quality Selector"),     self.tr("Pick 4K, 1080p, 720p or audio-only (MP3/M4A)."), FluentIcon.SETTING),
            (self.tr("Batch Download"),        self.tr("Paste multiple URLs or an entire playlist."),    FluentIcon.ADD),
            (self.tr("Smart File Naming"),     self.tr("Files saved by title/channel automatically."),   FluentIcon.EDIT),
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._section_lbl = SubtitleLabel(_section_title, self)
        layout.addWidget(self._section_lbl)

        grid = QGridLayout()
        grid.setContentsMargins(GRID_MARGINS, GRID_MARGINS, GRID_MARGINS, GRID_MARGINS)
        grid.setSpacing(GRID_SPACING)

        self._feature_cards: list[DashboardFeatureCard] = []
        for i, (title, desc, icon) in enumerate(_features):
            card = DashboardFeatureCard(title, desc, icon, self)
            self._feature_cards.append(card)
            grid.addWidget(card, i // 2, i % 2)

        layout.addLayout(grid)

    def changeEvent(self, event) -> None:  # type: ignore[override]
        from PyQt5.QtCore import QEvent
        super().changeEvent(event)
        if event.type() == QEvent.LanguageChange:
            self._retranslate_ui()

    def _retranslate_ui(self) -> None:
        self._section_lbl.setText(self.tr("Included Tools & Features"))
        _texts = (
            (self.tr("Multi-Source Support"),
             self.tr("1000+ sites: YouTube, TikTok, Pinterest & more.")),
            (self.tr("Quality Selector"),
             self.tr("Pick 4K, 1080p, 720p or audio-only (MP3/M4A).")),
            (self.tr("Batch Download"),
             self.tr("Paste multiple URLs or an entire playlist.")),
            (self.tr("Smart File Naming"),
             self.tr("Files saved by title/channel automatically.")),
        )
        for card, (title, desc) in zip(self._feature_cards, _texts):
            card.set_texts(title, desc)
