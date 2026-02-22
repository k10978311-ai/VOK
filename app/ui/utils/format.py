"""Formatting and text utilities for the UI."""

import re

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences from console output."""
    return ANSI_RE.sub("", text)


def format_size(size_bytes: int) -> str:
    """Format byte count as human-readable (e.g. 1.5 MB). Returns '—' if size_bytes < 0."""
    if size_bytes < 0:
        return "—"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size_bytes < 1024:
            if unit == "B":
                return f"{int(size_bytes)} B"
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"
