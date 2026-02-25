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
        section_title: str = "Included Tools & Features",
        features: tuple[tuple[str, str, object], ...] = DEFAULT_FEATURES,
        parent=None,
    ):
        super().__init__(parent)
        self.setObjectName("DashboardFeatureGrid")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(SubtitleLabel(section_title, self))

        grid = QGridLayout()
        grid.setContentsMargins(GRID_MARGINS, GRID_MARGINS, GRID_MARGINS, GRID_MARGINS)
        grid.setSpacing(GRID_SPACING)

        for i, (title, desc, icon) in enumerate(features):
            grid.addWidget(
                DashboardFeatureCard(title, desc, icon, self),
                i // 2,
                i % 2,
            )

        layout.addLayout(grid)
