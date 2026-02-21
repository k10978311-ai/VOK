"""Social media scraper and analytics workers.

Workers
-------
MetaFetchWorker     — extract post metadata (views, likes, comments, followers …)
CommentsWorker      — scrape comments from a post
SearchWorker        — search a platform by keyword or hashtag
PlaylistFetchWorker — list playlist/channel entries for selective download
TranslateWorker     — translate text via MyMemory API (free, no key required)
"""

from PyQt5.QtCore import QThread, pyqtSignal

from app.core.download import normalize_url


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def fmt_num(n) -> str:
    """Format a large integer with K / M / B suffix."""
    if n is None:
        return "—"
    try:
        n = int(n)
    except (TypeError, ValueError):
        return str(n)
    if n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.1f}B"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def fmt_duration(seconds) -> str:
    """Format seconds as H:MM:SS or M:SS."""
    if not seconds:
        return "—"
    try:
        s = int(seconds)
    except (TypeError, ValueError):
        return "—"
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"


def fmt_date(date_str: str) -> str:
    """Convert YYYYMMDD → YYYY-MM-DD."""
    if not date_str or len(date_str) != 8:
        return date_str or "—"
    return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"


# ---------------------------------------------------------------------------
# MetaFetchWorker
# ---------------------------------------------------------------------------

class MetaFetchWorker(QThread):
    """Extract post/profile metadata via yt-dlp (no download)."""

    log_line = pyqtSignal(str)
    data_ready = pyqtSignal(dict)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, url: str, cookies_file: str = "", parent=None):
        super().__init__(parent)
        self.url = url.strip()
        self.cookies_file = cookies_file.strip()

    def run(self) -> None:
        if not self.url:
            self.finished_signal.emit(False, "No URL provided.")
            return
        try:
            import yt_dlp
        except ImportError:
            self.finished_signal.emit(False, "yt-dlp not installed.")
            return

        url, note = normalize_url(self.url)
        if note:
            self.log_line.emit(f"[info] {note}")

        opts: dict = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
        }
        if self.cookies_file:
            opts["cookiefile"] = self.cookies_file

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
            if info:
                self.data_ready.emit(dict(info))
                self.finished_signal.emit(True, "Metadata fetched successfully.")
            else:
                self.finished_signal.emit(False, "No data returned.")
        except Exception as exc:
            self.log_line.emit(f"[error] {exc}")
            self.finished_signal.emit(False, str(exc))


# ---------------------------------------------------------------------------
# CommentsWorker
# ---------------------------------------------------------------------------

class CommentsWorker(QThread):
    """Scrape comments for a post via yt-dlp."""

    log_line = pyqtSignal(str)
    comments_ready = pyqtSignal(list)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, url: str, max_comments: int = 100, cookies_file: str = "", parent=None):
        super().__init__(parent)
        self.url = url.strip()
        self.max_comments = max(1, max_comments)
        self.cookies_file = cookies_file.strip()

    def run(self) -> None:
        if not self.url:
            self.finished_signal.emit(False, "No URL provided.")
            return
        try:
            import yt_dlp
        except ImportError:
            self.finished_signal.emit(False, "yt-dlp not installed.")
            return

        url, note = normalize_url(self.url)
        if note:
            self.log_line.emit(f"[info] {note}")

        opts: dict = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "getcomments": True,
            "extractor_args": {
                "youtube": {
                    "comment_sort": ["top"],
                    "max_comments": [str(self.max_comments)],
                },
                "tiktok": {"max_comments": [str(self.max_comments)]},
            },
        }
        if self.cookies_file:
            opts["cookiefile"] = self.cookies_file

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
            comments = list((info or {}).get("comments") or [])
            self.comments_ready.emit(comments)
            self.finished_signal.emit(True, f"Fetched {len(comments)} comment(s).")
        except Exception as exc:
            self.log_line.emit(f"[error] {exc}")
            self.finished_signal.emit(False, str(exc))


# ---------------------------------------------------------------------------
# SearchWorker
# ---------------------------------------------------------------------------

# Maps platform name → yt-dlp search prefix
_SEARCH_PREFIXES: dict[str, str] = {
    "YouTube":    "ytsearch20:",
    "TikTok":     "ttsearch20:",
    "SoundCloud": "scsearch20:",
    "Bilibili":   "bilisearch20:",
}


