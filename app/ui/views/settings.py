"""Settings view: Fluent UI setting cards."""

import webbrowser

import app
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QColorDialog, QFileDialog, QHBoxLayout, QMessageBox

from qfluentwidgets import (
    ComboBox,
    FluentIcon,
    InfoBar,
    InfoBarPosition,
    LargeTitleLabel,
    LineEdit,
    PrimaryPushButton,
    PushButton,
    SegmentedWidget,
    SettingCard,
    SettingCardGroup,
    SwitchButton,
    setTheme,
    setThemeColor,
    Theme,
)

from app.common.paths import get_default_downloads_dir
from app.common.state import add_log_entry
from app.config import get_default_settings, load_settings, save_settings
from app.core.updater import check_update, download_update, install_update
from app.ui.theme import apply_app_palette

from .base import BaseView

_THEME_MAP = {"Auto": Theme.AUTO, "Light": Theme.LIGHT, "Dark": Theme.DARK}


class UpdateCheckWorker(QThread):
    """Check GitHub Releases for a newer version."""
    result_ready = pyqtSignal(object, object)  # (version or None, download_url or None)

    def run(self):
        version, url = check_update(app.__version__)
        self.result_ready.emit(version, url)


class UpdateDownloadWorker(QThread):
    """Download the update installer to TEMP."""
    progress_signal = pyqtSignal(int, int)  # current, total (0 if unknown)
    done_signal = pyqtSignal(str)  # path
    failed_signal = pyqtSignal()

    def __init__(self, url: str, parent=None):
        super().__init__(parent)
        self._url = url

    def run(self):
        def progress(current, total):
            self.progress_signal.emit(current, total or 0)
        path = download_update(self._url, progress_callback=progress)
        if path:
            self.done_signal.emit(path)
        else:
            self.failed_signal.emit()


