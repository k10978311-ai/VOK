# coding: utf-8
"""Common utilities: file names, JSON, URLs, explorer, process execution, proxy."""

import os
import re
import sys
from json import loads
from pathlib import Path
from typing import Union

from PyQt5.QtCore import QDir, QFile, QFileInfo, QProcess, QStandardPaths, QUrl
from PyQt5.QtGui import QDesktopServices


def adjustFileName(name: str) -> str:
    """Normalize a file name for safe use on disk."""
    name = re.sub(r'[\\/:*?"<>|\r\n\s]+', "_", name.strip()).strip()
    return name.rstrip(".")


def readFile(filePath: str) -> str:
    """Read file contents as UTF-8 string."""
    f = QFile(filePath)
    if not f.open(QFile.ReadOnly):
        return ""
    data = f.readAll().data().decode("utf-8", errors="replace")
    f.close()
    return data


def loadJsonData(filePath: str):
    """Load JSON from file."""
    return loads(readFile(filePath))


def removeFile(filePath: Union[str, Path]) -> None:
    """Remove file if it exists; ignore errors."""
    try:
        os.remove(filePath)
    except OSError:
        pass


def openUrl(url: str) -> bool:
    """Open URL in default app (browser or local file)."""
    if not url.startswith("http"):
        if not os.path.exists(url):
            return False
        QDesktopServices.openUrl(QUrl.fromLocalFile(url))
    else:
        QDesktopServices.openUrl(QUrl(url))
    return True


def showInFolder(path: Union[str, Path]) -> bool:
    """Reveal file or folder in system file explorer."""
    if not os.path.exists(path):
        return False
    if isinstance(path, Path):
        path = str(path.absolute())
    if not path or path.lower().startswith("http"):
        return False

    info = QFileInfo(path)
    if sys.platform == "win32":
        args = [QDir.toNativeSeparators(path)]
        if not info.isDir():
            args.insert(0, "/select,")
        QProcess.startDetached("explorer", args)
    elif sys.platform == "darwin":
        args = [
            "-e", "tell application \"Finder\"",
            "-e", "activate",
            "-e", f'select POSIX file "{path}"',
            "-e", "end tell",
            "-e", "return",
        ]
        QProcess.execute("/usr/bin/osascript", args)
    else:
        url = QUrl.fromLocalFile(path if info.isDir() else info.path())
        QDesktopServices.openUrl(url)
    return True


def runProcess(
    executable: Union[str, Path],
    args=None,
    timeout: int = 5000,
    cwd: Union[str, Path, None] = None,
) -> str:
    """Run process and return stdout as UTF-8 string."""
    process = QProcess()
    if cwd:
        process.setWorkingDirectory(str(cwd))
    process.start(str(executable).replace("\\", "/"), args or [])
    process.waitForFinished(timeout)
    out = process.readAllStandardOutput()
    return out.data().decode("utf-8", errors="replace")


def runDetachedProcess(
    executable: Union[str, Path],
    args=None,
    cwd: Union[str, Path, None] = None,
) -> None:
    """Start process detached (no wait)."""
    process = QProcess()
    if cwd:
        process.setWorkingDirectory(str(cwd))
    process.startDetached(str(executable).replace("\\", "/"), args or [])


def getSystemProxy() -> str:
    """Return system HTTP proxy URL if set; otherwise empty string or env proxy."""
    if sys.platform == "win32":
        try:
            import winreg
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                enabled, _ = winreg.QueryValueEx(key, "ProxyEnable")
                if enabled:
                    return "http://" + winreg.QueryValueEx(key, "ProxyServer")[0]
        except (OSError, ValueError):
            pass
    elif sys.platform == "darwin":
        try:
            s = os.popen("scutil --proxy").read()
            info = dict(re.findall(r"(?m)^\s+([A-Z]\w+)\s+:\s+(\S+)", s))
            if info.get("HTTPEnable") == "1":
                return f"http://{info.get('HTTPProxy', '')}:{info.get('HTTPPort', '')}"
            if info.get("ProxyAutoConfigEnable") == "1":
                return info.get("ProxyAutoConfigURLString", "")
        except (OSError, KeyError):
            pass
    return os.environ.get("http_proxy", "") or os.environ.get("HTTP_PROXY", "")


# ── File types ─────────────────────────────────────────────────────────────────

VIDEO_EXTENSIONS = {".mp4", ".mkv", ".webm", ".avi", ".mov", ".m4v", ".wmv", ".flv"}

# ── Pagination ─────────────────────────────────────────────────────────────────

PAGE_SIZE = 50

# ── Job status constants ───────────────────────────────────────────────────────

ST_PENDING = "Pending"
ST_QUEUED  = "Queued"
ST_RUNNING = "Running"
ST_DONE    = "Done"
ST_ERROR   = "Error"

STATUS_COLOR: dict[str, str] = {
    ST_PENDING: "#888888",
    ST_QUEUED:  "#AAAAAA",
    ST_RUNNING: "#3B9EFF",
    ST_DONE:    "#4CAF50",
    ST_ERROR:   "#F44336",
}


# ── Format helpers ─────────────────────────────────────────────────────────────

def fmt_duration(secs: float) -> str:
    if secs < 0:
        return "\u2014"
    m, s = int(secs) // 60, int(secs) % 60
    return f"{m}m {s:02d}s" if m else f"{s}s"


def fmt_eta(secs: float, status: str) -> str:
    """Rough estimate: ~0.5\u00d7 realtime for libx264 fast. Only shown for pending/queued."""
    if status in (ST_RUNNING, ST_DONE, ST_ERROR) or secs < 0:
        return "\u2014"
    est = max(1.0, secs * 0.5)
    m, s = int(est) // 60, int(est) % 60
    return f"~{m}m {s:02d}s" if m else f"~{s}s"
