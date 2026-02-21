"""Single-download worker: yt-dlp in a thread with progress and log signals.

Supported platforms include (but are not limited to):
  YouTube, TikTok, Douyin, Kuaishou, Instagram, Facebook, Pinterest,
  Twitter/X, ok.ru, VK, Twitch, Vimeo, Dailymotion, SoundCloud,
  Bilibili, Reddit, and 1 000+ more via yt-dlp's extractor library.

For platforms that require authentication (e.g. Instagram stories,
ok.ru private videos) pass a Netscape-format cookies file via `cookies_file`.
"""

import os
import re
from typing import Callable
from urllib.parse import parse_qs, urlparse

from PyQt5.QtCore import QThread, pyqtSignal

from app.common.paths import DOWNLOADS_DIR

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

# Domains whose extractors are confirmed working with yt-dlp
SUPPORTED_DOMAINS = (
    "youtube.com", "youtu.be",
    "tiktok.com",
    "douyin.com",
    "kuaishou.com", "kwai.com",
    "instagram.com",
    "facebook.com",
    "pinterest.com", "pin.it",
    "twitter.com", "x.com",
    "ok.ru",
    "vk.com", "vkvideo.ru",
    "twitch.tv",
    "vimeo.com",
    "dailymotion.com",
    "soundcloud.com",
    "bilibili.com",
    "reddit.com",
)

# ---------------------------------------------------------------------------
# URL normalizers
# Each entry is (pattern, replacement_fn).  The first match wins.
# These fix embed/modal/share URLs that yt-dlp's extractors don't accept.
# ---------------------------------------------------------------------------
_URL_RULES: list[tuple[re.Pattern, "Callable[[re.Match], str]"]] = [
    # Douyin jingxuan/featured page with modal_id query param
    #   https://www.douyin.com/jingxuan?modal_id=7602920755290033448
    #   → https://www.douyin.com/video/7602920755290033448
    (
        re.compile(r"douyin\.com/[^?#]*\?.*modal_id=(\d+)", re.I),
        lambda m: f"https://www.douyin.com/video/{m.group(1)}",
    ),
    # Douyin share short-links  iesdouyin.com/share/video/ID/
    (
        re.compile(r"iesdouyin\.com/share/video/(\d+)", re.I),
        lambda m: f"https://www.douyin.com/video/{m.group(1)}",
    ),
    # TikTok share/embed  vm.tiktok.com or vt.tiktok.com (short links — keep as-is,
    # yt-dlp follows redirects; only the modal pattern needs rewriting)
    # VK clip embed  vk.com/clip-OWNER_ID  → vk.com/video-OWNER_ID  (same content)
    (
        re.compile(r"(https?://(?:www\.)?vk\.com/)clip(-\d+_\d+)", re.I),
        lambda m: f"{m.group(1)}video{m.group(2)}",
    ),
]


def normalize_url(url: str) -> tuple[str, str | None]:
    """Rewrite known embed/modal URLs to their canonical yt-dlp-compatible form.

    Returns
    -------
    (canonical_url, note)
        note is a human-readable explanation when a rewrite happened, else None.
    """
    stripped = url.strip()
    for pattern, rewrite in _URL_RULES:
        m = pattern.search(stripped)
        if m:
            canonical = rewrite(m)
            return canonical, f"URL rewritten → {canonical}"
    return stripped, None


def _strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text)


_DOMAIN_LABELS: dict[str, str] = {
    "youtu.be": "YouTube",
    "youtube.com": "YouTube",
    "kwai.com": "Kuaishou",
    "kuaishou.com": "Kuaishou",
    "pin.it": "Pinterest",
    "pinterest.com": "Pinterest",
    "twitter.com": "Twitter/X",
    "x.com": "Twitter/X",
    "vkvideo.ru": "VK",
    "vk.com": "VK",
}


def detect_platform(url: str) -> str:
    """Return a short platform name from the URL, or 'Unknown'."""
    url_lower = url.lower()
    for domain in SUPPORTED_DOMAINS:
        if domain in url_lower:
            if domain in _DOMAIN_LABELS:
                return _DOMAIN_LABELS[domain]
            return domain.split(".")[0].capitalize()
    return "Unknown"


