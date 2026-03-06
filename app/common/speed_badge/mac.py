# coding: utf-8
from PyQt5.QtCore import QObject
from Foundation import NSObject, NSAutoreleasePool
from AppKit import NSApp, NSApplication, NSImage, NSString, NSFont, NSColor


class MacSpeedBadge(QObject):

    def __init__(self, parent=None):
        super().__init__(parent)

    def setSpeed(self, speed: str):
        tile = NSApp().dockTile()
        tile.setBadgeLabel_(speed)
        tile.display()

    def hide(self):
        NSApp().dockTile().setBadgeLabel_(None)
