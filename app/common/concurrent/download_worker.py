# coding: utf-8
"""DownloadWorker — runs yt-dlp in a QThread with progress and log signals."""

import os
from pathlib import Path
from typing import Callable

from PyQt5.QtCore import QThread, pyqtSignal

from app.common.paths import get_default_downloads_dir
from app.core.download import (
    _impersonate_available,
    _strip_ansi,
    check_unsupported_url,
    detect_platform,
    normalize_url,
)
from app.core.ffmpeg.manager import ffmpeg_available as _ffmpeg_available, ffmpeg_manager

# Emit ffmpeg / impersonation hints only once per session to avoid log spam
_ffmpeg_hint_shown: bool = False
_impersonate_hint_shown: bool = False


def _fmt_bytes(n: float) -> str:
    """Format a byte count as a short human-readable string (e.g. '12.3MB')."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{int(n)}{unit}" if unit == "B" else f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}PB"


def _fmt_speed(bps: float | None) -> str:
    """Format bytes-per-second as a speed string (e.g. '3.2MB/s')."""
    if not bps or bps < 0:
        return "0MB/s"
    for unit in ("B/s", "KB/s", "MB/s", "GB/s"):
        if bps < 1024:
            return f"{int(bps)}{unit}" if unit == "B/s" else f"{bps:.1f}{unit}"
        bps /= 1024
    return f"{bps:.1f}TB/s"


def _fmt_eta(secs: int | None) -> str:
    """Format seconds remaining as HH:MM:SS."""
    if secs is None or secs < 0:
        return "--:--"
    h, rem = divmod(int(secs), 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def _unique_path(path: str) -> str:
    """Return *path* unchanged if it doesn't exist, otherwise append (2), (3) … until unique."""
    if not os.path.exists(path):
        return path
    p = Path(path)
    stem, suffix = p.stem, p.suffix
    counter = 2
    while True:
        candidate = p.with_name(f"{stem} ({counter}){suffix}")
        if not candidate.exists():
            return str(candidate)
        counter += 1




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
    # (pct 0–1, speed_str, eta_str, current_size_str, total_size_str)
    progress_detail = pyqtSignal(float, str, str, str, str)
    finished_signal = pyqtSignal(bool, str, str, int)  # success, message, filepath, size_bytes (-1 if unknown)

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
        self.output_dir = output_dir or str(get_default_downloads_dir())
        self.format_key = format_key
        self.single_video = single_video
        self.concurrent_fragments = max(1, min(16, int(concurrent_fragments)))
        self.cookies_file = cookies_file.strip() if cookies_file else ""
        self.job_id = job_id or url[:80]
        self._cancelled = False
        self._final_path = ""
        self._final_size = -1

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        if not self.url:
            self.finished_signal.emit(False, "No URL provided.", "", -1)
            return
        try:
            import yt_dlp
        except ImportError:
            self.finished_signal.emit(False, "yt-dlp not installed. Run: pip install yt-dlp", "", -1)
            return

        # YoutubeDL subclass: intercepts prepare_filename to add (2)/(3) when file already exists.
        class _UniqueYDL(yt_dlp.YoutubeDL):
            def prepare_filename(self, info_dict, dir_type="", warn=False):
                name = super().prepare_filename(info_dict, dir_type=dir_type, warn=warn)
                # Only de-duplicate the primary output, not fragment/temp paths
                if not dir_type and name:
                    name = _unique_path(name)
                return name

        # Rewrite embed/modal URLs to canonical form before yt-dlp sees them.
        url, rewrite_note = normalize_url(self.url)
        if rewrite_note:
            self.log_line.emit(f"[info] {rewrite_note}")

        # Fail fast with a clear message for known-unsupported URLs (avoids generic timeout).
        unsupported_msg = check_unsupported_url(url)
        if unsupported_msg:
            self.log_line.emit(f"[error] {unsupported_msg}")
            self.finished_signal.emit(False, unsupported_msg, "", -1)
            return

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

        import re as _re
        _fragment_re = _re.compile(r'\.f\d+\.[a-z0-9]+$', _re.IGNORECASE)

        def progress_hook(d: dict):
            if self._cancelled:
                raise yt_dlp.utils.DownloadCancelled()
            status = d.get("status")
            if status == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                done = d.get("downloaded_bytes", 0) or 0
                pct = (done / total) if total else 0.0
                if total:
                    self.progress.emit(pct)
                speed_str = _fmt_speed(d.get("speed"))
                eta_str   = _fmt_eta(d.get("eta"))
                cur_str   = _fmt_bytes(done) if done else "0B"
                tot_str   = _fmt_bytes(total) if total else "?"
                self.progress_detail.emit(pct, speed_str, eta_str, cur_str, tot_str)
            elif status == "finished":
                self.progress.emit(1.0)
                filename = d.get("filename", "")
                # Skip intermediate fragment files (.f251.webm, .f140.mp4, etc.)
                # The real final path is set by postprocessor_hook after merging.
                if filename and os.path.isfile(filename) and not _fragment_re.search(filename):
                    self._final_path = filename
                    try:
                        self._final_size = os.path.getsize(filename)
                    except OSError:
                        self._final_size = -1

        def postprocessor_hook(d: dict):
            """Fired after each postprocessor (merge, convert, etc.).
            Captures the final output filepath once ffmpeg merging is done.
            """
            if d.get("status") == "finished":
                info = d.get("info_dict", {})
                # filepath is set for MergeFormat / FFmpegMerger
                final = info.get("filepath") or info.get("_filename")
                if final and os.path.isfile(final):
                    self._final_path = final
                    try:
                        self._final_size = os.path.getsize(final)
                    except OSError:
                        pass

        def log_emit(msg: str):
            self.log_line.emit(_strip_ansi(msg))

        class LogLogger:
            def __init__(self, emit: Callable[[str], None]):
                self._emit = emit

            def debug(self, msg): self._emit(msg)
            def info(self, msg): self._emit(msg)

            def warning(self, msg: str) -> None:
                global _impersonate_hint_shown
                m = msg.lower()
                if "impersonation" in m and "no impersonate target" in m:
                    if not _impersonate_hint_shown:
                        _impersonate_hint_shown = True
                        self._emit(
                            "[info] TikTok: for best compatibility install curl_cffi: "
                            'pip install "yt-dlp[curl-cffi]"'
                        )
                    return
                self._emit(f"[warning] {msg}")

            def error(self, msg): self._emit(f"[error] {msg}")

        # Resolve ffmpeg binary once (system PATH → imageio-ffmpeg fallback)
        _ffmpeg_path: str | None = None
        try:
            _ffmpeg_path = ffmpeg_manager.get()
        except Exception:
            pass

        # If chosen format requires merging but ffmpeg is missing, use single-stream fallback
        global _ffmpeg_hint_shown
        if "+" in fkey and not _ffmpeg_path:
            if not _ffmpeg_hint_shown:
                _ffmpeg_hint_shown = True
                log_emit(
                    "[warning] ffmpeg is not installed; merging video+audio is unavailable. "
                    "Using best single stream. Install ffmpeg for best quality."
                )
            fkey = "best/b"

        opts: dict = {
            "outtmpl": out_tmpl,
            "format": fkey,
            "progress_hooks": [progress_hook],
            "postprocessor_hooks": [postprocessor_hook],
            "logger": LogLogger(log_emit),
            "noprogress": False,
            "noplaylist": self.single_video,
            "socket_timeout": 120,
            "retries": 5,
            "fragment_retries": 5,
            "concurrent_fragment_downloads": self.concurrent_fragments,
            # Sanitize filenames for Windows to prevent shutil.move errors with special chars
            # (dots/parens in titles confuse yt-dlp's fragment temp-dir naming on Windows)
            "windowsfilenames": True,
        }

        if _ffmpeg_path:
            opts["ffmpeg_location"] = _ffmpeg_path

        # Use browser impersonation when available (helps TikTok and other sites)
        if _impersonate_available():
            try:
                opts["impersonate"] = "chrome"
            except Exception:
                pass

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
            with _UniqueYDL(opts) as ydl:
                ydl.download([url])
            if self._cancelled:
                self.finished_signal.emit(False, "Cancelled.", "", -1)
            else:
                self.finished_signal.emit(
                    True, "Download completed.", self._final_path, self._final_size
                )
        except yt_dlp.utils.DownloadCancelled:
            self.finished_signal.emit(False, "Cancelled.", "", -1)
        except Exception as exc:
            log_emit(str(exc))
            self.finished_signal.emit(False, str(exc), "", -1)
