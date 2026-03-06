"""Settings view: Fluent UI setting cards."""

import webbrowser

import app
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QColorDialog, QFileDialog, QMessageBox

from qfluentwidgets import (
    ComboBox,
    FluentIcon,
    InfoBar,
    InfoBarPosition,
    LargeTitleLabel,
    LineEdit,
    OptionsConfigItem,
    OptionsSettingCard,
    PushSettingCard,
    OptionsValidator,
    PushButton,
    QConfig,
    SegmentedWidget,
    SettingCard,
    SettingCardGroup,
    SwitchButton,
    setTheme,
    setThemeColor,
    Theme,
)

from app.common.i18n import apply_language, LANGUAGES
from app.common.paths import get_default_downloads_dir
from app.common.state import add_log_entry
from app.config import get_default_settings, load_settings, save_settings
from app.core.updater import check_update, download_update, install_update
from app.ui.helpers import DOWNLOAD_FORMATS
from app.ui.theme import apply_app_palette

from .base import BaseView

_THEME_MAP = {"Auto": Theme.AUTO, "Light": Theme.LIGHT, "Dark": Theme.DARK}
_THEME_REVERSE = {v: k for k, v in _THEME_MAP.items()}


class _VokConfig(QConfig):
    """Application config items backed by QConfig for OptionsSettingCard."""
    themeMode = OptionsConfigItem(
        "Appearance",
        "themeMode",
        Theme.DARK,
        OptionsValidator([Theme.LIGHT, Theme.DARK, Theme.AUTO]),
    )

    def save(self) -> None:  # VOK manages its own settings file — suppress QConfig I/O
        pass


