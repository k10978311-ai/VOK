"""
In-app auto-updater: check GitHub Releases, download installer, run silent install.

Uses GitHub API for latest release; installer is expected to be built with Inno Setup
(supports /VERYSILENT, /SUPPRESSMSGBOXES). AppMutex in the installer allows clean upgrade.
"""

import os
import subprocess
import sys
from typing import Tuple

# GitHub repo: owner/repo for API and releases
GITHUB_REPO = "k10978311-ai/VOK"
GITHUB_API_LATEST = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
REQUEST_TIMEOUT = 10
DOWNLOAD_CHUNK_SIZE = 8192


def _parse_version(version_str: str) -> Tuple[int, ...]:
    """Convert '0.1.2' or 'v0.1.2' to (0, 1, 2) for comparison."""
    s = (version_str or "").strip().lstrip("v")
    parts = []
    for part in s.split("."):
        try:
            parts.append(int(part))
        except ValueError:
            parts.append(0)
    return tuple(parts) if parts else (0, 0, 0)


def _version_greater(latest: str, current: str) -> bool:
    """True if latest > current (e.g. 0.1.2 > 0.1.1)."""
    return _parse_version(latest) > _parse_version(current)


def check_update(current_version: str) -> Tuple[str | None, str | None]:
    """
    Check GitHub Releases for a version newer than current_version.

    Returns
    -------
    (latest_version, download_url) if update available, else (None, None).
    """
    try:
        import requests
    except ImportError:
        return None, None

    try:
        r = requests.get(GITHUB_API_LATEST, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        data = r.json()
    except Exception:
        return None, None

    tag = (data.get("tag_name") or "").strip().lstrip("v")
    if not tag or not _version_greater(tag, current_version):
        return None, None

    assets = data.get("assets") or []
    for asset in assets:
        name = (asset.get("name") or "").lower()
        if name.endswith(".exe") and "install" in name:
            url = asset.get("browser_download_url")
            if url:
                return tag, url
    if assets:
        url = assets[0].get("browser_download_url")
        if url:
            return tag, url
    return None, None


def download_update(url: str, progress_callback=None) -> str | None:
    """
    Download the installer to TEMP and return its path.

    progress_callback(current_bytes, total_bytes or None) is optional.
    """
    try:
        import requests
    except ImportError:
        return None

    try:
        r = requests.get(url, stream=True, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        total = int(r.headers.get("content-length") or 0)
    except Exception:
        return None

    temp_dir = os.environ.get("TEMP", os.path.expandvars("%TEMP%"))
    path = os.path.join(temp_dir, "VOK-Update.exe")
    written = 0
    try:
        with open(path, "wb") as f:
            for chunk in r.iter_content(chunk_size=DOWNLOAD_CHUNK_SIZE):
                if not chunk:
                    continue
                f.write(chunk)
                written += len(chunk)
                if progress_callback and callable(progress_callback):
                    progress_callback(written, total if total else None)
        return path
    except Exception:
        try:
            os.remove(path)
        except OSError:
            pass
        return None


def install_update(installer_path: str) -> None:
    """
    Run the Inno Setup installer silently and exit the app.

    Uses /VERYSILENT /SUPPRESSMSGBOXES /NORESTART.
    Does not return; calls sys.exit(0) after launching the installer.
    """
    if not installer_path or not os.path.isfile(installer_path):
        return
    try:
        subprocess.Popen(
            [installer_path, "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"],
            shell=False,
        )
    except Exception:
        pass
    sys.exit(0)
