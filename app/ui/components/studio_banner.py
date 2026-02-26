"""FeatureTile — vertical gallery-style clickable card used in banner components."""

from __future__ import annotations

from PyQt5.QtCore import QPoint, QRect, QRectF, Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QPainter, QPainterPath, QPixmap
from PyQt5.QtWidgets import (
    QGraphicsBlurEffect,
    QGraphicsScene,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    CaptionLabel,
    FluentIcon,
    IconWidget,
    SubtitleLabel,
    isDarkTheme,
    qconfig,
)


class FeatureTile(QWidget):
    """Vertical gallery tile: large icon, title, description, link arrow."""

    clicked = pyqtSignal()

    # hover/press overlay alphas — separate for dark / light (painted, not stylesheet)
    _DARK_OVERLAY_NORMAL   = 18
    _DARK_OVERLAY_HOVER    = 45
    _DARK_OVERLAY_PRESSED  = 8
    _LIGHT_OVERLAY_NORMAL  = 22
    _LIGHT_OVERLAY_HOVER   = 55
    _LIGHT_OVERLAY_PRESSED = 10
    _BLUR_RADIUS           = 20

    def __init__(
        self,
        icon: FluentIcon,
        title: str,
        subtitle: str = "",
        parent=None,
    ):
        super().__init__(parent)
        self.setFixedSize(168, 118)
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._overlay_alpha = self._DARK_OVERLAY_NORMAL
        self._bg_cache: QPixmap | None = None
        self._icon_w: IconWidget | None = None
        self._arrow_w: IconWidget | None = None
        self._title_lbl: SubtitleLabel | None = None
        self._desc_lbl: CaptionLabel | None = None
        self._build(icon, title, subtitle)
        qconfig.themeChanged.connect(self._on_theme_changed)

    def _build(self, icon: FluentIcon, title: str, subtitle: str):
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(6)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(0)

        self._icon_w = IconWidget(icon, self)
        self._icon_w.setFixedSize(36, 36)
        top_row.addWidget(self._icon_w)

        top_row.addStretch(1)

        self._arrow_w = IconWidget(FluentIcon.LINK, self)
        self._arrow_w.setFixedSize(14, 14)
        top_row.addWidget(self._arrow_w, 0, Qt.AlignTop)

        root.addLayout(top_row)
        root.addSpacing(8)

        # title
        self._title_lbl = SubtitleLabel(title, self)
        self._title_lbl.setStyleSheet(
            "font-size: 13px; font-weight: 600;"
            " background: transparent; padding: 0;"
        )
        self._title_lbl.setWordWrap(True)
        root.addWidget(self._title_lbl)

        # description
        if subtitle:
            self._desc_lbl = CaptionLabel(subtitle, self)
            self._desc_lbl.setStyleSheet(
                "font-size: 11px; background: transparent; padding: 0;"
            )
            self._desc_lbl.setWordWrap(True)
            root.addWidget(self._desc_lbl)

        root.addStretch(1)
        self._update_colors()

    def _on_theme_changed(self, _theme=None) -> None:
        self._update_colors()
        self._bg_cache = None
        self.update()

    def _update_colors(self) -> None:
        dark = isDarkTheme()
        icon_color  = "white" if dark else "#1a1a1a"
        title_color = "white" if dark else "#1a1a1a"
        desc_color  = "rgba(255,255,255,0.60)" if dark else "rgba(20,20,20,0.55)"
        self._overlay_alpha = (
            self._DARK_OVERLAY_NORMAL if dark else self._LIGHT_OVERLAY_NORMAL
        )
        if self._icon_w:
            self._icon_w.setStyleSheet(f"color: {icon_color};")
        if self._arrow_w:
            self._arrow_w.setStyleSheet(f"color: {icon_color};")
        if self._title_lbl:
            self._title_lbl.setTextColor(
                QColor("#1a1a1a"), QColor("white")
            )
            self._title_lbl.setStyleSheet(
                f"color: {title_color}; font-size: 13px; font-weight: 600;"
                " background: transparent; padding: 0;"
            )
        if self._desc_lbl:
            self._desc_lbl.setTextColor(
                QColor(20, 20, 20, 140), QColor(255, 255, 255, 153)
            )
            self._desc_lbl.setStyleSheet(
                f"color: {desc_color}; font-size: 11px;"
                " background: transparent; padding: 0;"
            )

    def showEvent(self, event):
        super().showEvent(event)
        # QTimer.singleShot(0, self._cache_background)

    def _cache_background(self):
        """Grab and blur the parent region once; called deferred after show."""
        if not self.parent() or not self.isVisible():
            return
        pos = self.mapTo(self.parent(), QPoint(0, 0))
        raw = self.parent().grab(QRect(pos, self.size()))
        self._bg_cache = self._blur_pixmap(raw, self._BLUR_RADIUS)
        self.update()
    @staticmethod
    def _blur_pixmap(pixmap: QPixmap, radius: int) -> QPixmap:
        """Return a blurred copy of *pixmap* using QGraphicsBlurEffect."""
        scene = QGraphicsScene()
        item = scene.addPixmap(pixmap)
        effect = QGraphicsBlurEffect()
        effect.setBlurRadius(radius)
        effect.setBlurHints(QGraphicsBlurEffect.QualityHint)
        item.setGraphicsEffect(effect)

        result = QPixmap(pixmap.size())
        result.fill(Qt.transparent)
        p = QPainter(result)
        scene.render(p, source=QRectF(item.boundingRect()))
        p.end()
        return result

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 10, 10)
        painter.setClipPath(path)

        if self._bg_cache:
            painter.drawPixmap(0, 0, self._bg_cache)

        overlay_color = (
            QColor(255, 255, 255, self._overlay_alpha)
            if isDarkTheme()
            else QColor(0, 0, 0, self._overlay_alpha)
        )
        painter.fillPath(path, overlay_color)

        painter.end()

    def _set_overlay(self, alpha: int):
        self._overlay_alpha = alpha
        self.update()

    def _normal_alpha(self) -> int:
        return self._DARK_OVERLAY_NORMAL if isDarkTheme() else self._LIGHT_OVERLAY_NORMAL

    def _hover_alpha(self) -> int:
        return self._DARK_OVERLAY_HOVER if isDarkTheme() else self._LIGHT_OVERLAY_HOVER

    def _pressed_alpha(self) -> int:
        return self._DARK_OVERLAY_PRESSED if isDarkTheme() else self._LIGHT_OVERLAY_PRESSED

    def enterEvent(self, event):
        self._set_overlay(self._hover_alpha())
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._set_overlay(self._normal_alpha())
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._set_overlay(self._pressed_alpha())
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._set_overlay(self._hover_alpha() if self.underMouse() else self._normal_alpha())
            if self.rect().contains(event.pos()):
                self.clicked.emit()
        super().mouseReleaseEvent(event)
