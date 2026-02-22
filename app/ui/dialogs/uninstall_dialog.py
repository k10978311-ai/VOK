"""Uninstall flow: open feedback URL, ask theme, then remove config and quit."""

import webbrowser

from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    BodyLabel,
    ComboBox,
    PrimaryPushButton,
    PushButton,
    Theme,
    TitleLabel,
    setTheme,
    setThemeColor,
)

from app.common.paths import get_config_dir
from app.config import get_settings_path, load_settings

# Optional: replace with your feedback/survey URL
UNINSTALL_FEEDBACK_URL = "https://github.com"

_THEME_MAP = {"Auto": Theme.AUTO, "Light": Theme.LIGHT, "Dark": Theme.DARK}


class UninstallDialog(QDialog):
    """Ask theme, open feedback URL, then confirm before removing app data and quitting."""

    def __init__(self, parent=None):
        super().__init__(parent)
        # Use light theme for this dialog: light background, dark text
        s = load_settings()
        self._prev_theme = s.get("theme", "Dark")
        self._prev_color = QColor(s.get("theme_color", "#0078D4"))
        setTheme(Theme.LIGHT)
        setThemeColor(QColor("#0078D4"))
        self.finished.connect(self._restore_theme)
        self.setWindowTitle("Remove VOK data")
        self.setMinimumSize(460, 320)
        self.setMinimumWidth(480)
        self._build_ui()

    def _restore_theme(self) -> None:
        """Restore app theme when dialog closes (e.g. if user cancels)."""
        setTheme(_THEME_MAP.get(self._prev_theme, Theme.DARK))
        setThemeColor(self._prev_color)

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(16)
        lay.setContentsMargins(24, 24, 24, 24)

        lay.addWidget(TitleLabel("Remove app data", self))
        lay.addWidget(BodyLabel(
            "Before removing your data, we'd like your feedback (optional). "
            "A webpage will open where you can tell us why you're leaving.",
            self,
        ))
        lay.addSpacing(8)

        form = QWidget()
        form_lay = QFormLayout(form)
        form_lay.setSpacing(12)
        self._theme_combo = ComboBox(self)
        self._theme_combo.addItems(["Auto", "Light", "Dark", "Skip"])
        self._theme_combo.setCurrentText("Skip")
        self._theme_combo.setMinimumWidth(160)
        form_lay.addRow(BodyLabel("Which theme did you prefer?", self), self._theme_combo)
        lay.addWidget(form)

        lay.addWidget(BodyLabel(
            "This will delete your settings and any stored data. The app will then quit.",
            self,
        ))
        lay.addSpacerItem(QSpacerItem(0, 20, QSizePolicy.Minimum, QSizePolicy.Fixed))
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        cancel_btn = PushButton("Cancel", self)
        cancel_btn.setMinimumWidth(88)
        cancel_btn.clicked.connect(self.reject)
        remove_btn = PrimaryPushButton("Open feedback & remove data", self)
        remove_btn.setMinimumWidth(88)
        remove_btn.clicked.connect(self._on_remove)
        btn_row.addSpacing(12)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(remove_btn)
        lay.addLayout(btn_row)

    def _on_remove(self):
        try:
            webbrowser.open(UNINSTALL_FEEDBACK_URL)
        except Exception:
            pass
        self._remove_config_and_quit()

    def _remove_config_and_quit(self):
        path = get_settings_path()
        try:
            if path.exists():
                path.unlink()
        except OSError:
            pass
        config_dir = get_config_dir()
        try:
            if config_dir.exists() and not any(config_dir.iterdir()):
                config_dir.rmdir()
        except OSError:
            pass
        self.accept()
        from PyQt5.QtWidgets import QApplication
        QApplication.quit()
