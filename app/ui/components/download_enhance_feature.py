"""Enhance download card: URL + stream-edit options (logo, flip, color, speed)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QColorDialog,
    QDialog,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
)

from app.config import load_settings, save_settings
from qfluentwidgets import (
    BodyLabel,
    CardWidget,
    ComboBox,
    CompactSpinBox,
    ExpandGroupSettingCard,
    FluentIcon,
    LineEdit,
    PrimaryPushButton,
    PushButton,
    SettingCard,
    SettingCardGroup,
    Slider,
    SwitchButton,
    TitleLabel,
)

from app.ui.components import CardHeader


@dataclass
class EnhanceOptions:
    """Options for post-download stream edit (logo, flip, color, speed)."""

    logo_path: str = ""
    logo_position: str = "center"  # left, right, center, top, custom
    logo_size: int = 120            # logo height in pixels; width auto-scaled
    logo_x: int = 10               # custom X offset from left (pixels)
    logo_y: int = 10               # custom Y offset from top (pixels)
    flip: str = "none"  # none, horizontal, vertical, both
    brightness: int = 0  # -100..100, 0 = no change
    contrast: int = 0
    saturation: int = 0
    speed: float = 1.0  # 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0
    keep_original: bool = True  # if True, create folder per download and keep original; else one file only
    aspect_ratio: str = "original"  # original, 16:9, 9:16, 4:3, 1:1
    bg_type: str = "blur"  # blur, color, stretch
    bg_color: str = "#000000"  # background color when bg_type == "color"

    def has_edits(self) -> bool:
        """True if any edit is requested (so we need post-process)."""
        return (
            bool(self.logo_path and Path(self.logo_path).is_file())
            or self.flip != "none"
            or self.brightness != 0
            or self.contrast != 0
            or self.saturation != 0
            or self.speed != 1.0
            or self.aspect_ratio != "original"
        )


LOGO_POSITIONS = ["Left", "Right", "Center", "Top", "Custom"]
FLIP_OPTIONS = ["None", "Horizontal", "Vertical", "Both"]
SPEED_OPTIONS = ["0.5x", "0.75x", "1x", "1.25x", "1.5x", "1.75x", "2x"]
SPEED_VALUES = [0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0]
ASPECT_RATIO_OPTIONS = ["Original", "16:9", "9:16", "4:3", "1:1"]
BG_TYPE_OPTIONS = ["Blur", "Color", "Stretch"]


# ── Color adjust popup ────────────────────────────────────────────────────────

class ColorAdjustDialog(QDialog):
    """Modal popup for brightness / contrast / saturation sliders."""

    def __init__(self, brightness: int, contrast: int, saturation: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Color Adjustment")
        self.setModal(True)
        self.setMinimumWidth(400)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 20)
        root.setSpacing(16)

        title = TitleLabel("Color Adjustment", self)
        root.addWidget(title)

        sub = BodyLabel("Adjust brightness, contrast and saturation for the output video.", self)
        sub.setWordWrap(True)
        root.addWidget(sub)
        root.addSpacing(4)

        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(14)

        def _make_row(label: str, value: int, row: int):
            lbl = BodyLabel(label, self)
            slider = Slider(Qt.Horizontal, self)
            slider.setRange(-100, 100)
            slider.setValue(value)
            slider.setMinimumWidth(200)
            val_lbl = BodyLabel(str(value), self)
            val_lbl.setFixedWidth(36)
            slider.valueChanged.connect(lambda v, l=val_lbl: l.setText(str(v)))
            grid.addWidget(lbl, row, 0)
            grid.addWidget(slider, row, 1)
            grid.addWidget(val_lbl, row, 2)
            return slider

        self._brightness_slider = _make_row("Brightness", brightness, 0)
        self._contrast_slider = _make_row("Contrast", contrast, 1)
        self._saturation_slider = _make_row("Saturation", saturation, 2)
        root.addLayout(grid)

        root.addSpacing(8)

        # Reset + OK / Cancel
        btn_row = QHBoxLayout()
        reset_btn = PushButton("Reset", self)
        reset_btn.setIcon(FluentIcon.SYNC)
        reset_btn.clicked.connect(self._reset)
        btn_row.addWidget(reset_btn)
        btn_row.addStretch(1)

        cancel_btn = PushButton("Cancel", self)
        cancel_btn.clicked.connect(self.reject)
        ok_btn = PrimaryPushButton("Apply", self)
        ok_btn.clicked.connect(self.accept)
        btn_row.addWidget(cancel_btn)
        btn_row.addSpacing(8)
        btn_row.addWidget(ok_btn)
        root.addLayout(btn_row)

    def _reset(self) -> None:
        self._brightness_slider.setValue(0)
        self._contrast_slider.setValue(0)
        self._saturation_slider.setValue(0)

    @property
    def brightness(self) -> int:
        return self._brightness_slider.value()

    @property
    def contrast(self) -> int:
        return self._contrast_slider.value()

    @property
    def saturation(self) -> int:
        return self._saturation_slider.value()


# ── Enhance feature card ──────────────────────────────────────────────────────

class DownloadEnhanceFeature(QWidget):
    """Enhance-download section: URL input + SettingCard options + color popup."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DownloadEnhanceFeature")

        # Stored color values (not directly bound to widgets all the time)
        self._brightness: int = 0
        self._contrast: int = 0
        self._saturation: int = 0

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(12)

        # ── URL card ──────────────────────────────────────────────────────
        url_card = CardWidget(self)
        url_lay = QVBoxLayout(url_card)
        url_lay.setSpacing(10)
        url_lay.addWidget(CardHeader(FluentIcon.SYNC, "Enhance — Download with stream edit", url_card))
        url_row = QHBoxLayout()
        url_row.addWidget(BodyLabel("URL", url_card))
        self._url_edit = LineEdit(url_card)
        self._url_edit.setPlaceholderText(
            "https://  —  Paste video URL, then configure options below …"
        )
        self._url_edit.setClearButtonEnabled(True)
        url_row.addWidget(self._url_edit, 1)
        url_lay.addLayout(url_row)
        outer.addWidget(url_card)

        # ── Options group ─────────────────────────────────────────────────
        self._group = SettingCardGroup("Stream edit options", self)

        # ── Logo expand group ─────────────────────────────────────────────
        self._logo_expand_card = ExpandGroupSettingCard(
            FluentIcon.PHOTO,
            "Logo overlay",
            "Overlay an image on the video — expand to configure",
            self,
        )

        # Sub-row 1: logo file path
        _logo_file_w = QWidget()
        _logo_file_lay = QHBoxLayout(_logo_file_w)
        _logo_file_lay.setContentsMargins(0, 0, 0, 0)
        _logo_file_lay.setSpacing(8)
        self._logo_edit = LineEdit()
        self._logo_edit.setPlaceholderText("No logo selected")
        self._logo_edit.setMinimumWidth(200)
        self._logo_edit.setClearButtonEnabled(True)
        self._logo_browse_btn = PushButton("Browse\u2026")
        self._logo_browse_btn.setIcon(FluentIcon.FOLDER)
        self._logo_browse_btn.clicked.connect(self._browse_logo)
        _logo_file_lay.addWidget(self._logo_edit, 1)
        _logo_file_lay.addWidget(self._logo_browse_btn)
        self._logo_expand_card.addGroup(
            FluentIcon.DOCUMENT, "Logo file", "PNG / JPG / WebP image path",
            _logo_file_w, stretch=1,
        )

        # Sub-row 2: logo size
        self._logo_size_spin = CompactSpinBox()
        self._logo_size_spin.setRange(10, 600)
        self._logo_size_spin.setValue(120)
        self._logo_size_spin.setSuffix(" px")
        self._logo_expand_card.addGroup(
            FluentIcon.ZOOM_IN, "Logo size", "Height in pixels — width auto-scales to preserve aspect ratio",
            self._logo_size_spin,
        )

        # Sub-row 3: position preset
        self._logo_position = ComboBox()
        self._logo_position.addItems(LOGO_POSITIONS)
        self._logo_position.setCurrentIndex(2)  # Center
        self._logo_position.setFixedWidth(150)
        self._logo_position.currentTextChanged.connect(self._on_logo_pos_changed)
        self._logo_expand_card.addGroup(
            FluentIcon.MOVE, "Position preset",
            "Anchor point on the frame — choose Custom for pixel-exact control",
            self._logo_position,
        )

        # Sub-row 4: custom X
        self._logo_x_spin = CompactSpinBox()
        self._logo_x_spin.setRange(0, 9999)
        self._logo_x_spin.setValue(10)
        self._logo_x_spin.setSuffix(" px")
        self._logo_x_group = self._logo_expand_card.addGroup(
            FluentIcon.RIGHT_ARROW, "Offset X", "Pixels from the left edge of the video",
            self._logo_x_spin,
        )
        self._logo_x_group.setEnabled(False)

        # Sub-row 5: custom Y
        self._logo_y_spin = CompactSpinBox()
        self._logo_y_spin.setRange(0, 9999)
        self._logo_y_spin.setValue(10)
        self._logo_y_spin.setSuffix(" px")
        self._logo_y_group = self._logo_expand_card.addGroup(
            FluentIcon.ARROW_DOWN, "Offset Y", "Pixels from the top edge of the video",
            self._logo_y_spin,
        )
        self._logo_y_group.setEnabled(False)

        self._group.addSettingCard(self._logo_expand_card)

        # Flip
        self._flip_card = SettingCard(
            FluentIcon.ROTATE,
            "Flip",
            "Mirror the source video (logo is never flipped)",
        )
        self._flip_combo = ComboBox()
        self._flip_combo.addItems(FLIP_OPTIONS)
        self._flip_combo.setFixedWidth(140)
        self._flip_card.hBoxLayout.addWidget(self._flip_combo)
        self._flip_card.hBoxLayout.addSpacing(16)
        self._group.addSettingCard(self._flip_card)

        # Speed
        self._speed_card = SettingCard(
            FluentIcon.SPEED_HIGH,
            "Playback speed",
            "Change the output video speed",
        )
        self._speed_combo = ComboBox()
        self._speed_combo.addItems(SPEED_OPTIONS)
        self._speed_combo.setCurrentIndex(2)  # 1x
        self._speed_combo.setFixedWidth(110)
        self._speed_card.hBoxLayout.addWidget(self._speed_combo)
        self._speed_card.hBoxLayout.addSpacing(16)
        self._group.addSettingCard(self._speed_card)

        # Aspect ratio + background fill expand group
        self._ar_expand_card = ExpandGroupSettingCard(
            FluentIcon.FIT_PAGE,
            "Aspect ratio",
            "Resize frame to a target ratio — fill empty space with blur, color, or stretch",
            self,
        )

        # Sub-row 1: target ratio
        self._ar_combo = ComboBox()
        self._ar_combo.addItems(ASPECT_RATIO_OPTIONS)
        self._ar_combo.setCurrentIndex(0)  # Original
        self._ar_combo.setFixedWidth(150)
        self._ar_combo.currentTextChanged.connect(self._on_aspect_ratio_changed)
        self._ar_expand_card.addGroup(
            FluentIcon.ZOOM, "Target ratio", "Select the output aspect ratio",
            self._ar_combo,
        )

        # Sub-row 2: background type
        self._bg_type_combo = ComboBox()
        self._bg_type_combo.addItems(BG_TYPE_OPTIONS)
        self._bg_type_combo.setCurrentIndex(0)  # Blur
        self._bg_type_combo.setFixedWidth(150)
        self._bg_type_combo.currentTextChanged.connect(self._on_bg_type_changed)
        self._ar_bg_type_group = self._ar_expand_card.addGroup(
            FluentIcon.TILES, "Background fill",
            "How to fill the empty space when content doesn't fit the target ratio",
            self._bg_type_combo,
        )
        self._ar_bg_type_group.setEnabled(False)

        # Sub-row 3: background color (only used when bg_type == Color)
        _bg_color_w = QWidget()
        _bg_color_lay = QHBoxLayout(_bg_color_w)
        _bg_color_lay.setContentsMargins(0, 0, 0, 0)
        _bg_color_lay.setSpacing(8)
        self._bg_color_edit = LineEdit()
        self._bg_color_edit.setPlaceholderText("#000000")
        self._bg_color_edit.setText("#000000")
        self._bg_color_edit.setFixedWidth(100)
        self._bg_color_edit.editingFinished.connect(self._save_config)
        self._bg_color_btn = PushButton("Pick…")
        self._bg_color_btn.setIcon(FluentIcon.PALETTE)
        self._bg_color_btn.clicked.connect(self._pick_bg_color)
        _bg_color_lay.addWidget(self._bg_color_edit)
        _bg_color_lay.addWidget(self._bg_color_btn)
        _bg_color_lay.addStretch()
        self._ar_bg_color_group = self._ar_expand_card.addGroup(
            FluentIcon.BRUSH, "Background color",
            "Color used when background fill is set to 'Color'",
            _bg_color_w,
        )
        self._ar_bg_color_group.setEnabled(False)

        self._group.addSettingCard(self._ar_expand_card)

        # Color adjust (popup)
        self._color_card = SettingCard(
            FluentIcon.PALETTE,
            "Color adjustment",
            "Brightness / Contrast / Saturation",
        )
        self._color_summary_lbl = BodyLabel("0 / 0 / 0")
        self._color_adjust_btn = PushButton("Adjust\u2026")
        self._color_adjust_btn.setIcon(FluentIcon.EDIT)
        self._color_adjust_btn.clicked.connect(self._open_color_dialog)
        self._color_card.hBoxLayout.addWidget(self._color_summary_lbl)
        self._color_card.hBoxLayout.addSpacing(12)
        self._color_card.hBoxLayout.addWidget(self._color_adjust_btn)
        self._color_card.hBoxLayout.addSpacing(16)
        self._group.addSettingCard(self._color_card)

        # Keep original
        self._keep_card = SettingCard(
            FluentIcon.SAVE,
            "Keep original",
            "Create a folder per download and keep both original and enhanced files",
        )
        self._keep_original_switch = SwitchButton()
        self._keep_original_switch.setChecked(True)
        self._keep_card.hBoxLayout.addWidget(self._keep_original_switch)
        self._keep_card.hBoxLayout.addSpacing(16)
        self._group.addSettingCard(self._keep_card)

        # Auto defaults
        # self._auto_card = SettingCard(
        #     FluentIcon.SYNC,
        #     "Auto (recommended defaults)",
        #     "Reset all options to sensible defaults in one click",
        # )
        # self._auto_switch = SwitchButton()
        # self._auto_switch.setChecked(False)
        # self._auto_card.hBoxLayout.addWidget(self._auto_switch)
        # self._auto_card.hBoxLayout.addSpacing(16)
        # self._group.addSettingCard(self._auto_card)

        outer.addWidget(self._group)

        # ── Load persisted state then wire auto-save ───────────────────────
        self._load_config()

        self._logo_edit.editingFinished.connect(self._save_config)
        self._logo_size_spin.valueChanged.connect(self._save_config)
        self._logo_x_spin.valueChanged.connect(self._save_config)
        self._logo_y_spin.valueChanged.connect(self._save_config)
        # logo_position already connected via currentTextChanged → _on_logo_pos_changed → _save_config
        self._flip_combo.currentIndexChanged.connect(self._save_config)
        self._speed_combo.currentIndexChanged.connect(self._save_config)
        self._keep_original_switch.checkedChanged.connect(self._save_config)
        # ar_combo already connected via currentTextChanged → _on_aspect_ratio_changed → _save_config
        # bg_type_combo already connected via currentTextChanged → _on_bg_type_changed → _save_config
        # _self._auto_switch.checkedChanged.connect(self._on_auto_changed)

    # ── Helpers ───────────────────────────────────────────────────────────

    def _color_summary(self) -> str:
        return f"B {self._brightness:+d}  /  C {self._contrast:+d}  /  S {self._saturation:+d}"

    def _open_color_dialog(self) -> None:
        dlg = ColorAdjustDialog(
            self._brightness, self._contrast, self._saturation, self.window()
        )
        if dlg.exec_() == QDialog.Accepted:
            self._brightness = dlg.brightness
            self._contrast = dlg.contrast
            self._saturation = dlg.saturation
            self._color_summary_lbl.setText(self._color_summary())
            self._save_config()

    def _on_logo_pos_changed(self, text: str) -> None:
        is_custom = text == "Custom"
        self._logo_x_group.setEnabled(is_custom)
        self._logo_y_group.setEnabled(is_custom)
        self._save_config()

    def _on_aspect_ratio_changed(self, text: str) -> None:
        is_original = text == "Original"
        self._ar_bg_type_group.setEnabled(not is_original)
        is_color = self._bg_type_combo.currentText() == "Color"
        self._ar_bg_color_group.setEnabled(not is_original and is_color)
        self._save_config()

    def _on_bg_type_changed(self, text: str) -> None:
        is_color = text == "Color"
        self._ar_bg_color_group.setEnabled(is_color)
        self._save_config()

    def _pick_bg_color(self) -> None:
        from PyQt5.QtGui import QColor
        current = self._bg_color_edit.text().strip() or "#000000"
        color = QColorDialog.getColor(QColor(current), self.window(), "Select background color")
        if color.isValid():
            self._bg_color_edit.setText(color.name())
            self._save_config()

    def _browse_logo(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select logo image",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.webp);;All files (*)",
        )
        if path:
            self._logo_edit.setText(path)
            self._save_config()

    def _on_auto_changed(self, checked: bool) -> None:
        if checked:
            self._logo_position.setCurrentText("Center")
            self._logo_size_spin.setValue(120)
            self._logo_x_spin.setValue(10)
            self._logo_y_spin.setValue(10)
            self._flip_combo.setCurrentIndex(0)       # None
            self._speed_combo.setCurrentIndex(2)      # 1x
            self._brightness = 0
            self._contrast = 0
            self._saturation = 0
            self._color_summary_lbl.setText(self._color_summary())
        self._save_config()

    # ── Persistence ───────────────────────────────────────────────────────

    def _load_config(self) -> None:
        """Restore all enhance options from settings on startup."""
        s = load_settings()
        self._logo_edit.setText(s.get("enhance_logo_path", ""))
        pos = s.get("enhance_logo_position", "center").capitalize()
        self._logo_position.setCurrentIndex(
            LOGO_POSITIONS.index(pos) if pos in LOGO_POSITIONS else 2
        )
        flip = s.get("enhance_flip", "none").capitalize()
        self._flip_combo.setCurrentIndex(
            FLIP_OPTIONS.index(flip) if flip in FLIP_OPTIONS else 0
        )
        speed = s.get("enhance_speed", 1.0)
        try:
            self._speed_combo.setCurrentIndex(SPEED_VALUES.index(speed))
        except ValueError:
            self._speed_combo.setCurrentIndex(2)
        self._logo_size_spin.setValue(int(s.get("enhance_logo_size", 120)))
        self._logo_x_spin.setValue(int(s.get("enhance_logo_x", 10)))
        self._logo_y_spin.setValue(int(s.get("enhance_logo_y", 10)))
        self._brightness = int(s.get("enhance_brightness", 0))
        self._contrast = int(s.get("enhance_contrast", 0))
        self._saturation = int(s.get("enhance_saturation", 0))
        self._color_summary_lbl.setText(self._color_summary())
        self._keep_original_switch.setChecked(s.get("enhance_keep_original", True))
        # Aspect ratio
        ar = s.get("enhance_aspect_ratio", "original")
        ar_cap = ar.upper() if ar in ("16:9", "9:16", "4:3", "1:1") else ar.capitalize()
        self._ar_combo.setCurrentIndex(
            ASPECT_RATIO_OPTIONS.index(ar_cap) if ar_cap in ASPECT_RATIO_OPTIONS else 0
        )
        bg_type = s.get("enhance_bg_type", "blur").capitalize()
        self._bg_type_combo.setCurrentIndex(
            BG_TYPE_OPTIONS.index(bg_type) if bg_type in BG_TYPE_OPTIONS else 0
        )
        self._bg_color_edit.setText(s.get("enhance_bg_color", "#000000"))
        # Apply custom X/Y visibility after all fields are set
        is_custom = self._logo_position.currentText() == "Custom"
        self._logo_x_group.setEnabled(is_custom)
        self._logo_y_group.setEnabled(is_custom)
        # Apply AR visibility
        is_original = self._ar_combo.currentText() == "Original"
        self._ar_bg_type_group.setEnabled(not is_original)
        is_color = self._bg_type_combo.currentText() == "Color"
        self._ar_bg_color_group.setEnabled(not is_original and is_color)

    def _save_config(self) -> None:
        """Persist all enhance options to settings."""
        opts = self.get_options()
        s = load_settings()
        s["enhance_logo_path"] = opts.logo_path
        s["enhance_logo_position"] = opts.logo_position
        s["enhance_logo_size"] = opts.logo_size
        s["enhance_logo_x"] = opts.logo_x
        s["enhance_logo_y"] = opts.logo_y
        s["enhance_flip"] = opts.flip
        s["enhance_speed"] = opts.speed
        s["enhance_brightness"] = opts.brightness
        s["enhance_contrast"] = opts.contrast
        s["enhance_saturation"] = opts.saturation
        s["enhance_keep_original"] = opts.keep_original
        s["enhance_aspect_ratio"] = opts.aspect_ratio
        s["enhance_bg_type"] = opts.bg_type
        s["enhance_bg_color"] = opts.bg_color
        save_settings(s)

    # ── Public API ────────────────────────────────────────────────────────

    def url(self) -> str:
        return self._url_edit.text().strip()

    def set_url(self, text: str) -> None:
        self._url_edit.setText(text)

    def get_options(self) -> EnhanceOptions:
        pos_idx = self._logo_position.currentIndex()
        logo_position = LOGO_POSITIONS[pos_idx].lower() if 0 <= pos_idx < len(LOGO_POSITIONS) else "center"
        flip_idx = self._flip_combo.currentIndex()
        flip = FLIP_OPTIONS[flip_idx].lower() if 0 <= flip_idx < len(FLIP_OPTIONS) else "none"
        speed_idx = self._speed_combo.currentIndex()
        speed = SPEED_VALUES[speed_idx] if 0 <= speed_idx < len(SPEED_VALUES) else 1.0
        ar_text = self._ar_combo.currentText()
        aspect_ratio = ar_text.lower() if ar_text == "Original" else ar_text
        bg_type = self._bg_type_combo.currentText().lower()
        return EnhanceOptions(
            logo_path=self._logo_edit.text().strip(),
            logo_position=logo_position,
            logo_size=self._logo_size_spin.value(),
            logo_x=self._logo_x_spin.value(),
            logo_y=self._logo_y_spin.value(),
            flip=flip,
            brightness=self._brightness,
            contrast=self._contrast,
            saturation=self._saturation,
            speed=speed,
            keep_original=self._keep_original_switch.isChecked(),
            aspect_ratio=aspect_ratio,
            bg_type=bg_type,
            bg_color=self._bg_color_edit.text().strip() or "#000000",
        )
