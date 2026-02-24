"""Apply theme and palette so Fusion style and Qt widgets match light/dark and accent."""

from PyQt5.QtGui import QColor, QPalette
from PyQt5.QtWidgets import QApplication


def apply_app_palette(theme_name: str, accent_hex: str = "#0078D4") -> None:
    """Set QApplication palette so Fusion-style widgets (e.g. QTableWidget) match the theme.

    Call after setTheme/setThemeColor. theme_name: 'Auto', 'Light', or 'Dark'.
    """
    app = QApplication.instance()
    if not app:
        return
    try:
        accent = QColor(accent_hex) if accent_hex else QColor("#0078D4")
        if not accent.isValid():
            accent = QColor("#0078D4")
    except Exception:
        accent = QColor("#0078D4")

    is_dark = theme_name == "Dark"
    if theme_name == "Auto":
        is_dark = True  # Default to dark; Fusion has no system theme detection here

    pal = QPalette()
    if is_dark:
        # Dark theme: dark backgrounds, light text
        pal.setColor(QPalette.Window, QColor(53, 53, 53))
        pal.setColor(QPalette.WindowText, QColor(240, 240, 240))
        pal.setColor(QPalette.Base, QColor(42, 42, 42))
        pal.setColor(QPalette.AlternateBase, QColor(45, 45, 45))
        pal.setColor(QPalette.Text, QColor(240, 240, 240))
        pal.setColor(QPalette.Button, QColor(53, 53, 53))
        pal.setColor(QPalette.ButtonText, QColor(240, 240, 240))
        pal.setColor(QPalette.Highlight, accent)
        pal.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
        pal.setColor(QPalette.Link, accent)
        pal.setColor(QPalette.PlaceholderText, QColor(140, 140, 140))
    else:
        # Light theme
        pal.setColor(QPalette.Window, QColor(240, 240, 240))
        pal.setColor(QPalette.WindowText, QColor(0, 0, 0))
        pal.setColor(QPalette.Base, QColor(255, 255, 255))
        pal.setColor(QPalette.AlternateBase, QColor(248, 248, 248))
        pal.setColor(QPalette.Text, QColor(0, 0, 0))
        pal.setColor(QPalette.Button, QColor(240, 240, 240))
        pal.setColor(QPalette.ButtonText, QColor(0, 0, 0))
        pal.setColor(QPalette.Highlight, accent)
        pal.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
        pal.setColor(QPalette.Link, accent)
        pal.setColor(QPalette.PlaceholderText, QColor(120, 120, 120))

    app.setPalette(pal)