class SettingsView(BaseView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")

        title = LargeTitleLabel(self)
        title.setText("Settings")
        self._layout.addWidget(title)
        self._layout.addSpacing(4)

        # ── Download group ────────────────────────────────────────────────
        dl_group = SettingCardGroup("Download", self)

        path_card = SettingCard(
            FluentIcon.FOLDER,
            "Download path",
            "Folder where downloaded files are saved",
        )
        self._path_edit = LineEdit()
        self._path_edit.setMinimumWidth(240)
        self._path_edit.setPlaceholderText(str(get_default_downloads_dir()))
        browse_btn = PushButton("Browse…")
        browse_btn.clicked.connect(self._browse_path)
        path_card.hBoxLayout.addWidget(self._path_edit)
        path_card.hBoxLayout.addWidget(browse_btn)
        path_card.hBoxLayout.addSpacing(16)
        dl_group.addSettingCard(path_card)

        single_card = SettingCard(
            FluentIcon.VIDEO,
            "Single video only (no playlists)",
            "Download only the current video; skip playlists when a single URL is used.",
        )
        self._single_switch = SwitchButton()
        single_card.hBoxLayout.addWidget(self._single_switch)
        single_card.hBoxLayout.addSpacing(16)
        dl_group.addSettingCard(single_card)

        mode_card = SettingCard(
            FluentIcon.DOWNLOAD,
            "Download mode",
            "Normal or enhanced download.",
        )
        self._mode_segmented = SegmentedWidget()
        self._mode_segmented.insertItem(0, "normal", "Normal", None)
        self._mode_segmented.insertItem(1, "enhance", "Enhance", self._on_enhance_mode_clicked)
        self._mode_segmented.setCurrentItem("normal")
        mode_card.hBoxLayout.addWidget(self._mode_segmented)
        mode_card.hBoxLayout.addSpacing(16)
        dl_group.addSettingCard(mode_card)

        sound_complete_card = SettingCard(
            FluentIcon.MUSIC,
            "Sound alert on completed download",
            "Play a sound when a download finishes successfully.",
        )
        self._sound_complete_switch = SwitchButton()
        self._sound_complete_switch.setChecked(True)
        sound_complete_card.hBoxLayout.addWidget(self._sound_complete_switch)
        sound_complete_card.hBoxLayout.addSpacing(16)
        dl_group.addSettingCard(sound_complete_card)

        sound_error_card = SettingCard(
            FluentIcon.IOT,
            "Sound alert on download error",
            "Play a sound when a download fails or is skipped.",
        )
        self._sound_error_switch = SwitchButton()
        self._sound_error_switch.setChecked(True)
        sound_error_card.hBoxLayout.addWidget(self._sound_error_switch)
        sound_error_card.hBoxLayout.addSpacing(16)
        dl_group.addSettingCard(sound_error_card)

        self._layout.addWidget(dl_group)

        # ── Performance group ─────────────────────────────────────────────
        perf_group = SettingCardGroup("Performance", self)

        conc_card = SettingCard(
            FluentIcon.DOWNLOAD,
            "Concurrent downloads",
            "Number of parallel download jobs (1 – 4)",
        )
        self._conc_combo = ComboBox()
        self._conc_combo.addItems(["1", "2", "3", "4"])
        self._conc_combo.setFixedWidth(80)
        conc_card.hBoxLayout.addWidget(self._conc_combo)
        conc_card.hBoxLayout.addSpacing(16)
        perf_group.addSettingCard(conc_card)

        frag_card = SettingCard(
            FluentIcon.SPEED_HIGH,
            "Concurrent fragments",
            "Fragment threads per download job (1 – 16)",
        )
        self._frag_combo = ComboBox()
        self._frag_combo.addItems([str(i) for i in range(1, 17)])
        self._frag_combo.setFixedWidth(80)
        frag_card.hBoxLayout.addWidget(self._frag_combo)
        frag_card.hBoxLayout.addSpacing(16)
        perf_group.addSettingCard(frag_card)

        self._layout.addWidget(perf_group)

        # ── Appearance group ──────────────────────────────────────────────
        appear_group = SettingCardGroup("Appearance", self)

        theme_card = SettingCard(
            FluentIcon.BRUSH,
            "Theme",
            "Choose between automatic, light or dark mode",
        )
        self._theme_combo = ComboBox()
        self._theme_combo.addItems(["Auto", "Light", "Dark"])
        self._theme_combo.setFixedWidth(100)
        theme_card.hBoxLayout.addWidget(self._theme_combo)
        theme_card.hBoxLayout.addSpacing(16)
        appear_group.addSettingCard(theme_card)

        color_card = SettingCard(
            FluentIcon.PALETTE,
            "Accent color",
            "Hex color used as the application accent (e.g. #0078D4)",
        )
        self._color_edit = LineEdit()
        self._color_edit.setFixedWidth(120)
        self._color_edit.setPlaceholderText("#0078D4")
        color_btn = PushButton("Choose…")
        color_btn.clicked.connect(self._pick_accent_color)
        color_card.hBoxLayout.addWidget(self._color_edit)
        color_card.hBoxLayout.addWidget(color_btn)
        color_card.hBoxLayout.addSpacing(16)
        appear_group.addSettingCard(color_card)

        self._layout.addWidget(appear_group)

        # ── Advanced group ────────────────────────────────────────────────
        adv_group = SettingCardGroup("Advanced", self)

        cookies_card = SettingCard(
            FluentIcon.CERTIFICATE,
            "Cookies file",
            "Netscape cookies.txt for sites that require login "
            "(ok.ru private, Instagram, etc.)",
        )
        self._cookies_edit = LineEdit()
        self._cookies_edit.setMinimumWidth(240)
        self._cookies_edit.setPlaceholderText("Path to cookies.txt (optional)")
        self._cookies_edit.setClearButtonEnabled(True)
        cookies_browse_btn = PushButton("Browse…")
        cookies_browse_btn.clicked.connect(self._browse_cookies)
        cookies_card.hBoxLayout.addWidget(self._cookies_edit)
        cookies_card.hBoxLayout.addWidget(cookies_browse_btn)
        cookies_card.hBoxLayout.addSpacing(16)
        adv_group.addSettingCard(cookies_card)

        self._layout.addWidget(adv_group)

        # ── Software update group ─────────────────────────────────────────
        updates_group = SettingCardGroup("Software update", self)

        auto_update_card = SettingCard(
            FluentIcon.SYNC,
            "Check for updates when the application starts",
            "The new version will be more stable and have more features",
        )
        self._auto_update_switch = SwitchButton()
        self._auto_update_switch.setChecked(True)
        auto_update_card.hBoxLayout.addWidget(self._auto_update_switch)
        auto_update_card.hBoxLayout.addSpacing(16)
        updates_group.addSettingCard(auto_update_card)

        self._layout.addWidget(updates_group)

        # ── About group ───────────────────────────────────────────────────
        about_group = SettingCardGroup("About", self)

        help_card = SettingCard(
            FluentIcon.HELP,
            "Help",
            "Report bugs, request features, or read the documentation on GitHub",
        )
        open_help_btn = PushButton("Open help page")
        open_help_btn.clicked.connect(
            lambda: webbrowser.open("https://github.com/k10978311-ai/VOK")
        )
        help_card.hBoxLayout.addWidget(open_help_btn)
        help_card.hBoxLayout.addSpacing(16)
        about_group.addSettingCard(help_card)

        feedback_card = SettingCard(
            FluentIcon.FEEDBACK,
            "Provide feedback",
            "Submit a bug report or feature request via GitHub Issues",
        )
        feedback_btn = PushButton("Provide feedback")
        feedback_btn.clicked.connect(
            lambda: webbrowser.open("https://github.com/k10978311-ai/VOK/issues")
        )
        feedback_card.hBoxLayout.addWidget(feedback_btn)
        feedback_card.hBoxLayout.addSpacing(16)
        about_group.addSettingCard(feedback_card)

        about_card = SettingCard(
            FluentIcon.INFO,
            "About",
            f"\u00a9 Copyright 2025, VOK Downloader \u2013 Version {app.__version__}",
        )
        self._check_update_btn = PushButton("Check update")
        self._check_update_btn.setIcon(FluentIcon.SYNC)
        self._check_update_btn.clicked.connect(self._on_check_update_clicked)
        about_card.hBoxLayout.addWidget(self._check_update_btn)
        about_card.hBoxLayout.addSpacing(16)
        about_group.addSettingCard(about_card)

        self._layout.addWidget(about_group)

        self._update_check_worker = None
        self._update_download_worker = None

        # ── Actions ───────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        self._save_btn = PrimaryPushButton("Save")
        self._save_btn.setIcon(FluentIcon.SAVE)
        self._save_btn.clicked.connect(self._save)
        self._reset_btn = PushButton("Reset")
        self._reset_btn.setIcon(FluentIcon.SYNC)
        self._reset_btn.clicked.connect(self._reset)
        btn_row.addWidget(self._save_btn)
        btn_row.addWidget(self._reset_btn)
        btn_row.addStretch(1)
        self._layout.addSpacing(8)
        self._layout.addLayout(btn_row)
        self._layout.addStretch(1)

        self._load_values()

    # ── Helpers ───────────────────────────────────────────────────────────

    def _apply_settings_to_ui(self, s: dict) -> None:
        """Populate UI widgets from a settings dict (from load_settings or get_default_settings)."""
        self._path_edit.setText(s.get("download_path", str(get_default_downloads_dir())))
        self._single_switch.setChecked(s.get("single_video_default", True))
        self._conc_combo.setCurrentText(str(int(s.get("concurrent_downloads", 2))))
        self._frag_combo.setCurrentText(str(int(s.get("concurrent_fragments", 4))))
        theme = s.get("theme", "Dark")
        if theme not in ("Auto", "Light", "Dark"):
            theme = "Dark"
        self._theme_combo.setCurrentText(theme)
        self._color_edit.setText(s.get("theme_color", "#0078D4"))
        self._cookies_edit.setText(s.get("cookies_file", ""))
        self._sound_complete_switch.setChecked(s.get("sound_alert_on_complete", True))
        self._sound_error_switch.setChecked(s.get("sound_alert_on_error", True))
        self._auto_update_switch.setChecked(s.get("auto_update_on_start", True))

    def _load_values(self) -> None:
        self._apply_settings_to_ui(load_settings())

    def _reset(self) -> None:
        """Reset form to default settings and show feedback."""
        self._apply_settings_to_ui(get_default_settings())
        InfoBar.success(
            title="Reset",
            content="Settings form reset to defaults. Click Save to apply.",
            isClosable=True,
            duration=2500,
            position=InfoBarPosition.TOP_RIGHT,
            parent=self,
        )

    def _save(self):
        path = self._path_edit.text().strip() or str(get_default_downloads_dir())
        color_hex = self._color_edit.text().strip() or "#0078D4"
        theme_name = self._theme_combo.currentText()

        s = load_settings()
        s["download_path"] = path
        s["single_video_default"] = self._single_switch.isChecked()
        s["concurrent_downloads"] = int(self._conc_combo.currentText())
        s["concurrent_fragments"] = int(self._frag_combo.currentText())
        s["theme"] = theme_name
        s["theme_color"] = color_hex
        s["cookies_file"] = self._cookies_edit.text().strip()
        s["sound_alert_on_complete"] = self._sound_complete_switch.isChecked()
        s["sound_alert_on_error"] = self._sound_error_switch.isChecked()
        s["auto_update_on_start"] = self._auto_update_switch.isChecked()
        save_settings(s)

        setTheme(_THEME_MAP.get(theme_name, Theme.AUTO))
        try:
            setThemeColor(QColor(color_hex))
        except Exception:
            pass
        apply_app_palette(theme_name, color_hex)

        add_log_entry("info", "Settings saved.")
        InfoBar.success(
            title="Saved",
            content="Settings saved successfully.",
            isClosable=True,
            duration=2500,
            position=InfoBarPosition.TOP_RIGHT,
            parent=self,
        )

    def _on_enhance_mode_clicked(self):
        """Show 'Coming soon!' when user selects Enhance download mode."""
        InfoBar.info(
            title="Enhance",
            content="Coming soon!",
            isClosable=True,
            duration=3000,
            position=InfoBarPosition.TOP_RIGHT,
            parent=self,
        )

    def _browse_path(self):
        start = self._path_edit.text() or str(get_default_downloads_dir())
        path = QFileDialog.getExistingDirectory(self, "Download folder", start)
        if path:
            self._path_edit.setText(path)

    def _browse_cookies(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select cookies file",
            "",
            "Text files (*.txt);;All files (*)",
        )
        if path:
            self._cookies_edit.setText(path)

    def _on_check_update_clicked(self):
        if self._update_check_worker and self._update_check_worker.isRunning():
            return
        self._check_update_btn.setEnabled(False)
        self._update_check_worker = UpdateCheckWorker(self)
        self._update_check_worker.result_ready.connect(self._on_update_check_result)
        self._update_check_worker.finished.connect(lambda: self._check_update_btn.setEnabled(True))
        self._update_check_worker.start()

    def _on_update_check_result(self, version: str | None, download_url: str | None):
        if version is None or download_url is None:
            InfoBar.success(
                title="No update",
                content="You are on the latest version.",
                isClosable=True,
                duration=3000,
                position=InfoBarPosition.TOP_RIGHT,
                parent=self,
            )
            return
        reply = QMessageBox.question(
            self,
            "Update available",
            f"New version {version} is available.\n\nUpdate now? The app will close and the new version will be installed.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        self._check_update_btn.setEnabled(False)
        self._update_download_worker = UpdateDownloadWorker(download_url, self)
        self._update_download_worker.done_signal.connect(self._on_update_downloaded)
        self._update_download_worker.failed_signal.connect(self._on_update_download_failed)
        self._update_download_worker.finished.connect(lambda: self._check_update_btn.setEnabled(True))
        self._update_download_worker.start()
        InfoBar.success(
            title="Downloading update",
            content="The installer is downloading. The app will close when ready.",
            isClosable=True,
            duration=5000,
            position=InfoBarPosition.TOP_RIGHT,
            parent=self,
        )

    def _on_update_downloaded(self, path: str):
        install_update(path)

    def _on_update_download_failed(self):
        self._check_update_btn.setEnabled(True)
        InfoBar.error(
            title="Update failed",
            content="Could not download the update. Try again later.",
            isClosable=True,
            duration=4000,
            position=InfoBarPosition.TOP_RIGHT,
            parent=self,
        )

    def _pick_accent_color(self):
        """Open Qt5 color dialog and set accent color hex to the line edit."""
        default_hex = "#0078D4"
        raw = self._color_edit.text().strip() or default_hex
        initial = QColor(raw)
        if not initial.isValid():
            initial = QColor(default_hex)
        color = QColorDialog.getColor(initial, self, "Accent color")
        if color.isValid():
            self._color_edit.setText(color.name())
