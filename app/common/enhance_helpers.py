"""Enhance helpers: build options, output paths, and video probing."""

from __future__ import annotations

import json
import os
import subprocess
import sys

from app.config import load_settings
from app.core.ffmpeg.cache import get_ffmpeg_path
from app.ui.components.download_enhance_feature import EnhanceOptions


def options_from_settings() -> EnhanceOptions:
    """Build EnhanceOptions directly from persisted settings (no widget dependency)."""
    s = load_settings()
    return EnhanceOptions(
        logo_path=s.get("enhance_logo_path", ""),
        logo_position=s.get("enhance_logo_position", "center"),
        logo_size=int(s.get("enhance_logo_size", 120)),
        logo_x=int(s.get("enhance_logo_x", 10)),
        logo_y=int(s.get("enhance_logo_y", 10)),
        flip=s.get("enhance_flip", "none"),
        speed=float(s.get("enhance_speed", 1.0)),
        brightness=int(s.get("enhance_brightness", 0)),
        contrast=int(s.get("enhance_contrast", 0)),
        saturation=int(s.get("enhance_saturation", 0)),
        keep_original=bool(s.get("enhance_keep_original", True)),
        aspect_ratio=s.get("enhance_aspect_ratio", "original"),
        bg_type=s.get("enhance_bg_type", "blur"),
        bg_color=s.get("enhance_bg_color", "#000000"),
    )


def build_output_path(input_path: str) -> str:
    """Return a non-colliding _enhanced.mp4 path beside the input file."""
    base, _ = os.path.splitext(input_path)
    candidate = f"{base}_enhanced.mp4"
    n = 2
    while os.path.exists(candidate):
        candidate = f"{base}_enhanced_{n}.mp4"
        n += 1
    return candidate


def probe_video_meta(path: str) -> tuple[str, float]:
    """Return (resolution_str, duration_secs) using ffprobe. Falls back to ('—', -1.0)."""
    try:
        ffmpeg = get_ffmpeg_path()
        ffprobe = os.path.join(os.path.dirname(ffmpeg), "ffprobe")
        if not os.path.isfile(ffprobe):
            ffprobe = "ffprobe"
        _flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        result = subprocess.run(
            [ffprobe, "-v", "quiet", "-print_format", "json",
             "-show_streams", "-show_format", path],
            capture_output=True, text=True, timeout=10,
            creationflags=_flags,
        )
        data = json.loads(result.stdout)
        duration = float(data.get("format", {}).get("duration", -1))
        resolution = "—"
        for s in data.get("streams", []):
            if s.get("codec_type") == "video":
                w, h = s.get("width", 0), s.get("height", 0)
                if w and h:
                    resolution = f"{w}\u00d7{h}"
                break
        return resolution, duration
    except Exception:
        return "—", -1.0
