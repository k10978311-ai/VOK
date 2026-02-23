"""Base view for FluentWindow sub-interfaces."""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QFrame, QVBoxLayout, QWidget
from qfluentwidgets import ScrollArea


class BaseView(ScrollArea):
    """Scrollable view used as a FluentWindow sub-interface.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName(self.__class__.__name__)
        self.setFrameShape(QFrame.NoFrame)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self._container = QWidget()
        self._container.setObjectName(f"{self.__class__.__name__}Container")
        self._layout = QVBoxLayout(self._container)
        self._layout.setContentsMargins(24, 24, 24, 24)
        self._layout.setSpacing(16)
        self.setWidget(self._container)

        # Keep both layers transparent — theme engine owns the background colour.
        self.setStyleSheet("QScrollArea, QWidget#{}Container {{ background: transparent; border: none; }}".format(
            self.__class__.__name__
        ))
