"""Downloader view helpers: format options and platform host icons."""

from PyQt5.QtGui import QIcon
from qfluentwidgets import FluentIcon
from qfluentwidgets.common.icon import toQIcon

from app.common.paths import ICONS_DIR

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

# Platform display name -> icon filename in resources/icons (README.md)
PLATFORM_ICON_NAMES = {
    "YouTube": "youtube.png",
    "tiktok": "tiktok.png",
    "Douyin": "douyin.png",
    "Kuaishou": "kuaishou.png",
    "Instagram": "instagram.png",
    "Facebook": "facebook.png",
    "Pinterest": "pinterest.png",
    "Twitter/X": "twitter.png",
    "VK": "vk.png",
}


def host_icon(platform: str) -> QIcon:
    """Return QIcon for platform from resources/icons, or FluentIcon.GLOBE as fallback."""
    name = PLATFORM_ICON_NAMES.get(platform)
    if name:
        path = ICONS_DIR / name
        if path.exists():
            icon = QIcon(str(path))
            if not icon.isNull():
                return icon
    return toQIcon(FluentIcon.GLOBE)
