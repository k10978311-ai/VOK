"""Language / translator utilities for VOK."""

import os

from PyQt5.QtCore import QLocale, QTranslator
from PyQt5.QtWidgets import QApplication

from app.common.paths import TRANSLATIONS_DIR

# Human-readable label → BCP-47 locale string (empty = system auto)
LANGUAGES: dict[str, str] = {
    "Auto (System)": "",
    "English": "en_US",
    "中文 (简体)": "zh_CN",
    "中文 (繁體)": "zh_TW",
    "日本語": "ja_JP",
    "Русский": "ru_RU",
    "Français": "fr_FR",
    "Deutsch": "de_DE",
    "Español": "es_ES",
    "Português": "pt_BR",
    "한국어": "ko_KR",
    "العربية": "ar_SA",
    "ភាសាខ្មែរ": "km_KH",
}

# Languages that have compiled .qm files bundled with the app.
AVAILABLE_LOCALES: frozenset[str] = frozenset(
    {"zh_CN", "ja_JP", "ko_KR", "ru_RU", "km_KH"}
)

# Internal attribute names used to keep translator references alive
_ATTR_FLUENT = "_vok_fluent_translator"
_ATTR_APP = "_vok_app_translator"


def apply_language(locale_name: str) -> None:
    """Install translators for *locale_name* (e.g. 'zh_CN').

    Pass an empty string or 'Auto' to follow the system locale.
    Translators are kept alive on the QApplication instance.
    """
    app = QApplication.instance()
    if app is None:
        return

    # Resolve locale
    if not locale_name or locale_name.lower() == "auto":
        locale = QLocale.system()
    else:
        locale = QLocale(locale_name)

    import qfluentwidgets as _qfw

    # 1) Remove and replace qfluentwidgets translator
    old_fluent: QTranslator | None = getattr(app, _ATTR_FLUENT, None)
    if old_fluent is not None:
        app.removeTranslator(old_fluent)

    fluent_translator = QTranslator(app)
    fluent_i18n = os.path.join(os.path.dirname(_qfw.__file__), "i18n")
    fluent_translator.load(locale, "qfluentwidgets", ".", fluent_i18n)
    app.installTranslator(fluent_translator)
    setattr(app, _ATTR_FLUENT, fluent_translator)

    # 2) Remove and replace app translator
    old_app: QTranslator | None = getattr(app, _ATTR_APP, None)
    if old_app is not None:
        app.removeTranslator(old_app)

    app_translator = QTranslator(app)
    if app_translator.load(locale, "vok", "_", str(TRANSLATIONS_DIR)):
        app.installTranslator(app_translator)
        setattr(app, _ATTR_APP, app_translator)
    else:
        setattr(app, _ATTR_APP, None)
