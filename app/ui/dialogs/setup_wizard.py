"""First-run setup wizard: theme and download path."""

from PyQt5.QtWidgets import (
    QDialog,
    QFileDialog,
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
    LineEdit,
    PrimaryPushButton,
    PushButton,
    TitleLabel,
)

from app.common.paths import get_default_downloads_dir
from app.config import save_settings

_THEME_OPTIONS = ["Auto", "Light", "Dark"]


class SetupWizardDialog(QDialog):
    """First-run setup: choose theme and download folder, then save and continue."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Welcome to VOK")
        self.setMinimumSize(500, 340)
        self.setMinimumWidth(480)
        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(16)
        lay.setContentsMargins(24, 24, 24, 24)

        # Header
        title = TitleLabel("Setup", self)
        lay.addWidget(title)
        subtitle = BodyLabel("Set your preferences before you start.", self)
        subtitle.setWordWrap(True)
        lay.addWidget(subtitle)
        lay.addSpacing(8)

        # Form
        form = QWidget()
        form_lay = QFormLayout(form)
        form_lay.setSpacing(12)

        # Theme
        theme_label = BodyLabel("Theme", self)
        theme_label.setToolTip("Appearance: automatic (follow system), light, or dark.")
        self._theme_combo = ComboBox(self)
        self._theme_combo.addItems(_THEME_OPTIONS)
        self._theme_combo.setCurrentText("Dark")
        self._theme_combo.setMinimumWidth(160)
        self._theme_combo.setToolTip("Choose Auto, Light, or Dark.")
        form_lay.addRow(theme_label, self._theme_combo)

        # Download folder
        path_label = BodyLabel("Download folder", self)
        path_label.setToolTip("Videos and files will be saved to this folder.")
        path_row = QHBoxLayout()
        path_row.setSpacing(8)
        self._path_edit = LineEdit(self)
        self._path_edit.setPlaceholderText(str(get_default_downloads_dir()))
        self._path_edit.setText(str(get_default_downloads_dir()))
        self._path_edit.setMinimumWidth(200)
        self._path_edit.setToolTip("Choose where to save downloaded videos.")
        self._path_edit.setClearButtonEnabled(True)
        browse = PushButton("Browse…", self)
        browse.setMinimumWidth(90)
        browse.clicked.connect(self._browse)
        path_row.addWidget(self._path_edit, 1)
        path_row.addWidget(browse, 0)
        form_lay.addRow(path_label, path_row)

        lay.addWidget(form)
        path_hint = BodyLabel("Videos will be saved here.", self)
        lay.addWidget(path_hint)

        # Bottom buttons
        lay.addSpacerItem(QSpacerItem(0, 20, QSizePolicy.Minimum, QSizePolicy.Fixed))
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        skip_btn = PushButton("Skip", self)
        skip_btn.setMinimumWidth(88)
        skip_btn.clicked.connect(self._on_skip)
        skip_btn.setToolTip("Use default settings and continue.")
        finish_btn = PrimaryPushButton("Finish", self)
        finish_btn.setMinimumWidth(88)
        finish_btn.clicked.connect(self._on_finish)
        finish_btn.setToolTip("Save your choices and start using VOK.")
        btn_row.addSpacing(12)
        btn_row.addWidget(skip_btn)
        btn_row.addWidget(finish_btn)
        lay.addLayout(btn_row)

    def _browse(self):
        start = self._path_edit.text() or str(get_default_downloads_dir())
        path = QFileDialog.getExistingDirectory(self, "Download folder", start)
        if path:
            self._path_edit.setText(path)

    def _save_and_close(self, path: str, theme: str):
        save_settings({
            "download_path": path,
            "theme": theme,
            "single_video_default": True,
            "theme_color": "#0078D4",
            "concurrent_downloads": 2,
            "concurrent_fragments": 4,
            "cookies_file": "",
        })

    def _on_skip(self):
        self._save_and_close(str(get_default_downloads_dir()), "Dark")
        self.accept()

    def _on_finish(self):
        path = self._path_edit.text().strip() or str(get_default_downloads_dir())
        self._save_and_close(path, self._theme_combo.currentText())
        self.accept()