class SearchWorker(QThread):
    """Search a platform for content by keyword or hashtag."""

    log_line = pyqtSignal(str)
    results_ready = pyqtSignal(list)
    finished_signal = pyqtSignal(bool, str)

    def __init__(
        self,
        keyword: str,
        platform: str = "YouTube",
        is_hashtag: bool = False,
        cookies_file: str = "",
        parent=None,
    ):
        super().__init__(parent)
        self.keyword = keyword.strip()
        self.platform = platform
        self.is_hashtag = is_hashtag
        self.cookies_file = cookies_file.strip()

    def run(self) -> None:
        if not self.keyword:
            self.finished_signal.emit(False, "No keyword provided.")
            return
        try:
            import yt_dlp
        except ImportError:
            self.finished_signal.emit(False, "yt-dlp not installed.")
            return

        term = self.keyword
        if self.is_hashtag and not term.startswith("#"):
            term = f"#{term}"

        prefix = _SEARCH_PREFIXES.get(self.platform, "ytsearch20:")
        query = f"{prefix}{term}"

        opts: dict = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "extract_flat": True,
        }
        if self.cookies_file:
            opts["cookiefile"] = self.cookies_file

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(query, download=False)
            entries = list((info or {}).get("entries") or [])
            results = []
            for e in entries:
                if e:
                    results.append({
                        "title":       e.get("title") or "",
                        "uploader":    e.get("uploader") or e.get("channel") or "",
                        "view_count":  e.get("view_count") or 0,
                        "like_count":  e.get("like_count") or 0,
                        "duration":    e.get("duration") or 0,
                        "upload_date": e.get("upload_date") or "",
                        "url":         e.get("webpage_url") or e.get("url") or "",
                    })
            self.results_ready.emit(results)
            self.finished_signal.emit(True, f"Found {len(results)} result(s).")
        except Exception as exc:
            self.log_line.emit(f"[error] {exc}")
            self.finished_signal.emit(False, str(exc))


# ---------------------------------------------------------------------------
# PlaylistFetchWorker
# ---------------------------------------------------------------------------

class PlaylistFetchWorker(QThread):
    """List playlist / channel entries without downloading (selective download)."""

    log_line = pyqtSignal(str)
    entries_ready = pyqtSignal(list)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, url: str, cookies_file: str = "", parent=None):
        super().__init__(parent)
        self.url = url.strip()
        self.cookies_file = cookies_file.strip()
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        if not self.url:
            self.finished_signal.emit(False, "No URL provided.")
            return
        try:
            import yt_dlp
        except ImportError:
            self.finished_signal.emit(False, "yt-dlp not installed.")
            return

        url, note = normalize_url(self.url)
        if note:
            self.log_line.emit(f"[info] {note}")

        opts: dict = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "extract_flat": True,
            "noplaylist": False,
        }
        if self.cookies_file:
            opts["cookiefile"] = self.cookies_file

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
            entries: list[dict] = []
            if info:
                if "entries" in info:
                    for e in (info["entries"] or []):
                        if self._cancelled:
                            break
                        if e:
                            entries.append({
                                "title":       e.get("title") or "Unknown",
                                "url":         e.get("webpage_url") or e.get("url") or "",
                                "duration":    e.get("duration") or 0,
                                "uploader":    e.get("uploader") or e.get("channel") or "",
                                "upload_date": e.get("upload_date") or "",
                            })
                else:
                    entries.append({
                        "title":       info.get("title") or "Unknown",
                        "url":         info.get("webpage_url") or url,
                        "duration":    info.get("duration") or 0,
                        "uploader":    info.get("uploader") or "",
                        "upload_date": info.get("upload_date") or "",
                    })
            self.entries_ready.emit(entries)
            self.finished_signal.emit(True, f"Found {len(entries)} item(s).")
        except Exception as exc:
            self.log_line.emit(f"[error] {exc}")
            self.finished_signal.emit(False, str(exc))


# ---------------------------------------------------------------------------
# TranslateWorker
# ---------------------------------------------------------------------------

class TranslateWorker(QThread):
    """Translate text via MyMemory API (free — 1 000 req/day, no key required)."""

    log_line = pyqtSignal(str)
    translation_ready = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)

    LANGUAGES: dict[str, str] = {
        "English":    "en",
        "Spanish":    "es",
        "French":     "fr",
        "German":     "de",
        "Japanese":   "ja",
        "Korean":     "ko",
        "Chinese":    "zh",
        "Arabic":     "ar",
        "Portuguese": "pt",
        "Russian":    "ru",
        "Italian":    "it",
        "Hindi":      "hi",
        "Turkish":    "tr",
        "Vietnamese": "vi",
        "Thai":       "th",
        "Indonesian": "id",
    }

    def __init__(self, text: str, target_lang: str = "en", parent=None):
        super().__init__(parent)
        self.text = text.strip()
        self.target_lang = target_lang

    def run(self) -> None:
        if not self.text:
            self.finished_signal.emit(False, "No text to translate.")
            return
        try:
            import json
            import urllib.parse
            import urllib.request

            params = urllib.parse.urlencode({
                "q": self.text[:500],
                "langpair": f"autodetect|{self.target_lang}",
            })
            req_url = f"https://api.mymemory.translated.net/get?{params}"
            with urllib.request.urlopen(req_url, timeout=15) as resp:
                data = json.loads(resp.read().decode())
            translated = (data.get("responseData") or {}).get("translatedText", "")
            if translated and "PLEASE SELECT TWO DISTINCT" not in translated.upper():
                self.translation_ready.emit(translated)
                self.finished_signal.emit(True, "Translated successfully.")
            else:
                self.finished_signal.emit(False, "Translation failed — try again or check language pair.")
        except Exception as exc:
            self.log_line.emit(f"[error] {exc}")
            self.finished_signal.emit(False, str(exc))
