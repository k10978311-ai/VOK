from __future__ import annotations

from qfluentwidgets import (
    MessageBoxBase,
    ScrollArea,
    SubtitleLabel,
)

from app.ui.components import DownloadEnhanceFeature


class EnhanceSettingDialog(MessageBoxBase):
    """Modal dialog for configuring enhance (stream-edit) options."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()
        self.yesButton.setText(self.tr("Done"))
        self.cancelButton.hide()
        self.widget.setMinimumWidth(700)

    # ── Build ──────────────────────────────────────────────────────────────

    def _build(self) -> None:
        self.viewLayout.addWidget(SubtitleLabel(self.tr("Enhance Settings"), self))
        self.viewLayout.setSpacing(8)

        scroll = ScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(ScrollArea.NoFrame)
        scroll.setMinimumHeight(500)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }"
                             "QScrollArea > QWidget > QWidget { background: transparent; }")

        self._feature = DownloadEnhanceFeature()
        self._feature.setContentsMargins(4, 4, 4, 4)
        # Hide the URL input card (first widget) — not needed inside this dialog
        first = self._feature.layout().itemAt(0).widget()
        if first is not None:
            first.setVisible(False)

        scroll.setWidget(self._feature)
        self.viewLayout.addWidget(scroll)
