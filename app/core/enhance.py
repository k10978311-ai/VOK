"""Post-download stream edit: ffmpeg overlay (logo), flip, color, speed."""

import os
import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from PyQt5.QtCore import QThread, pyqtSignal

if TYPE_CHECKING:
    from app.ui.components.download_enhance_feature import EnhanceOptions


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def _ar_filter_steps(opts: "EnhanceOptions", in_node: str, out_node: str) -> list[str]:
    """Return filter_complex steps for aspect ratio conversion.

    Returns an empty list when no AR change is needed (aspect_ratio == 'original').
    - blur:    scales source to fill frame (blurred), then overlays original centred
    - color:   pads with a solid colour (hex from opts.bg_color)
    - stretch: scales source to fill frame (distorted)
    """
    ar = getattr(opts, "aspect_ratio", "original")
    if ar == "original":
        return []

    _RATIOS = {"16:9": (16, 9), "9:16": (9, 16), "4:3": (4, 3), "1:1": (1, 1)}
    if ar not in _RATIOS:
        return []

    tw, th = _RATIOS[ar]
    ow = f"max(iw\\,ceil(ih*{tw}/{th}/2)*2)"
    oh = f"max(ih\\,ceil(iw*{th}/{tw}/2)*2)"

    bg_type = getattr(opts, "bg_type", "blur")
    
    # Extract and validate hex color more robustly
    raw_color = getattr(opts, "bg_color", "#000000") or "#000000"
    # Filter to only valid hex characters
    hex_color = "".join(c for c in raw_color if c in "0123456789ABCDEFabcdef")
    # Validate and normalize
    if not hex_color or len(hex_color) not in (3, 6):
        hex_color = "000000"  # fallback to black
    elif len(hex_color) == 3:
        hex_color = "".join(c * 2 for c in hex_color)

    if bg_type == "stretch":
        return [f"{in_node}scale={ow}:{oh}:force_original_aspect_ratio=disable[{out_node}]"]

    if bg_type == "color":
        return [
            f"{in_node}pad={ow}:{oh}:(ow-iw)/2:(oh-ih)/2:color=0x{hex_color}[{out_node}]"
        ]

    # blur (default): scale stretched + gblur as background, overlay original centred
    # Using gblur (Gaussian blur) with higher sigma for more visible blur effect
    return [
        f"{in_node}split=2[_ar_fg][_ar_bg]",
        f"[_ar_bg]scale={ow}:{oh}:force_original_aspect_ratio=disable,gblur=sigma=25[_ar_bgblur]",
        f"[_ar_bgblur][_ar_fg]overlay=(W-w)/2:(H-h)/2[{out_node}]",
    ]


