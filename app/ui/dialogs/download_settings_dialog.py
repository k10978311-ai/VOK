"""Download Settings dialog — qfluentwidgets MessageBoxBase + SettingCards."""
from __future__ import annotations

from PyQt5.QtWidgets import QFileDialog, QVBoxLayout, QWidget
from qfluentwidgets import (
    ComboBox,
    FluentIcon,
    InfoBar,
    InfoBarPosition,
    LineEdit,
    MessageBoxBase,
    PushButton,
    PushSettingCard,
    ScrollArea,
    SettingCard,
    SettingCardGroup,
    SubtitleLabel,
    SwitchButton,
)

from app.config.store import load_settings, save_settings
from app.ui.helpers import DOWNLOAD_FORMATS

INFOBAR_MS_SUCCESS = 3000


class DownloadSettingsDialog(MessageBoxBase):
    """Modal dialog for configuring download output folder, format, and options."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._settings = load_settings()
        self._build()
        self.yesButton.setText(self.tr("Save"))
        self.cancelButton.setText(self.tr("Cancel"))
        self.widget.setMinimumWidth(700)
        self.accepted.connect(self._save)

    # ── Build ──────────────────────────────────────────────────────────────

    def _build(self) -> None:
        s = self._settings

        self.viewLayout.addWidget(SubtitleLabel(self.tr("Download Settings"), self))
        self.viewLayout.setSpacing(10)

        scroll = ScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(ScrollArea.NoFrame)
        scroll.setMinimumHeight(520)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }"
                             "QScrollArea > QWidget > QWidget { background: transparent; }")

        container = QWidget()
        lay = QVBoxLayout(container)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        # ── Output ────────────────────────────────────────────────────────
        output_grp = SettingCardGroup(self.tr("Output"), container)

        self._path_card = PushSettingCard(
            text=self.tr("Choose"),
            icon=FluentIcon.FOLDER,
            title=self.tr("Save folder"),
            content=s.get("download_path", ""),
        )
        self._path_card.clicked.connect(self._browse_folder)
        output_grp.addSettingCard(self._path_card)

        self._format_card = SettingCard(
            FluentIcon.MEDIA,
            self.tr("Format"),
            self.tr("Video/audio quality and container"),
        )
        self._format_combo = ComboBox()
        self._format_combo.addItems(DOWNLOAD_FORMATS)
        cur_fmt = s.get("download_format", DOWNLOAD_FORMATS[0])
        idx = self._format_combo.findText(cur_fmt)
        self._format_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self._format_combo.setFixedWidth(175)
        self._format_card.hBoxLayout.addWidget(self._format_combo)
        self._format_card.hBoxLayout.addSpacing(16)
        output_grp.addSettingCard(self._format_card)

        lay.addWidget(output_grp)

        # ── Performance ───────────────────────────────────────────────────
        perf_grp = SettingCardGroup(self.tr("Performance"), container)

        self._conc_card = SettingCard(
            FluentIcon.DOWNLOAD,
            self.tr("Concurrent downloads"),
            self.tr("Number of parallel download jobs (1 \u2013 8)"),
        )
        self._conc_combo = ComboBox()
        self._conc_combo.addItems([str(i) for i in range(1, 9)])
        self._conc_combo.setCurrentText(str(s.get("concurrent_downloads", 2)))
        self._conc_combo.setFixedWidth(80)
        self._conc_card.hBoxLayout.addWidget(self._conc_combo)
        self._conc_card.hBoxLayout.addSpacing(16)
        perf_grp.addSettingCard(self._conc_card)

        self._frag_card = SettingCard(
            FluentIcon.SPEED_HIGH,
            self.tr("Concurrent fragments"),
            self.tr("Fragment threads per download job (1 \u2013 16)"),
        )
        self._frag_combo = ComboBox()
        self._frag_combo.addItems([str(i) for i in range(1, 17)])
        self._frag_combo.setCurrentText(str(s.get("concurrent_fragments", 4)))
        self._frag_combo.setFixedWidth(80)
        self._frag_card.hBoxLayout.addWidget(self._frag_combo)
        self._frag_card.hBoxLayout.addSpacing(16)
        perf_grp.addSettingCard(self._frag_card)

        lay.addWidget(perf_grp)

        # ── Advanced ──────────────────────────────────────────────────────
        adv_grp = SettingCardGroup(self.tr("Advanced"), container)

        self._cookies_card = SettingCard(
            FluentIcon.CERTIFICATE,
            self.tr("Cookies file"),
            self.tr("Netscape cookies.txt for sites that require login"),
        )
        self._cookies_edit = LineEdit()
        self._cookies_edit.setMinimumWidth(200)
        self._cookies_edit.setText(s.get("cookies_file", ""))
        self._cookies_edit.setPlaceholderText(self.tr("Path to cookies.txt (optional)"))
        self._cookies_edit.setClearButtonEnabled(True)
        self._cookies_browse_btn = PushButton(self.tr("Browse\u2026"))
        self._cookies_browse_btn.clicked.connect(self._browse_cookies)
        self._cookies_card.hBoxLayout.addWidget(self._cookies_edit)
        self._cookies_card.hBoxLayout.addSpacing(8)
        self._cookies_card.hBoxLayout.addWidget(self._cookies_browse_btn)
        self._cookies_card.hBoxLayout.addSpacing(16)
        adv_grp.addSettingCard(self._cookies_card)

        lay.addWidget(adv_grp)

        # ── Notifications ─────────────────────────────────────────────────
        notif_grp = SettingCardGroup(self.tr("Notifications"), container)

        self._auto_reset_card = SettingCard(
            FluentIcon.SYNC,
            self.tr("Auto-reset link before download"),
            self.tr("Clear the URL input field after a download starts"),
        )
        self._auto_reset_switch = SwitchButton()
        self._auto_reset_switch.setChecked(bool(s.get("auto_reset_link_before_download", True)))
        self._auto_reset_card.hBoxLayout.addWidget(self._auto_reset_switch)
        self._auto_reset_card.hBoxLayout.addSpacing(16)
        notif_grp.addSettingCard(self._auto_reset_card)

        self._sound_ok_card = SettingCard(
            FluentIcon.MUSIC,
            self.tr("Sound alert on complete"),
            self.tr("Play a sound when a download finishes successfully"),
        )
        self._sound_ok_switch = SwitchButton()
        self._sound_ok_switch.setChecked(bool(s.get("sound_alert_on_complete", True)))
        self._sound_ok_card.hBoxLayout.addWidget(self._sound_ok_switch)
        self._sound_ok_card.hBoxLayout.addSpacing(16)
        notif_grp.addSettingCard(self._sound_ok_card)

        self._sound_err_card = SettingCard(
            FluentIcon.IOT,
            self.tr("Sound alert on error"),
            self.tr("Play a sound when a download fails or is skipped"),
        )
        self._sound_err_switch = SwitchButton()
        self._sound_err_switch.setChecked(bool(s.get("sound_alert_on_error", True)))
        self._sound_err_card.hBoxLayout.addWidget(self._sound_err_switch)
        self._sound_err_card.hBoxLayout.addSpacing(16)
        notif_grp.addSettingCard(self._sound_err_card)

        lay.addWidget(notif_grp)
        lay.addStretch(1)

        scroll.setWidget(container)
        self.viewLayout.addWidget(scroll)

    # ── Browse helpers ─────────────────────────────────────────────────────

    def _browse_folder(self) -> None:
        d = QFileDialog.getExistingDirectory(
            self, self.tr("Select Save Folder"), self._path_card.contentLabel.text()
        )
        if d:
            self._path_card.contentLabel.setText(d)

    def _browse_cookies(self) -> None:
        f, _ = QFileDialog.getOpenFileName(
            self, self.tr("Select Cookies File"), "",
            self.tr("Text files (*.txt);;All files (*)")
        )
        if f:
            self._cookies_edit.setText(f)

    # ── Save ───────────────────────────────────────────────────────────────

    def _save(self) -> None:
        s = self._settings
        s["download_path"]                   = self._path_card.contentLabel.text()
        s["download_format"]                 = self._format_combo.currentText()
        s["concurrent_downloads"]            = int(self._conc_combo.currentText())
        s["concurrent_fragments"]            = int(self._frag_combo.currentText())
        s["cookies_file"]                    = self._cookies_edit.text().strip()
        s["auto_reset_link_before_download"] = self._auto_reset_switch.isChecked()
        s["sound_alert_on_complete"]         = self._sound_ok_switch.isChecked()
        s["sound_alert_on_error"]            = self._sound_err_switch.isChecked()
        save_settings(s)
        InfoBar.success(
            self.tr("Settings saved"),
            self.tr("Download settings updated."),
            duration=INFOBAR_MS_SUCCESS,
            position=InfoBarPosition.TOP_RIGHT,
            parent=self.parent(),
        )
