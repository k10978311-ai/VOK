"""Downloader view helpers: format options and platform host icons."""

from PyQt5.QtGui import QIcon
from qfluentwidgets import FluentIcon
from qfluentwidgets.common.icon import toQIcon

from app.common.paths import ICONS_DIR, get_host_icons_cache_dir

DOWNLOAD_FORMATS = [
    "Best (video+audio)",
    "HD 1080p",
    "HD 720p",
    "4K / 2160p",
    "Best video",
    "Best audio",
    "Video (mp4)",
    "Audio (mp3)",
    "Photo / Image",
]

PLATFORM_ICON_NAMES = {
    "YouTube": "youtube.png",
    "TikTok": "tiktok.png",
    "Douyin": "douyin.png",
    "Kuaishou": "kuaishou.png",
    "Instagram": "instagram.png",
    "Facebook": "facebook.png",
    "Pinterest": "pinterest.png",
    "Twitter/X": "twitter.png",
    "VK": "vk.png",
}


def host_icon(platform: str) -> QIcon:
    """Return QIcon for platform: built-in names, then host icon cache, else globe fallback."""
    if not platform:
        return toQIcon(FluentIcon.GLOBE)
    name = PLATFORM_ICON_NAMES.get(platform)
    if name:
        path = ICONS_DIR / name
        if path.exists():
            icon = QIcon(str(path))
            if not icon.isNull():
                return icon
    # Use cached host icon (from extract_host service) if present
    try:
        from app.core.extract_host import get_cached_icon_path
        cache_dir = get_host_icons_cache_dir()
        cached = get_cached_icon_path(platform, cache_dir)
        if cached is not None:
            icon = QIcon(str(cached))
            if not icon.isNull():
                return icon
    except Exception:
        pass
    return toQIcon(FluentIcon.GLOBE)