def _build_video_filters(opts: "EnhanceOptions", has_logo: bool) -> str:
    """Build -filter_complex video part. Returns the filter string for [0:v] (and optionally [1:v] for logo).

    Flip is applied to the source video BEFORE logo overlay so the logo is
    never mirrored. Color and speed are applied to the composite afterwards.
    """
    # ── Flip (source-only) ────────────────────────────────────────────────
    flip_parts: list[str] = []
    if opts.flip == "horizontal":
        flip_parts.append("hflip")
    elif opts.flip == "vertical":
        flip_parts.append("vflip")
    elif opts.flip == "both":
        flip_parts.append("hflip,vflip")
    flip_filter = ",".join(flip_parts)  # "" if no flip

    # ── Color + speed (applied after overlay) ────────────────────────────
    post_parts: list[str] = []
    b = opts.brightness / 200.0
    c = 1.0 + opts.contrast / 200.0
    s = 1.0 + opts.saturation / 200.0
    if b != 0 or c != 1.0 or s != 1.0:
        post_parts.append(f"eq=brightness={b}:contrast={c}:saturation={s}")
    if opts.speed != 1.0:
        post_parts.append(f"setpts={1.0 / opts.speed}*PTS")
    post_filter = ",".join(post_parts)  # "" if no color/speed changes

    if not has_logo:
        # No logo — check whether we need AR conversion
        ar_steps = _ar_filter_steps(opts, "[0:v]", "v_ar")
        if ar_steps:
            # Need filter_complex even without logo
            steps: list[str] = []
            cur = "[0:v]"
            if flip_filter:
                steps.append(f"[0:v]{flip_filter}[vflip]")
                cur = "[vflip]"
            steps.extend(_ar_filter_steps(opts, cur, "v_ar"))
            cur = "[v_ar]"
            if post_filter:
                steps.append(f"{cur}{post_filter}[vout]")
            else:
                steps.append(f"{cur}copy[vout]")
            return ";".join(steps)
        # No AR change — simple single-filter vf chain
        all_parts = flip_parts + post_parts
        vf = ",".join(all_parts) if all_parts else "copy"
        return f"[0:v]{vf}[vout]"

    # ── With logo ─────────────────────────────────────────────────────────
    # Step 1: flip source only → [vsrc]
    # Step 2: scale logo       → [logo]
    # Step 3: overlay logo on flipped source → [v1]
    # Step 4: apply color / speed to composite → [vout]
    pos = opts.logo_position
    if pos == "custom":
        logo_x = max(0, getattr(opts, "logo_x", 10))
        logo_y = max(0, getattr(opts, "logo_y", 10))
        overlay_xy = f"{logo_x}:{logo_y}"
    elif pos == "left":
        overlay_xy = "10:10"
    elif pos == "right":
        overlay_xy = "main_w-overlay_w-10:10"
    elif pos == "top":
        overlay_xy = "(main_w-overlay_w)/2:10"
    else:
        overlay_xy = "(main_w-overlay_w)/2:(main_h-overlay_h)/2"

    logo_h = max(10, getattr(opts, "logo_size", 120))
    logo_scale = f"[1:v]scale=-1:{logo_h}[logo]"
    src_node = "[0:v]"

    steps: list[str] = [logo_scale]

    if flip_filter:
        steps.append(f"{src_node}{flip_filter}[vsrc]")
        src_node = "[vsrc]"

    # Apply aspect ratio AFTER flip, BEFORE logo overlay
    ar_steps = _ar_filter_steps(opts, src_node, "varat")
    if ar_steps:
        steps.extend(ar_steps)
        src_node = "[varat]"

    steps.append(f"{src_node}[logo]overlay={overlay_xy}[v1]")

    if post_filter:
        steps.append(f"[v1]{post_filter}[vout]")
    else:
        steps.append("[v1]copy[vout]")

    return ";".join(steps)


def run_enhance(
    input_path: str,
    output_path: str,
    opts: "EnhanceOptions",
) -> tuple[bool, str, int]:
    """Run ffmpeg to apply logo, flip, color, speed. Returns (success, message, output_size_bytes)."""
    if not ffmpeg_available():
        return False, "ffmpeg is not installed. Install ffmpeg for stream edit.", -1
    if not input_path or not os.path.isfile(input_path):
        return False, "Input file not found.", -1
    has_logo = bool(opts.logo_path and os.path.isfile(opts.logo_path))
    video_filters = _build_video_filters(opts, has_logo)
    # Audio: speed change
    audio_filter = f"atempo={opts.speed}" if opts.speed != 1.0 else "copy"
    # Build command
    cmd = [
        "ffmpeg",
        "-y",
        "-i", input_path,
    ]
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
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,
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


class EnhancePostProcessWorker(QThread):
    """Runs run_enhance in a background thread. Emits log_line and finished_signal."""

    log_line = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str, str, int)  # success, message, output_path, size_bytes

    def __init__(
        self,
        input_path: str,
        output_path: str,
        opts: "EnhanceOptions",
        job_id: str = "",
        parent=None,
    ):
        super().__init__(parent)
        self._input_path = input_path
        self._output_path = output_path
        self._opts = opts
        self._job_id = job_id
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        self.log_line.emit("[info] Enhance: applying logo, flip, color, speed…")
        success, message, size = run_enhance(
            self._input_path,
            self._output_path,
            self._opts,
        )
        if self._cancelled:
            self.finished_signal.emit(False, "Enhance cancelled.", "", -1)
            return
        self.log_line.emit(f"[info] {message}")
        self.finished_signal.emit(success, message, self._output_path if success else "", size)
