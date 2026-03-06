# coding: utf-8
from enum import Enum

from qfluentwidgets import FluentIconBase, getIconColor, Theme


class Icon(FluentIconBase, Enum):

    SELECT = "Select"
    SETTINGS = "Settings"
    SETTINGS_FILLED = "SettingsFilled"
    CLOUD_DOWNLOAD = "CloudDownload"
    CLOUD_DOWNLOAD_FILLED = "CloudDownloadFilled"

    def path(self, theme=Theme.AUTO):
        return f":/app/images/icons/{self.value}_{getIconColor(theme)}.svg"


class Ico(FluentIconBase, Enum):

    M3U8DL = "M3U8DL"

    def path(self, theme=Theme.AUTO):
        return f":/app/images/icos/{self.value}.ico"


class PNG(FluentIconBase, Enum):

    SHAKA_PACKAGER = "ShakaPackager"

    def path(self, theme=Theme.AUTO):
        return f":/app/images/png/{self.value}.png"


class Logo(FluentIconBase, Enum):

    KEY = "Key"
    GEAR = "Gear"
    FILM = "Film"
    MOON = "Moon"
    KNOT = "Knot"
    LINK = "Link"
    GLOBE = "Globe"
    WHALE = "Whale"
    LABEL = "Label"
    BROOM = "Broom"
    TIMER = "Timer"
    INBOX = "Inbox"
    BENTO = "Bento"
    PIZZA = "Pizza"
    LEDGER = "Ledger"
    POSTAL = "Postal"
    PLANET = "Planet"
    SHIELD = "Shield"
    COOKIE = "Cookie"
    HAMMER = "Hammer"
    OFFICE = "Office"
    PENCIL = "Pencil"
    PUZZLE = "Puzzle"
    FFMPEG = "FFmpeg"
    MONKEY = "Monkey"
    FOLDER = "Folder"
    ROCKET = "Rocket"
    SCROLL = "Scroll"
    WINDOW = "Window"
    CONTROL = "Control"
    CYCLONE = "Cyclone"
    ALEMBIC = "Alembic"
    BANDAGE = "Bandage"
    PACKAGE = "Package"
    SYRINGE = "Syringe"
    UNLOCKED = "Unlocked"
    AIRPLANE = "Airplane"
    CALENDAR = "Calendar"
    BOOKMARK = "Bookmark"
    TERMINAL = "Terminal"
    JOYSTICK = "Joystick"
    BAR_CHART = "BarChart"
    SMILEFACE = "Smileface"
    HOURGLASS = "Hourglass"
    PROJECTOR = "Projector"
    WASTEBASKET = "Wastebasket"
    VIDEO_CAMERA = "VideoCamera"
    CARD_FILE_BOX = "CardFileBox"
    VIDEOCASSETTE = "Videocassette"

    def path(self, theme=Theme.AUTO) -> str:
        return f":/app/images/logo/{self.value}.svg"