vok_config = _VokConfig()


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
        self._update_check_worker = None
        self._update_download_worker = None
        self._build_ui()
        self._load_values()
        self._connect_auto_save()

    # ── UI construction ───────────────────────────────────────────────────

    def _build_ui(self) -> None:
        self.setWindowTitle(self.tr("Settings"))

        self._title_lbl = LargeTitleLabel(self)
        self._title_lbl.setText(self.tr("Settings"))
        self._layout.addWidget(self._title_lbl)
        self._layout.addSpacing(4)

        # ── Download group ────────────────────────────────────────────────
        self._dl_group = SettingCardGroup(self.tr("Downloads"), self)

        self._path_push_card = PushSettingCard(
            text=self.tr("Choose"),
            icon=FluentIcon.FOLDER,
            title=self.tr("Download path"),
            content=str(get_default_downloads_dir()),
        )
        self._path_push_card.clicked.connect(self._browse_path)
        self._dl_group.addSettingCard(self._path_push_card)

        self._format_card = SettingCard(
            FluentIcon.MEDIA,
            self.tr("Default download format"),
            self.tr("Video/audio quality and container used for new downloads"),
        )
        self._format_combo = ComboBox()
        self._format_combo.addItems(DOWNLOAD_FORMATS)
        self._format_combo.setFixedWidth(175)
        self._format_card.hBoxLayout.addWidget(self._format_combo)
        self._format_card.hBoxLayout.addSpacing(16)
        self._dl_group.addSettingCard(self._format_card)

        self._single_card = SettingCard(
            FluentIcon.VIDEO,
            self.tr("Single video only (no playlists)"),
            self.tr(
                "Download only the current video; skip playlists"
                " when a single URL is used."
            ),
        )
        self._single_switch = SwitchButton()
        self._single_card.hBoxLayout.addWidget(self._single_switch)
        self._single_card.hBoxLayout.addSpacing(16)
        self._dl_group.addSettingCard(self._single_card)

        self._mode_card = SettingCard(
            FluentIcon.DOWNLOAD,
            self.tr("Download mode"),
            self.tr("Normal or enhanced download."),
        )
        self._mode_segmented = SegmentedWidget()
        self._mode_segmented.insertItem(0, "normal", self.tr("Normal"), None)
        self._mode_segmented.insertItem(
            1, "enhance", self.tr("Enhance"), self._on_enhance_mode_clicked
        )
        self._mode_segmented.setCurrentItem("normal")
        self._mode_card.hBoxLayout.addWidget(self._mode_segmented)
        self._mode_card.hBoxLayout.addSpacing(16)
        self._dl_group.addSettingCard(self._mode_card)

        self._sound_complete_card = SettingCard(
            FluentIcon.MUSIC,
            self.tr("Sound alert on completed download"),
            self.tr("Play a sound when a download finishes successfully."),
        )
        self._sound_complete_switch = SwitchButton()
        self._sound_complete_switch.setChecked(True)
        self._sound_complete_card.hBoxLayout.addWidget(self._sound_complete_switch)
        self._sound_complete_card.hBoxLayout.addSpacing(16)
        self._dl_group.addSettingCard(self._sound_complete_card)

        self._sound_error_card = SettingCard(
            FluentIcon.IOT,
            self.tr("Sound alert on download error"),
            self.tr("Play a sound when a download fails or is skipped."),
        )
        self._sound_error_switch = SwitchButton()
        self._sound_error_switch.setChecked(True)
        self._sound_error_card.hBoxLayout.addWidget(self._sound_error_switch)
        self._sound_error_card.hBoxLayout.addSpacing(16)
        self._dl_group.addSettingCard(self._sound_error_card)

        self._auto_reset_card = SettingCard(
            FluentIcon.SYNC,
            self.tr("Auto-clear URL before download"),
            self.tr(
                "Automatically clear the URL input field after a download starts."
            ),
        )
        self._auto_reset_switch = SwitchButton()
        self._auto_reset_switch.setChecked(True)
        self._auto_reset_card.hBoxLayout.addWidget(self._auto_reset_switch)
        self._auto_reset_card.hBoxLayout.addSpacing(16)
        self._dl_group.addSettingCard(self._auto_reset_card)

        self._layout.addWidget(self._dl_group)

        # ── Performance group ─────────────────────────────────────────────
        self._perf_group = SettingCardGroup(self.tr("Performance"), self)

        self._conc_card = SettingCard(
            FluentIcon.DOWNLOAD,
            self.tr("Concurrent downloads"),
            self.tr("Number of parallel download jobs (1 \u2013 4)"),
        )
        self._conc_combo = ComboBox()
        self._conc_combo.addItems(["1", "2", "3", "4"])
        self._conc_combo.setFixedWidth(80)
        self._conc_card.hBoxLayout.addWidget(self._conc_combo)
        self._conc_card.hBoxLayout.addSpacing(16)
        self._perf_group.addSettingCard(self._conc_card)

        self._frag_card = SettingCard(
            FluentIcon.SPEED_HIGH,
            self.tr("Concurrent fragments"),
            self.tr("Fragment threads per download job (1 \u2013 16)"),
        )
        self._frag_combo = ComboBox()
        self._frag_combo.addItems([str(i) for i in range(1, 17)])
        self._frag_combo.setFixedWidth(80)
        self._frag_card.hBoxLayout.addWidget(self._frag_combo)
        self._frag_card.hBoxLayout.addSpacing(16)
        self._perf_group.addSettingCard(self._frag_card)

        self._layout.addWidget(self._perf_group)

        # ── Appearance group ──────────────────────────────────────────────
        self._appear_group = SettingCardGroup(self.tr("Appearance"), self)

        self._theme_card = OptionsSettingCard(
            vok_config.themeMode,
            FluentIcon.BRUSH,
            self.tr("Application theme"),
            self.tr("Adjust the appearance of your application"),
            texts=[
                self.tr("Light"),
                self.tr("Dark"),
                self.tr("Follow system settings"),
            ],
            parent=self,
        )
        self._theme_card.optionChanged.connect(self._on_theme_option_changed)
        self._appear_group.addSettingCard(self._theme_card)

        self._language_card = SettingCard(
            FluentIcon.LANGUAGE,
            self.tr("Language"),
            self.tr(
                "Application display language"
                " (restart may be needed for full effect)"
            ),
        )
        self._language_combo = ComboBox()
        self._language_combo.addItems(list(LANGUAGES.keys()))
        self._language_combo.setFixedWidth(175)
        self._language_card.hBoxLayout.addWidget(self._language_combo)
        self._language_card.hBoxLayout.addSpacing(16)
        self._appear_group.addSettingCard(self._language_card)

        self._color_card = SettingCard(
            FluentIcon.PALETTE,
            self.tr("Accent color"),
            self.tr(
                "Hex color used as the application accent (e.g. #0078D4)"
            ),
        )
        self._color_edit = LineEdit()
        self._color_edit.setFixedWidth(120)
        self._color_edit.setPlaceholderText("#0078D4")
        self._color_btn = PushButton(self.tr("Choose\u2026"))
        self._color_btn.clicked.connect(self._pick_accent_color)
        self._color_card.hBoxLayout.addWidget(self._color_edit)
        self._color_card.hBoxLayout.addSpacing(8)
        self._color_card.hBoxLayout.addWidget(self._color_btn)
        self._color_card.hBoxLayout.addSpacing(16)
        self._appear_group.addSettingCard(self._color_card)

        self._layout.addWidget(self._appear_group)

        # ── Advanced group ────────────────────────────────────────────────
        self._adv_group = SettingCardGroup(self.tr("Advanced"), self)

        self._cookies_card = SettingCard(
            FluentIcon.CERTIFICATE,
            self.tr("Cookies file"),
            self.tr(
                "Netscape cookies.txt for sites that require login"
                " (ok.ru private, Instagram, etc.)"
            ),
        )
        self._cookies_edit = LineEdit()
        self._cookies_edit.setMinimumWidth(240)
        self._cookies_edit.setPlaceholderText(
            self.tr("Path to cookies.txt (optional)")
        )
        self._cookies_edit.setClearButtonEnabled(True)
        self._cookies_browse_btn = PushButton(self.tr("Browse\u2026"))
        self._cookies_browse_btn.clicked.connect(self._browse_cookies)
        self._cookies_card.hBoxLayout.addWidget(self._cookies_edit)
        self._cookies_card.hBoxLayout.addSpacing(8)
        self._cookies_card.hBoxLayout.addWidget(self._cookies_browse_btn)
        self._cookies_card.hBoxLayout.addSpacing(16)
        self._adv_group.addSettingCard(self._cookies_card)

        self._reset_card = SettingCard(
            FluentIcon.SYNC,
            self.tr("Reset settings"),
            self.tr("Restore all settings to their factory defaults"),
        )
        self._reset_btn = PushButton(self.tr("Reset to defaults"))
        self._reset_btn.setIcon(FluentIcon.SYNC)
        self._reset_btn.clicked.connect(self._reset)
        self._reset_card.hBoxLayout.addWidget(self._reset_btn)
        self._reset_card.hBoxLayout.addSpacing(16)
        self._adv_group.addSettingCard(self._reset_card)

        self._layout.addWidget(self._adv_group)

        # ── Software update group ─────────────────────────────────────────
        self._updates_group = SettingCardGroup(self.tr("Software update"), self)

        self._auto_update_card = SettingCard(
            FluentIcon.SYNC,
            self.tr("Check for updates when the application starts"),
            self.tr(
                "The new version will be more stable and have more features"
            ),
        )
        self._auto_update_switch = SwitchButton()
        self._auto_update_switch.setChecked(True)
        self._auto_update_card.hBoxLayout.addWidget(self._auto_update_switch)
        self._auto_update_card.hBoxLayout.addSpacing(16)
        self._updates_group.addSettingCard(self._auto_update_card)

        self._layout.addWidget(self._updates_group)

        # ── About group ───────────────────────────────────────────────────
        self._about_group = SettingCardGroup(self.tr("About"), self)

        self._help_card = SettingCard(
            FluentIcon.HELP,
            self.tr("Help"),
            self.tr(
                "Report bugs, request features, or read the"
                " documentation on GitHub"
            ),
        )
        self._open_help_btn = PushButton(self.tr("Open help page"))
        self._open_help_btn.clicked.connect(
            lambda: webbrowser.open("https://github.com/k10978311-ai/VOK")
        )
        self._help_card.hBoxLayout.addWidget(self._open_help_btn)
        self._help_card.hBoxLayout.addSpacing(16)
        self._about_group.addSettingCard(self._help_card)

        self._feedback_card = SettingCard(
            FluentIcon.FEEDBACK,
            self.tr("Provide feedback"),
            self.tr(
                "Submit a bug report or feature request via GitHub Issues"
            ),
        )
        self._feedback_btn = PushButton(self.tr("Provide feedback"))
        self._feedback_btn.clicked.connect(
            lambda: webbrowser.open(
                "https://github.com/k10978311-ai/VOK/issues"
            )
        )
        self._feedback_card.hBoxLayout.addWidget(self._feedback_btn)
        self._feedback_card.hBoxLayout.addSpacing(16)
        self._about_group.addSettingCard(self._feedback_card)

        self._about_card = SettingCard(
            FluentIcon.INFO,
            self.tr("About"),
            self.tr("\u00a9 Copyright 2025, VOK Downloader \u2013 Version")
            + f" {app.__version__}",
        )
        self._check_update_btn = PushButton(self.tr("Check update"))
        self._check_update_btn.setIcon(FluentIcon.SYNC)
        self._check_update_btn.clicked.connect(self._on_check_update_clicked)
        self._about_card.hBoxLayout.addWidget(self._check_update_btn)
        self._about_card.hBoxLayout.addSpacing(16)
        self._about_group.addSettingCard(self._about_card)

        self._layout.addWidget(self._about_group)
        self._layout.addStretch(1)

    # ── Language change ───────────────────────────────────────────────────

    def changeEvent(self, event) -> None:  # type: ignore[override]
        from PyQt5.QtCore import QEvent
        super().changeEvent(event)
        if event.type() == QEvent.LanguageChange:
            self._retranslate_ui()

    def _retranslate_ui(self) -> None:
        self.setWindowTitle(self.tr("Settings"))
        self._title_lbl.setText(self.tr("Settings"))

        # Groups
        self._dl_group.titleLabel.setText(self.tr("Downloads"))
        self._perf_group.titleLabel.setText(self.tr("Performance"))
        self._appear_group.titleLabel.setText(self.tr("Appearance"))
        self._adv_group.titleLabel.setText(self.tr("Advanced"))
        self._updates_group.titleLabel.setText(self.tr("Software update"))
        self._about_group.titleLabel.setText(self.tr("About"))

        # Download cards
        self._path_push_card.titleLabel.setText(self.tr("Download path"))
        self._path_push_card.button.setText(self.tr("Choose"))
        self._format_card.titleLabel.setText(self.tr("Default download format"))
        self._format_card.contentLabel.setText(
            self.tr("Video/audio quality and container used for new downloads")
        )
        self._single_card.titleLabel.setText(
            self.tr("Single video only (no playlists)")
        )
        self._single_card.contentLabel.setText(
            self.tr(
                "Download only the current video; skip playlists"
                " when a single URL is used."
            )
        )
        self._mode_card.titleLabel.setText(self.tr("Download mode"))
        self._mode_card.contentLabel.setText(
            self.tr("Normal or enhanced download.")
        )
        self._sound_complete_card.titleLabel.setText(
            self.tr("Sound alert on completed download")
        )
        self._sound_complete_card.contentLabel.setText(
            self.tr("Play a sound when a download finishes successfully.")
        )
        self._sound_error_card.titleLabel.setText(
            self.tr("Sound alert on download error")
        )
        self._sound_error_card.contentLabel.setText(
            self.tr("Play a sound when a download fails or is skipped.")
        )
        self._auto_reset_card.titleLabel.setText(
            self.tr("Auto-clear URL before download")
        )
        self._auto_reset_card.contentLabel.setText(
            self.tr(
                "Automatically clear the URL input field after a download starts."
            )
        )

        # Performance cards
        self._conc_card.titleLabel.setText(self.tr("Concurrent downloads"))
        self._conc_card.contentLabel.setText(
            self.tr("Number of parallel download jobs (1 \u2013 4)")
        )
        self._frag_card.titleLabel.setText(self.tr("Concurrent fragments"))
        self._frag_card.contentLabel.setText(
            self.tr("Fragment threads per download job (1 \u2013 16)")
        )

        # Appearance cards
        self._theme_card.card.titleLabel.setText(self.tr("Application theme"))
        self._theme_card.card.contentLabel.setText(
            self.tr("Adjust the appearance of your application")
        )
        self._language_card.titleLabel.setText(self.tr("Language"))
        self._language_card.contentLabel.setText(
            self.tr(
                "Application display language"
                " (restart may be needed for full effect)"
            )
        )
        self._color_card.titleLabel.setText(self.tr("Accent color"))
        self._color_card.contentLabel.setText(
            self.tr("Hex color used as the application accent (e.g. #0078D4)")
        )
        self._color_btn.setText(self.tr("Choose\u2026"))

        # Advanced cards
        self._cookies_card.titleLabel.setText(self.tr("Cookies file"))
        self._cookies_card.contentLabel.setText(
            self.tr(
                "Netscape cookies.txt for sites that require login"
                " (ok.ru private, Instagram, etc.)"
            )
        )
        self._cookies_edit.setPlaceholderText(
            self.tr("Path to cookies.txt (optional)")
        )
        self._cookies_browse_btn.setText(self.tr("Browse\u2026"))
        self._reset_card.titleLabel.setText(self.tr("Reset settings"))
        self._reset_card.contentLabel.setText(
            self.tr("Restore all settings to their factory defaults")
        )
        self._reset_btn.setText(self.tr("Reset to defaults"))

        # Updates cards
        self._auto_update_card.titleLabel.setText(
            self.tr("Check for updates when the application starts")
        )
        self._auto_update_card.contentLabel.setText(
            self.tr(
                "The new version will be more stable and have more features"
            )
        )

        # About cards
        self._help_card.titleLabel.setText(self.tr("Help"))
        self._help_card.contentLabel.setText(
            self.tr(
                "Report bugs, request features, or read the"
                " documentation on GitHub"
            )
        )
        self._open_help_btn.setText(self.tr("Open help page"))
        self._feedback_card.titleLabel.setText(self.tr("Provide feedback"))
        self._feedback_card.contentLabel.setText(
            self.tr(
                "Submit a bug report or feature request via GitHub Issues"
            )
        )
        self._feedback_btn.setText(self.tr("Provide feedback"))
        self._about_card.titleLabel.setText(self.tr("About"))
        self._about_card.contentLabel.setText(
            self.tr("\u00a9 Copyright 2025, VOK Downloader \u2013 Version")
            + f" {app.__version__}"
        )
        self._check_update_btn.setText(self.tr("Check update"))

    # ── Helpers ───────────────────────────────────────────────────────────

    def _apply_settings_to_ui(self, s: dict) -> None:
        """Populate UI widgets from a settings dict (from load_settings or get_default_settings)."""
        self._path_push_card.contentLabel.setText(s.get("download_path", str(get_default_downloads_dir())))
        fmt = s.get("download_format", "Best (video+audio)")
        self._format_combo.setCurrentText(fmt if fmt in DOWNLOAD_FORMATS else DOWNLOAD_FORMATS[0])
        self._single_switch.setChecked(s.get("single_video_default", True))
        self._conc_combo.setCurrentText(str(int(s.get("concurrent_downloads", 2))))
        self._frag_combo.setCurrentText(str(int(s.get("concurrent_fragments", 4))))
        self._color_edit.setText(s.get("theme_color", "#0078D4"))
        self._cookies_edit.setText(s.get("cookies_file", ""))
        self._sound_complete_switch.setChecked(s.get("sound_alert_on_complete", True))
        self._sound_error_switch.setChecked(s.get("sound_alert_on_error", True))
        self._auto_reset_switch.setChecked(s.get("auto_reset_link_before_download", True))
        self._auto_update_switch.setChecked(s.get("auto_update_on_start", True))
        lang = s.get("language", "Auto (System)")
        lang_labels = list(LANGUAGES.keys())
        self._language_combo.setCurrentText(lang if lang in lang_labels else lang_labels[0])
        # sync OptionsSettingCard
        theme_name = s.get("theme", "Dark")
        if theme_name not in _THEME_MAP:
            theme_name = "Dark"
        vok_config.set(vok_config.themeMode, _THEME_MAP[theme_name])

    def _load_values(self) -> None:
        self._apply_settings_to_ui(load_settings())

    def _connect_auto_save(self) -> None:
        """Connect all widget change signals to auto-save."""
        self._format_combo.currentTextChanged.connect(self._save)
        self._single_switch.checkedChanged.connect(self._save)
        self._conc_combo.currentTextChanged.connect(self._save)
        self._frag_combo.currentTextChanged.connect(self._save)
        self._sound_complete_switch.checkedChanged.connect(self._save)
        self._sound_error_switch.checkedChanged.connect(self._save)
        self._auto_reset_switch.checkedChanged.connect(self._save)
        self._auto_update_switch.checkedChanged.connect(self._save)
        self._color_edit.editingFinished.connect(self._save)
        self._cookies_edit.editingFinished.connect(self._save)
        self._language_combo.currentTextChanged.connect(self._on_language_changed)

    def _reset(self) -> None:
        """Reset all settings to defaults and auto-save."""
        self._apply_settings_to_ui(get_default_settings())
        self._save()
        InfoBar.success(
            title=self.tr("Reset"),
            content=self.tr("Settings restored to defaults."),
            isClosable=True,
            duration=2500,
            position=InfoBarPosition.TOP_RIGHT,
            parent=self,
        )

    def _save(self):
        path = self._path_push_card.contentLabel.text().strip() or str(get_default_downloads_dir())
        color_hex = self._color_edit.text().strip() or "#0078D4"

        s = load_settings()
        s["download_path"] = path
        s["download_format"] = self._format_combo.currentText()
        s["single_video_default"] = self._single_switch.isChecked()
        s["concurrent_downloads"] = int(self._conc_combo.currentText())
        s["concurrent_fragments"] = int(self._frag_combo.currentText())
        s["theme"] = _THEME_REVERSE.get(vok_config.themeMode.value, "Dark")
        s["theme_color"] = color_hex
        s["cookies_file"] = self._cookies_edit.text().strip()
        s["sound_alert_on_complete"] = self._sound_complete_switch.isChecked()
        s["sound_alert_on_error"] = self._sound_error_switch.isChecked()
        s["auto_reset_link_before_download"] = self._auto_reset_switch.isChecked()
        s["auto_update_on_start"] = self._auto_update_switch.isChecked()
        s["language"] = self._language_combo.currentText()
        save_settings(s)

        setTheme(_THEME_MAP.get(s["theme"], Theme.AUTO))
        try:
            setThemeColor(QColor(color_hex))
        except Exception:
            pass
        apply_app_palette(s["theme"], color_hex)

        add_log_entry("info", "Settings saved.")

    def _on_theme_option_changed(self, item: OptionsConfigItem) -> None:
        """Live-preview theme and auto-save when the user picks a different option."""
        setTheme(item.value)
        self._save()

    def _on_language_changed(self, label: str) -> None:
        """Apply translator immediately and save."""
        locale_str = LANGUAGES.get(label, "")
        apply_language(locale_str)
        self._save()
        InfoBar.info(
            title=self.tr("Language changed"),
            content=self.tr("Some text will update on next restart."),
            isClosable=True,
            duration=3500,
            position=InfoBarPosition.TOP_RIGHT,
            parent=self,
        )

    def _on_enhance_mode_clicked(self):
        """Show 'Coming soon!' when user selects Enhance download mode."""
        InfoBar.info(
            title=self.tr("Enhance"),
            content=self.tr("Coming soon!"),
            isClosable=True,
            duration=3000,
            position=InfoBarPosition.TOP_RIGHT,
            parent=self,
        )

    def _browse_path(self):
        start = self._path_push_card.contentLabel.text() or str(get_default_downloads_dir())
        path = QFileDialog.getExistingDirectory(self, self.tr("Download folder"), start)
        if path:
            self._path_push_card.contentLabel.setText(path)
            self._save()

    def _browse_cookies(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Select cookies file"),
            "",
            self.tr("Text files (*.txt);;All files (*)"),
        )
        if path:
            self._cookies_edit.setText(path)
            self._save()

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
                title=self.tr("No update"),
                content=self.tr("You are on the latest version."),
                isClosable=True,
                duration=3000,
                position=InfoBarPosition.TOP_RIGHT,
                parent=self,
            )
            return
        reply = QMessageBox.question(
            self,
            self.tr("Update available"),
            self.tr("New version %1 is available.\n\nUpdate now? The app will close and the new version will be installed.").replace("%1", version),
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
            title=self.tr("Downloading update"),
            content=self.tr("The installer is downloading. The app will close when ready."),
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
            title=self.tr("Update failed"),
            content=self.tr("Could not download the update. Try again later."),
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
        color = QColorDialog.getColor(initial, self, self.tr("Accent color"))
        if color.isValid():
            self._color_edit.setText(color.name())
            self._save()
