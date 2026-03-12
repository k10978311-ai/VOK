# coding: utf-8
"""run_enhance — executes the ffmpeg subprocess for the enhance pipeline."""

import os
import subprocess
import sys
from typing import TYPE_CHECKING

from app.core.ffmpeg.cache import get_ffmpeg_path
from app.core.ffmpeg.manager import ffmpeg_available
from app.core.enhance.filters import _build_video_filters

if TYPE_CHECKING:
    from app.ui.components.download_enhance_feature import EnhanceOptions


def run_enhance(
    input_path: str,
    output_path: str,
    opts: "EnhanceOptions",
) -> tuple[bool, str, int]:
    """Run ffmpeg to apply logo, flip, color, speed.

    Returns
    -------
    (success: bool, message: str, output_size_bytes: int)
        output_size_bytes is -1 on failure.
    """
    if not ffmpeg_available():
        return False, "ffmpeg is not installed. Install ffmpeg for stream edit.", -1
    if not input_path or not os.path.isfile(input_path):
        return False, "Input file not found.", -1

    # libx264 only works with mp4/mkv/mov containers — remap incompatible extensions.
    _INCOMPATIBLE = {".webm", ".flv", ".ts", ".avi", ".ogg"}
    root, out_ext = os.path.splitext(output_path)
    if out_ext.lower() in _INCOMPATIBLE:
        output_path = root + ".mp4"

    ffmpeg = get_ffmpeg_path()
    has_logo = bool(opts.logo_path and os.path.isfile(opts.logo_path))
    video_filters = _build_video_filters(opts, has_logo)
    audio_filter = f"atempo={opts.speed}" if opts.speed != 1.0 else "copy"

    cmd = [ffmpeg, "-y", "-i", input_path]
    if has_logo:
        cmd.extend(["-i", opts.logo_path])
    cmd.extend([
        "-filter_complex", video_filters,
        "-map", "[vout]",
        "-map", "0:a?",
    ])
    if opts.speed != 1.0:
        cmd.extend(["-filter:a", audio_filter])
    else:
        cmd.extend(["-c:a", "copy"])
    cmd.extend([
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-movflags", "+faststart",
        output_path,
    ])

    try:
        _flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        proc = subprocess.run(
            cmd, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=600,
            creationflags=_flags,
        )
        if proc.returncode != 0:
            err = (proc.stderr or proc.stdout or "")[-800:]
            return False, f"ffmpeg failed: {err}", -1
        size = os.path.getsize(output_path) if os.path.isfile(output_path) else -1
        return True, "Enhance completed.", size
    except subprocess.TimeoutExpired:
        return False, "ffmpeg timed out.", -1
    except Exception as e:
        return False, str(e), -1
