"""VOK Studio: Video enhancement workspace with three-panel layout."""

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout
from qfluentwidgets import (
    BodyLabel,
    CardWidget,
    ComboBox,
    FluentIcon,
    LargeTitleLabel,
    LineEdit,
    PrimaryPushButton,
    PushButton,
    StrongBodyLabel,
)

from app.common.paths import PROJECT_ROOT
from app.ui.components import CardHeader

from .base import BaseView


class VokStudioView(BaseView):
    """Three-panel workspace for video enhancement and style generation."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("VOK Studio")
        # Set content margins
        self._layout.setContentsMargins(24, 20, 24, 24)

        # Title section
        title = LargeTitleLabel("VOK Studio", self)
        self._layout.addWidget(title)

        subtitle = BodyLabel(
            "Enhance videos with AI-powered tools and generate style presets.",
            self,
        )
        self._layout.addWidget(subtitle)
        self._layout.addSpacing(8)

        # Three-panel layout
        self._build_three_panel_layout()
        self._layout.addStretch(1)

    def _build_three_panel_layout(self):
        """Create left, center, and right panels."""
        panels_layout = QHBoxLayout()
        panels_layout.setSpacing(16)

        # Left panel - Controls & Settings
        self._left_panel = self._create_left_panel()
        panels_layout.addWidget(self._left_panel, stretch=2)

        # Center panel - Preview & Main Content
        self._center_panel = self._create_center_panel()
        panels_layout.addWidget(self._center_panel, stretch=3)

        # Right panel - Properties & Options
        self._right_panel = self._create_right_panel()
        panels_layout.addWidget(self._right_panel, stretch=2)

        self._layout.addLayout(panels_layout)

    def _create_left_panel(self):
        """Create left panel for controls and settings."""
        card = CardWidget(self)
        card.setMinimumWidth(200)
        layout = QVBoxLayout(card)
        layout.setSpacing(12)

        layout.addWidget(CardHeader(FluentIcon.SETTING, "Controls", card))

        # Enhancement options
        layout.addWidget(StrongBodyLabel("Enhancement", card))
        
        upscale_btn = PushButton("AI Upscale", card)
        upscale_btn.setIcon(FluentIcon.ZOOM_IN)
        layout.addWidget(upscale_btn)

        denoise_btn = PushButton("Denoise", card)
        denoise_btn.setIcon(FluentIcon.BRUSH)
        layout.addWidget(denoise_btn)

        stabilize_btn = PushButton("Stabilize", card)
        stabilize_btn.setIcon(FluentIcon.ALIGNMENT)
        layout.addWidget(stabilize_btn)

        layout.addSpacing(16)

        # Format & Crop section
        layout.addWidget(StrongBodyLabel("Format & Crop", card))
        
        layout.addWidget(BodyLabel("Aspect Ratio:", card))
        self._ratio_combo = ComboBox(card)
        self._ratio_combo.addItems(["16:9", "9:16", "1:1", "4:3", "21:9", "Original"])
        self._ratio_combo.setCurrentIndex(0)
        layout.addWidget(self._ratio_combo)

        layout.addSpacing(16)

        # Media & Style section
        layout.addWidget(StrongBodyLabel("Media & Style", card))

        layout.addWidget(BodyLabel("Media Type:", card))
        self._media_combo = ComboBox(card)
        self._media_combo.addItems(["Image", "Video", "Gradient", "Color"])
        self._media_combo.setCurrentIndex(0)
        layout.addWidget(self._media_combo)

        layout.addWidget(BodyLabel("Background:", card))
        self._background_combo = ComboBox(card)
        self._background_combo.addItems(["Gradient", "Color", "Image", "Transparent"])
        self._background_combo.setCurrentIndex(0)
        layout.addWidget(self._background_combo)

        layout.addWidget(BodyLabel("Object Fit:", card))
        self._object_fit_combo = ComboBox(card)
        self._object_fit_combo.addItems(["Contain", "Cover", "Fill", "Scale Down"])
        self._object_fit_combo.setCurrentIndex(0)
        layout.addWidget(self._object_fit_combo)

        layout.addWidget(BodyLabel("Frame Fit:", card))
        self._frame_fit_combo = ComboBox(card)
        self._frame_fit_combo.addItems(["Contain", "Cover"])
        self._frame_fit_combo.setCurrentIndex(0)
        layout.addWidget(self._frame_fit_combo)

        layout.addWidget(BodyLabel("Content Blur:", card))
        self._blur_combo = ComboBox(card)
        self._blur_combo.addItems(["Off", "Low", "Medium", "High"])
        self._blur_combo.setCurrentIndex(0)
        layout.addWidget(self._blur_combo)

        layout.addWidget(BodyLabel("Custom Color:", card))
        self._color_input = LineEdit(card)
        self._color_input.setPlaceholderText("#RRGGBB")
        layout.addWidget(self._color_input)

        layout.addWidget(BodyLabel("Gradient Preset:", card))
        self._gradient_combo = ComboBox(card)
        self._gradient_combo.addItems(["Sunset", "Ocean", "Neon", "Mono"])
        self._gradient_combo.setCurrentIndex(0)
        layout.addWidget(self._gradient_combo)

        layout.addWidget(BodyLabel("Audio Enhance:", card))
        self._audio_combo = ComboBox(card)
        self._audio_combo.addItems(["Off", "Voice Boost", "Noise Reduce", "Music Boost"])
        self._audio_combo.setCurrentIndex(0)
        layout.addWidget(self._audio_combo)

        layout.addStretch(1)
        return card

    def _create_center_panel(self):
        """Create center panel for preview and main content."""
        card = CardWidget(self)
        card.setMinimumWidth(400)
        layout = QVBoxLayout(card)
        layout.setSpacing(12)

        layout.addWidget(CardHeader(FluentIcon.VIDEO, "Preview", card))

        # Preview area with default image
        preview_area = CardWidget(card)
        preview_area.setMinimumHeight(300)
        preview_layout = QVBoxLayout(preview_area)
        preview_layout.setAlignment(Qt.AlignCenter)
        
        # Default preview image
        self._preview_label = QLabel(preview_area)
        self._preview_label.setAlignment(Qt.AlignCenter)
        self._preview_label.setScaledContents(False)
        
        # Load default preview image
        default_image_path = PROJECT_ROOT / "resources" / "images" / "image_sample.png"
        if default_image_path.exists():
            pixmap = QPixmap(str(default_image_path))
            if not pixmap.isNull():
                # Scale to reasonable preview size
                scaled_pixmap = pixmap.scaled(
                    400, 300, 
                    Qt.KeepAspectRatio, 
                    Qt.SmoothTransformation
                )
                self._preview_label.setPixmap(scaled_pixmap)
        else:
            # Fallback text if image not found
            self._preview_label.setText("🎬")
            self._preview_label.setStyleSheet("font-size: 72px;")
        
        preview_layout.addWidget(self._preview_label)

        layout.addWidget(preview_area)

        # Action buttons
        action_row = QHBoxLayout()
        action_row.setSpacing(8)

        preview_btn = PushButton("Preview", card)
        preview_btn.setIcon(FluentIcon.PLAY)
        action_row.addWidget(preview_btn)

        apply_btn = PushButton("Apply", card)
        action_row.addWidget(apply_btn)

        action_row.addStretch(1)

        save_btn = PrimaryPushButton("Save JSON", card)
        save_btn.setIcon(FluentIcon.SAVE)
        action_row.addWidget(save_btn)

        layout.addLayout(action_row)
        return card

    def _create_right_panel(self):
        """Create right panel for properties and options."""
        card = CardWidget(self)
        card.setMinimumWidth(200)
        layout = QVBoxLayout(card)
        layout.setSpacing(12)

        layout.addWidget(CardHeader(FluentIcon.DOCUMENT, "Config Summary", card))

        # Config summary section
        layout.addWidget(StrongBodyLabel("Current Config", card))

        info_items = [
            ("Media:", "Image"),
            ("Ratio:", "16:9"),
            ("Object Fit:", "Contain"),
            ("Background:", "Gradient"),
            ("Audio:", "Off"),
        ]
        
        for label_text, value_text in info_items:
            info_row = QHBoxLayout()
            info_row.setSpacing(8)
            info_row.addWidget(BodyLabel(label_text, card))
            info_row.addWidget(BodyLabel(value_text, card))
            info_row.addStretch(1)
            layout.addLayout(info_row)

        layout.addSpacing(16)

        # Presets
        layout.addWidget(StrongBodyLabel("Style Presets", card))

        preset_btn = PushButton("Load Preset", card)
        preset_btn.setIcon(FluentIcon.FOLDER)
        layout.addWidget(preset_btn)

        save_preset_btn = PushButton("Save Preset", card)
        save_preset_btn.setIcon(FluentIcon.SAVE)
        layout.addWidget(save_preset_btn)

        layout.addSpacing(8)
        layout.addWidget(BodyLabel("JSON config cached in app data", card))

        layout.addStretch(1)
        return card
