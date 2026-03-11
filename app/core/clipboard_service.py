"""
Clipboard sync service: parse clipboard text into video/single-video URLs only.

- Allows only direct video links (no playlist, channel, profile, or group URLs).
- Supports multiple links at once (newline, comma, or space separated).
- Skips duplicates against an existing URL set.
- Optional domain filter (comma-separated) to allow only certain hosts.
"""

import re
from typing import Container

from app.core.download import (
    check_unsupported_url,
    detect_collection_url,
    normalize_url,
)


# Split on newlines, commas, or runs of spaces
_URL_SPLIT_RE = re.compile(r"[\n,\s]+")


def parse_urls_from_text(text: str) -> list[str]:
    """Split text into candidate URL strings (http/https only)."""
    if not text or not text.strip():
        return []
    raw = [s.strip() for s in _URL_SPLIT_RE.split(text.strip()) if s.strip()]
    return [u for u in raw if u.startswith(("http://", "https://"))]


def is_video_url(url: str) -> bool:
    """Return True if URL is allowed: single video link, not playlist/profile/unsupported."""
    u = url.strip()
    if not u.startswith(("http://", "https://")):
        return False
    if check_unsupported_url(u) is not None:
        return False
    if detect_collection_url(u):
        return False
    return True


def apply_domain_filter(urls: list[str], domain_filter: str) -> list[str]:
    """Keep only URLs whose host is in the comma-separated domain_filter (e.g. 'youtube.com,tiktok.com')."""
    if not domain_filter or not domain_filter.strip():
        return list(urls)
    allowed = [d.strip().lower() for d in domain_filter.split(",") if d.strip()]
    if not allowed:
        return list(urls)
    result = []
    for url in urls:
        url_lower = url.lower()
        if any(d in url_lower for d in allowed):
            result.append(url)
    return result


def get_video_urls_to_add(
    text: str,
    existing_urls: Container[str],
    *,
    domain_filter: str = "",
) -> list[str]:
    """
    Parse clipboard text into normalized video-only URLs, excluding duplicates.

    - Splits on newlines, commas, spaces.
    - Keeps only http(s) URLs that pass is_video_url (no playlist/profile/unsupported).
    - Normalizes each URL; skips if already in existing_urls.
    - Optionally filters by domain_filter (comma-separated domains).

    Returns:
        List of canonical URLs to add (order preserved, no duplicates).
    """
    raw = parse_urls_from_text(text)
    seen = set()
    to_add = []
    for u in raw:
        canonical, _ = normalize_url(u)
        if canonical in seen:
            continue
        if canonical in existing_urls:
            continue
        if not is_video_url(canonical):
            continue
        seen.add(canonical)
        to_add.append(canonical)
    if domain_filter:
        to_add = apply_domain_filter(to_add, domain_filter)
    return to_add
