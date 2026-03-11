"""
Task queue core: validation, issue detection, and task row data.

Keeps UI-agnostic logic for:
- Detecting invalid / failed-metadata tasks (issue links)
- Building task row dict from URL and from yt-dlp metadata
- Supported file extensions for drag-and-drop
"""

from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from app.core.download import detect_platform


# Status strings (must match download_task_model)
STATUS_PENDING = "Pending"
STATUS_RUNNING = "Downloading"
STATUS_DONE = "Done"
STATUS_ERROR = "Error"
STATUS_CANCELED = "Canceled"

# Size placeholder when unknown
SIZE_PLACEHOLDER = "\u2014"  # em dash "—"

# File extensions for local drag-and-drop
VIDEO_EXTENSIONS = {
    "mp4", "mkv", "avi", "mov", "wmv", "flv", "webm", "m4v", "ts", "mpeg", "mpg",
}
AUDIO_EXTENSIONS = {
    "mp3", "aac", "wav", "flac", "ogg", "m4a", "opus", "wma",
}
SUPPORTED_EXTENSIONS = VIDEO_EXTENSIONS | AUDIO_EXTENSIONS


# ─── URL validation ────────────────────────────────────────────────────────

def is_http_url(url: str) -> bool:
    """True if string is a valid http or https URL."""
    if not url or not isinstance(url, str):
        return False
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        return False
    try:
        r = urlparse(url)
        return bool(r.netloc)
    except Exception:
        return False


# ─── Issue detection ────────────────────────────────────────────────────────

def is_invalid_url_task(task: dict | None) -> bool:
    """True if task has no valid http(s) URL (e.g. pasted plain text)."""
    if not task:
        return True
    url = (task.get("url") or "").strip()
    return not url or not url.startswith(("http://", "https://"))


def is_issue_task(task: dict | None) -> bool:
    """True if task is invalid or metadata fetch failed (title still URL, no size)."""
    if not task:
        return True
    if is_invalid_url_task(task):
        return True
    url = (task.get("url") or "").strip()
    title = (task.get("title") or "").strip()
    size = (task.get("size") or "").strip()
    status = task.get("status", STATUS_PENDING)
    if status != STATUS_PENDING:
        return False
    no_size = size in ("", "—", SIZE_PLACEHOLDER)
    title_looks_like_url = (
        title.startswith(("http://", "https://"))
        or (len(title) <= 80 and (url.startswith(title) or title in url))
    )
    return bool(no_size and title_looks_like_url)


# ─── URL → task row data ────────────────────────────────────────────────────

def resolve_host_from_url(url: str) -> str:
    """Return platform name or netloc for a URL."""
    platform = detect_platform(url)
    if platform and platform != "Unknown":
        return platform
    try:
        return urlparse(url).netloc.replace("www.", "")
    except Exception:
        return ""


def build_placeholder_title(canonical_url: str, max_len: int = 60) -> str:
    """Short placeholder title before metadata is fetched."""
    if len(canonical_url) <= max_len:
        return canonical_url
    return canonical_url[:max_len] + "…"


def prepare_url_task_row(canonical_url: str, path: str = "") -> dict[str, Any]:
    """Build initial task row dict for a normalized URL (before metadata)."""
    host = resolve_host_from_url(canonical_url)
    title = build_placeholder_title(canonical_url)
    return {
        "title": title,
        "host": host,
        "format": "",
        "path": path,
        "url": canonical_url,
    }


# ─── Metadata from yt-dlp info ──────────────────────────────────────────────

def extract_title_from_info(info: dict) -> str:
    """Title from yt-dlp extract_info."""
    return (info.get("title") or info.get("fulltitle") or "").strip()


def extract_uploader_from_info(info: dict) -> str:
    """Uploader/channel/artist from yt-dlp extract_info."""
    return (
        info.get("uploader") or info.get("channel") or info.get("artist") or ""
    ).strip()


def extract_filesize_from_info(info: dict) -> int | None:
    """Filesize in bytes from yt-dlp extract_info, or None."""
    fs = info.get("filesize") or info.get("filesize_approx")
    if fs is not None and isinstance(fs, (int, float)) and fs > 0:
        return int(fs)
    return None


def metadata_updates_from_info(info: dict) -> dict[str, Any]:
    """Build update dict for a task row from yt-dlp info (title, host, size)."""
    out: dict[str, Any] = {}
    title = extract_title_from_info(info)
    if title:
        out["title"] = title
    uploader = extract_uploader_from_info(info)
    if uploader:
        out["uploader"] = uploader  # caller can set host if missing
    size = extract_filesize_from_info(info)
    if size is not None:
        out["filesize"] = size  # caller formats with format_size
    return out


# ─── Path helpers ───────────────────────────────────────────────────────────

def resolve_task_path(file_path: str | None, path: str | None) -> str:
    """Preferred path for a task: file_path or path or empty."""
    for p in (file_path, path):
        if p and isinstance(p, str) and p.strip():
            return p.strip()
    return ""


def resolve_task_title(task: dict, fallback: str = "Unknown") -> str:
    """Title for display: title or basename of file_path/path or fallback."""
    title = (task.get("title") or "").strip()
    if title:
        return title
    path = resolve_task_path(task.get("file_path"), task.get("path"))
    if path:
        return Path(path).name or fallback
    return fallback


def dir_for_path(path_str: str) -> Path | None:
    """Directory containing the path (parent of file, or self if dir). Returns None if invalid."""
    if not path_str or not path_str.strip():
        return None
    p = Path(path_str.strip())
    if p.is_file():
        return p.parent
    if p.is_dir():
        return p
    return None


def build_playlist_task_entries(entries: list[dict]) -> list[dict[str, Any]]:
    """Build list of task dicts from playlist/channel entries (title, host, url)."""
    return [
        {
            "title": e.get("title") or e.get("url", ""),
            "host": e.get("uploader") or "",
            "url": e.get("url", ""),
        }
        for e in entries
        if e and e.get("url")
    ]