class DownloadWorker(QThread):
    """Runs yt-dlp in a background thread.

    Signals
    -------
    log_line      str          — one line of console output
    progress      float        — 0.0 – 1.0 download progress
    finished_signal (bool, str) — (success, message)
    """

    log_line = pyqtSignal(str)
    progress = pyqtSignal(float)
    finished_signal = pyqtSignal(bool, str)

    def __init__(
        self,
        url: str,
        output_dir: str,
        format_key: str,
        single_video: bool = True,
        concurrent_fragments: int = 4,
        cookies_file: str = "",
        job_id: str | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.url = url.strip()
        self.output_dir = output_dir or str(DOWNLOADS_DIR)
        self.format_key = format_key
        self.single_video = single_video
        self.concurrent_fragments = max(1, min(16, int(concurrent_fragments)))
        self.cookies_file = cookies_file.strip() if cookies_file else ""
        self.job_id = job_id or url[:80]
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
            self.finished_signal.emit(False, "yt-dlp not installed. Run: pip install yt-dlp")
            return

        # Rewrite embed/modal URLs to canonical form before yt-dlp sees them.
        url, rewrite_note = normalize_url(self.url)
        if rewrite_note:
            self.log_line.emit(f"[info] {rewrite_note}")

        os.makedirs(self.output_dir, exist_ok=True)
        out_tmpl = os.path.join(self.output_dir, "%(title)s.%(ext)s")

        format_map = {
            "Best (video+audio)": "bv*+ba/b",
            "HD 1080p": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
            "HD 720p": "bestvideo[height<=720]+bestaudio/best[height<=720]",
            "4K / 2160p": "bestvideo[height<=2160]+bestaudio/best[height<=2160]",
            "Best video": "bv",
            "Best audio": "ba",
            "Video (mp4)": "bv[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/b",
            "Audio (mp3)": "ba[ext=m4a]/ba/b",
            "Photo / Image": "bv*+ba/b",
        }
        fkey = format_map.get(self.format_key, "bv*+ba/b")
        is_mp3 = self.format_key == "Audio (mp3)"
        is_photo = self.format_key == "Photo / Image"

        def progress_hook(d: dict):
            if self._cancelled:
                raise yt_dlp.utils.DownloadCancelled()
            status = d.get("status")
            if status == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                done = d.get("downloaded_bytes", 0)
                if total:
                    self.progress.emit(done / total)
            elif status == "finished":
                self.progress.emit(1.0)

        def log_emit(msg: str):
            self.log_line.emit(_strip_ansi(msg))

        class LogLogger:
            def __init__(self, emit: Callable[[str], None]):
                self._emit = emit

            def debug(self, msg): self._emit(msg)
            def info(self, msg): self._emit(msg)
            def warning(self, msg): self._emit(f"[warning] {msg}")
            def error(self, msg): self._emit(f"[error] {msg}")

        opts: dict = {
            "outtmpl": out_tmpl,
            "format": fkey,
            "progress_hooks": [progress_hook],
            "logger": LogLogger(log_emit),
            "noprogress": False,
            "noplaylist": self.single_video,
            "socket_timeout": 120,
            "retries": 5,
            "fragment_retries": 5,
            "concurrent_fragment_downloads": self.concurrent_fragments,
        }

        if self.cookies_file and os.path.isfile(self.cookies_file):
            opts["cookiefile"] = self.cookies_file
            log_emit(f"[info] Using cookies: {self.cookies_file}")

        if is_mp3:
            opts["postprocessors"] = [
                {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}
            ]

        if is_photo:
            opts["writethumbnail"] = True

        platform = detect_platform(url)
        log_emit(f"[info] Platform detected: {platform}")

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
            if self._cancelled:
                self.finished_signal.emit(False, "Cancelled.")
            else:
                self.finished_signal.emit(True, "Download completed.")
        except yt_dlp.utils.DownloadCancelled:
            self.finished_signal.emit(False, "Cancelled.")
        except Exception as exc:
            log_emit(str(exc))
            self.finished_signal.emit(False, str(exc))
