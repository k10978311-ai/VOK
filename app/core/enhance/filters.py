# coding: utf-8
"""ffmpeg filter-graph builders for the enhance pipeline.

Functions
---------
_ar_filter_steps(opts, in_node, out_node) → list[str]
    Returns filter_complex steps for aspect-ratio conversion.

_build_video_filters(opts, has_logo) → str
    Assembles the full -filter_complex video string.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.ui.components.download_enhance_feature import EnhanceOptions


def _ar_filter_steps(opts: "EnhanceOptions", in_node: str, out_node: str) -> list[str]:
    """Return filter_complex steps for aspect ratio conversion.

    Returns an empty list when no AR change is needed (aspect_ratio == 'original').
    Modes: blur (default), color, stretch.
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

    raw_color = getattr(opts, "bg_color", "#000000") or "#000000"
    hex_color = "".join(c for c in raw_color if c in "0123456789ABCDEFabcdef")
    if not hex_color or len(hex_color) not in (3, 6):
        hex_color = "000000"
    elif len(hex_color) == 3:
        hex_color = "".join(c * 2 for c in hex_color)

    if bg_type == "stretch":
        return [f"{in_node}scale={ow}:{oh}:force_original_aspect_ratio=disable[{out_node}]"]

    if bg_type == "color":
        return [
            f"{in_node}pad={ow}:{oh}:(ow-iw)/2:(oh-ih)/2:color=0x{hex_color}[{out_node}]"
        ]

    # blur (default):
    # Background → cover-scale (preserve AR, fill canvas), center-crop to exact size, heavy blur.
    #   After force_original_aspect_ratio=increase one dimension equals the target exactly and
    #   the other is ≥ target.  min(iw, ceil(ih*tw/th/2)*2) / min(ih, ceil(iw*th/tw/2)*2)
    #   evaluated on the *scaled* iw/ih always resolves to the exact canvas dimensions.
    # Foreground → contain-scale (preserve AR, fit inside canvas), centred on blurred bg.
    crop_w = f"min(iw\\,ceil(ih*{tw}/{th}/2)*2)"
    crop_h = f"min(ih\\,ceil(iw*{th}/{tw}/2)*2)"
    return [
        f"{in_node}split=2[_ar_bg_src][_ar_fg_src]",
        f"[_ar_bg_src]scale={ow}:{oh}:force_original_aspect_ratio=increase,crop={crop_w}:{crop_h},gblur=sigma=40[_ar_bg]",
        f"[_ar_fg_src]scale={ow}:{oh}:force_original_aspect_ratio=decrease,setsar=1[_ar_fg]",
        f"[_ar_bg][_ar_fg]overlay=(W-w)/2:(H-h)/2[{out_node}]",
    ]


def _build_video_filters(opts: "EnhanceOptions", has_logo: bool) -> str:
    """Build -filter_complex video part.

    Order: flip source → AR conversion → logo overlay → color/speed.
    """
    # ── Flip ─────────────────────────────────────────────────────────────
    flip_parts: list[str] = []
    if opts.flip == "horizontal":
        flip_parts.append("hflip")
    elif opts.flip == "vertical":
        flip_parts.append("vflip")
    elif opts.flip == "both":
        flip_parts.append("hflip,vflip")
    flip_filter = ",".join(flip_parts)

    # ── Color + speed ─────────────────────────────────────────────────────
    post_parts: list[str] = []
    b = opts.brightness / 200.0
    c = 1.0 + opts.contrast / 200.0
    s = 1.0 + opts.saturation / 200.0
    if b != 0 or c != 1.0 or s != 1.0:
        post_parts.append(f"eq=brightness={b}:contrast={c}:saturation={s}")
    if opts.speed != 1.0:
        post_parts.append(f"setpts={1.0 / opts.speed}*PTS")
    post_filter = ",".join(post_parts)

    if not has_logo:
        cur = "[0:v]"
        steps: list[str] = []
        if flip_filter:
            steps.append(f"[0:v]{flip_filter}[vflip]")
            cur = "[vflip]"
        ar_steps = _ar_filter_steps(opts, cur, "v_ar")
        if ar_steps:
            steps.extend(ar_steps)
            cur = "[v_ar]"
            if post_filter:
                steps.append(f"{cur}{post_filter}[vout]")
                return ";".join(steps)
            # no post-filter: rename label inline via null
            steps[-1] = steps[-1].replace("[v_ar]", "[vout]")
            return ";".join(steps)
        # no AR change
        if steps:  # flip was applied
            if post_filter:
                steps.append(f"{cur}{post_filter}[vout]")
            else:
                steps[-1] = steps[-1].replace("[vflip]", "[vout]")
            return ";".join(steps)
        all_parts = flip_parts + post_parts
        vf = ",".join(all_parts) if all_parts else "copy"
        return f"[0:v]{vf}[vout]"

    # ── With logo ─────────────────────────────────────────────────────────
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
    steps: list[str] = [f"[1:v]scale=-1:{logo_h}[logo]"]
    src_node = "[0:v]"

    if flip_filter:
        steps.append(f"{src_node}{flip_filter}[vsrc]")
        src_node = "[vsrc]"

    ar_steps = _ar_filter_steps(opts, src_node, "varat")
    if ar_steps:
        steps.extend(ar_steps)
        src_node = "[varat]"

    steps.append(f"{src_node}[logo]overlay={overlay_xy}[v1]")

    if post_filter:
        steps.append(f"[v1]{post_filter}[vout]")
    else:
        # rename v1 → vout directly in the last overlay step
        steps[-1] = steps[-1].replace("[v1]", "[vout]")

    return ";".join(steps)
