"""Dashboard 'How to use' card: steps list and optional instruction images."""

from __future__ import annotations

from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QLabel, QVBoxLayout
from qfluentwidgets import BodyLabel, CardWidget, SubtitleLabel

from app.common.paths import INSTRUCTIONS_DIR


STEP_SPACING = 4
LAYOUT_SPACING = 12
LAYOUT_MARGINS = (20, 18, 20, 18)
IMAGE_MAX_WIDTH = 560

DEFAULT_STEPS = (
    "1. Copy a video URL from your browser.",
    "2. Go to the Download tab, paste the URL, and choose your format.",
    "3. Click Download — track progress in the Logs tab.",
)


class DashboardInstructionsCard(CardWidget):
    """Card showing how-to steps and optional images from resources/instructions/."""

    def __init__(
        self,
        title: str | None = None,
        steps: tuple[str, ...] | None = None,
        instructions_dir: Path | None = INSTRUCTIONS_DIR,
        parent=None,
    ):
        super().__init__(parent)
        self.setObjectName("DashboardInstructionsCard")
        self._instructions_dir = instructions_dir or INSTRUCTIONS_DIR

        _title = title or self.tr("How to use")
        _steps = steps or (
            self.tr("1. Copy a video URL from your browser."),
            self.tr("2. Go to the Download tab, paste the URL, and choose your format."),
            self.tr("3. Click Download — track progress in the Logs tab."),
        )

        layout = QVBoxLayout(self)
        layout.setSpacing(LAYOUT_SPACING)
        layout.setContentsMargins(*LAYOUT_MARGINS)

        self._title_lbl = SubtitleLabel(_title, self)
        layout.addWidget(self._title_lbl)
        layout.addSpacing(STEP_SPACING)

        self._step_labels: list[BodyLabel] = []
        for text in _steps:
            lbl = BodyLabel(text, self)
            lbl.setWordWrap(True)
            layout.addWidget(lbl)
            self._step_labels.append(lbl)

        if self._instructions_dir.exists():
            self._add_instruction_images(layout)

    def changeEvent(self, event) -> None:  # type: ignore[override]
        from PyQt5.QtCore import QEvent
        super().changeEvent(event)
        if event.type() == QEvent.LanguageChange:
            self._retranslate_ui()

    def _retranslate_ui(self) -> None:
        self._title_lbl.setText(self.tr("How to use"))
        _steps = (
            self.tr("1. Copy a video URL from your browser."),
            self.tr("2. Go to the Download tab, paste the URL, and choose your format."),
            self.tr("3. Click Download — track progress in the Logs tab."),
        )
        for lbl, text in zip(self._step_labels, _steps):
            lbl.setText(text)

    def _add_instruction_images(self, layout: QVBoxLayout) -> None:
        """Append instruction images (step1.png, step2.png, …) from instructions dir."""
        for i in range(1, 10):
            for ext in (".png", ".jpg", ".jpeg"):
                path = self._instructions_dir / f"step{i}{ext}"
                if path.exists():
                    pix = QPixmap(str(path))
                    if not pix.isNull():
                        label = QLabel(self)
                        label.setPixmap(
                            pix.scaledToWidth(IMAGE_MAX_WIDTH, Qt.SmoothTransformation)
                        )
                        label.setAlignment(Qt.AlignCenter)
                        layout.addWidget(label)
                    break
