# coding: utf-8
from PyQt5.QtWidgets import QApplication, QSystemTrayIcon

from qfluentwidgets import Action, SystemTrayMenu

from app.common.signal_bus import signal_bus


class SystemTrayIcon(QSystemTrayIcon):
    """System tray icon with show/exit actions."""

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        if parent is not None:
            self.setIcon(parent.windowIcon())
        self.menu = SystemTrayMenu(parent=parent)
        self.menu.addActions([
            Action(
                self.tr("Show panel"),
                triggered=self._on_show_panel,
            ),
            Action(
                self.tr("Exit"),
                triggered=self._on_exit,
            ),
        ])
        self.setContextMenu(self.menu)

    def _on_show_panel(self):
        signal_bus.app_message.emit("show")
        w = self.parent().window() if self.parent() else None
        if w:
            w.showNormal()
            w.raise_()
            w.activateWindow()
    
    def _on_exit(self):
        """Request application exit using the main window's exit handler."""
        w = self.parent().window() if self.parent() else None
        
        if w and hasattr(w, 'exit_handler') and w.exit_handler:
            # Use the organized exit handler with confirmation
            w.exit_handler.request_exit_with_confirmation(w, "system_tray_exit")
        elif w and hasattr(w, 'onExit'):
            # Fallback to main window's onExit method
            w.onExit()
        else:
            # Last resort fallback
            QApplication.instance().quit()
