"""Uninstall flow: open feedback URL, ask theme, then remove config and quit."""

import webbrowser

from PyQt5.QtWidgets import QDialog, QFormLayout, QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel,
    ComboBox,
    PrimaryPushButton,
    PushButton,
    TitleLabel,
)

from app.common.paths import get_config_dir
from app.config import get_settings_path

# Optional: replace with your feedback/survey URL
UNINSTALL_FEEDBACK_URL = "https://github.com"


class UninstallDialog(QDialog):
    """Ask theme, open feedback URL, then confirm before removing app data and quitting."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Remove VOK data")
        self.setFixedSize(460, 320)
        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.addWidget(TitleLabel("Remove app data", self))
        lay.addWidget(BodyLabel(
            "Before removing your data, we'd like your feedback (optional). "
            "A webpage will open where you can tell us why you're leaving.",
            self,
        ))
        lay.addSpacing(12)

        form = QWidget()
        form_lay = QFormLayout(form)
        form_lay.addRow(BodyLabel("Which theme did you prefer?", self))
        self._theme_combo = ComboBox(self)
        self._theme_combo.addItems(["Auto", "Light", "Dark", "Skip"])
        self._theme_combo.setCurrentText("Skip")
        self._theme_combo.setFixedWidth(120)
        form_lay.addRow(self._theme_combo)
        lay.addWidget(form)

        lay.addWidget(BodyLabel(
            "This will delete your settings and any stored data. The app will then quit.",
            self,
        ))
        lay.addStretch(1)
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        cancel_btn = PushButton("Cancel", self)
        cancel_btn.clicked.connect(self.reject)
        remove_btn = PrimaryPushButton("Open feedback & remove data", self)
        remove_btn.clicked.connect(self._on_remove)
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
