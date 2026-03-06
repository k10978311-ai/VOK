# coding: utf-8
from PyQt5.QtCore import QObject


class WindowsSpeedBadge(QObject):

    def __init__(self, parent=None):
        super().__init__(parent)

    def setSpeed(self, speed: str):
        pass

    def hide(self):
        pass
