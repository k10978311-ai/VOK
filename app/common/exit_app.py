"""
Application Exit Handler - Centralized cleanup and termination logic.

This module provides a clean, organized way to handle application exit with
proper resource cleanup, confirmation dialogs, and graceful shutdown.
"""

import sys
import threading
import time
from typing import Optional, TYPE_CHECKING

from PyQt5.QtCore import QThread
from PyQt5.QtWidgets import QApplication
from PyQt5.QtSql import QSqlDatabase
from qfluentwidgets import MessageBox

from app.common.logger import Logger

if TYPE_CHECKING:
    from app.ui.main_window import MainWindow


class ExitHandler:
    """Centralized application exit handler with cleanup management."""
    
    def __init__(self, main_window: 'MainWindow'):
        self.main_window = main_window
        self.logger = Logger("exit_handler")
        self._shutdown_in_progress = False
    
    def request_exit_with_confirmation(self, parent=None, reason: str = "user_request") -> bool:
        """
        Show confirmation dialog and exit if user confirms.
        
        Args:
            parent: Parent widget for the dialog
            reason: Reason for the exit request (for logging)
            
        Returns:
            bool: True if user confirmed and exit initiated, False if cancelled
        """
        if self._shutdown_in_progress:
            self.logger.info("Exit already in progress, ignoring request")
            return True
            
        self.logger.info(f"Exit confirmation requested: {reason}")
        
        # Use main window as default parent
        dialog_parent = parent or self.main_window
        
        reply = MessageBox(
            "Exit Application", 
            "Are you sure you want to exit VOK completely?\n\n"
            "This will close all downloads and background processes.",
            dialog_parent
        )
        reply.yesButton.setText("Exit")
        reply.cancelButton.setText("Cancel")
        
        if reply.exec() == MessageBox.MessageBoxAction.Yes:
            self.logger.info("User confirmed application exit")
            self.perform_exit()
            return True
        else:
            self.logger.info("User cancelled exit")
            return False
    
    def perform_exit(self, force: bool = False):
        """
        Perform application exit with full cleanup.
        
        Args:
            force: If True, skip confirmation dialogs
        """
        if self._shutdown_in_progress:
            self.logger.info("Shutdown already in progress")
            return
            
        self._shutdown_in_progress = True
        self.logger.info("Application shutdown initiated")
        
        try:
            # Hide system tray icon first
            self._hide_system_tray()
            
            # Stop and clean up database thread
            self._cleanup_database_thread()
            
            # Clean up all background threads
            self._cleanup_background_threads()
            
            # Disconnect all signal connections
            self._disconnect_signals()
            
            # Close database connection
            self._cleanup_database()
            
            self.logger.info("Application cleanup completed successfully")
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
        
        finally:
            # Ensure application terminates
            self._force_application_exit()
    
    def _hide_system_tray(self):
        """Hide the system tray icon."""
        try:
            if hasattr(self.main_window, 'systemTrayIcon'):
                self.main_window.systemTrayIcon.hide()
                self.logger.info("System tray icon hidden")
        except Exception as e:
            self.logger.error(f"Error hiding system tray: {e}")
    
    def _cleanup_database_thread(self):
        """Safely stop and clean up the database thread."""
        try:
            if not hasattr(self.main_window, 'databaseThread'):
                return
                
            thread = self.main_window.databaseThread
            
            # Use graceful shutdown if available
            if hasattr(thread, 'stop_gracefully'):
                self.logger.info("Requesting graceful database thread shutdown...")
                thread.stop_gracefully()
            
            if thread.isRunning():
                # Wait for current operation to finish
                if not thread.wait(3000):  # 3 second timeout
                    self.logger.warning("Database thread didn't stop gracefully, terminating...")
                    thread.terminate()
                    thread.wait(1000)
                else:
                    self.logger.info("Database thread stopped gracefully")
                    
        except Exception as e:
            self.logger.error(f"Error cleaning up database thread: {e}")
    
    def _cleanup_background_threads(self):
        """Find and stop all background QThread workers."""
        try:
            views = []
            for attr_name in ['dashboard', 'downloader', 'taskInterface', 'settings']:
                if hasattr(self.main_window, attr_name):
                    views.append(getattr(self.main_window, attr_name))
            
            for view in views:
                # Call view-specific cleanup if available
                if hasattr(view, '_stop_background_threads'):
                    view._stop_background_threads()
                
                # Check for any QThread attributes and stop them
                for attr_name in dir(view):
                    try:
                        attr = getattr(view, attr_name)
                        if isinstance(attr, QThread) and attr.isRunning():
                            self.logger.info(f"Stopping thread: {attr_name}")
                            attr.quit()
                            if not attr.wait(2000):  # 2 second timeout
                                self.logger.warning(f"Thread {attr_name} didn't stop gracefully, terminating...")
                                attr.terminate()
                                attr.wait(1000)
                    except (AttributeError, RuntimeError):
                        # Ignore attribute errors or runtime errors from deleted objects
                        continue
                        
            self.logger.info("Background thread cleanup completed")
                        
        except Exception as e:
            self.logger.error(f"Error cleaning up background threads: {e}")
    
    def _disconnect_signals(self):
        """Disconnect all signal connections to prevent crashes during cleanup."""
        try:
            from app.common.signal_bus import signal_bus
            from app.common.database import sqlSignalBus
            
            # Disconnect specific signal bus connections
            connections_to_disconnect = [
                (signal_bus.app_message, 'onAppMessage'),
                (signal_bus.app_error, 'onAppError'),
            ]
            
            # Add database signal if thread exists
            if hasattr(self.main_window, 'databaseThread'):
                connections_to_disconnect.append((sqlSignalBus.dataFetched, 'onDataFetched'))
            
            for signal, slot_name in connections_to_disconnect:
                try:
                    slot_method = getattr(self.main_window, slot_name, None)
                    if slot_method:
                        signal.disconnect(slot_method)
                except TypeError:
                    # Connection doesn't exist - this is normal
                    pass
                except Exception as e:
                    self.logger.warning(f"Error disconnecting {slot_name}: {e}")
                    
            self.logger.info("Signal disconnections completed")
                
        except Exception as e:
            self.logger.error(f"Error disconnecting signals: {e}")
    
    def _cleanup_database(self):
        """Close database connection and remove it."""
        try:
            from app.common.database import DBInitializer
            
            db = QSqlDatabase.database(DBInitializer.CONNECTION_NAME)
            if db.isOpen():
                db.close()
                self.logger.info("Database connection closed")
                
            QSqlDatabase.removeDatabase(DBInitializer.CONNECTION_NAME)
            self.logger.info("Database removed")
            
        except Exception as e:
            self.logger.error(f"Error cleaning up database: {e}")
    
    def _force_application_exit(self):
        """Ensure the application quits, with fallback to force exit."""
        self.logger.info("Initiating application shutdown...")
        
        # First try normal quit
        app = QApplication.instance()
        if app:
            app.quit()
            
            # Process any remaining events
            app.processEvents()
            
            # Start force exit timer in background
            def force_exit_timer():
                time.sleep(2)  # Wait 2 seconds
                if app and not app.closingDown():
                    self.logger.warning("Force exiting application...")
                    sys.exit(0)
            
            force_thread = threading.Thread(target=force_exit_timer, daemon=True)
            force_thread.start()
        else:
            # No QApplication instance, exit directly
            sys.exit(0)


# Convenience functions for global access
_exit_handler: Optional[ExitHandler] = None


def initialize_exit_handler(main_window: 'MainWindow'):
    """Initialize the global exit handler."""
    global _exit_handler
    _exit_handler = ExitHandler(main_window)


def request_exit_with_confirmation(parent=None, reason: str = "user_request") -> bool:
    """Request application exit with user confirmation."""
    if _exit_handler:
        return _exit_handler.request_exit_with_confirmation(parent, reason)
    else:
        # Fallback if not initialized
        QApplication.instance().quit()
        return True


def force_exit(reason: str = "forced"):
    """Force application exit without confirmation."""
    if _exit_handler:
        Logger("exit_app").info(f"Force exit requested: {reason}")
        _exit_handler.perform_exit(force=True)
    else:
        # Fallback
        sys.exit(0)
