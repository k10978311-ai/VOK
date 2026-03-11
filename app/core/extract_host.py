"""
Site Icon Fetcher Service
Extracts host from URLs and fetches site favicons/icons.
Icons are stored in a cache; if one exists for the host it is reused.
When no icon is found, an existing default icon from the cache is used.
"""

import re
import time
import logging
import argparse
from pathlib import Path
from urllib.parse import urlparse

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:
    raise SystemExit("Install dependencies: uv add requests")

try:
    from app.common.paths import get_host_icons_cache_dir, RESOURCES_DIR
except ImportError:
    get_host_icons_cache_dir = None
    RESOURCES_DIR = None

# ─── Logging Setup ────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("icon_fetcher.log", encoding="utf-8"),
    ],
)

log = logging.getLogger("icon_fetcher")


# ─── HTTP Session ──────────────────────────────────────────────────────────────

def make_session(timeout: int = 10) -> requests.Session:
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (compatible; IconFetcher/1.0)"
    })
    session.timeout = timeout
    return session


# ─── Core Functions ────────────────────────────────────────────────────────────

def extract_host(url: str) -> str | None:
    """Extract and return the host (scheme + netloc) from a URL."""
    url = url.strip()
    if not re.match(r"^https?://", url, re.IGNORECASE):
        url = "https://" + url
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if not host:
        log.warning(f"Could not parse host from: {url!r}")
        return None
    # Return base origin (scheme + host)
    return f"{parsed.scheme}://{host}"


def _safe_host_name(host: str) -> str:
    """Safe filesystem name from host (e.g. www.example.com -> www_example_com)."""
    return re.sub(r"[^\w.-]", "_", host)


# Cache lookup: check for existing icon file for this host
_CACHE_EXTENSIONS = ("ico", "png", "gif", "jpg", "jpeg", "svg")


def get_cached_icon_path(host: str, cache_dir: Path) -> Path | None:
    """Return path to a cached icon for host if one exists, else None."""
    base = _safe_host_name(host)
    for ext in _CACHE_EXTENSIONS:
        path = cache_dir / f"{base}.{ext}"
        if path.is_file() and path.stat().st_size > 0:
            return path
    return None


def ensure_default_icon(cache_dir: Path) -> Path | None:
    """Ensure a default icon exists in cache (e.g. when no icon found). Return its path or None."""
    for default_name in ("default.ico", "default.png"):
        default_path = cache_dir / default_name
        if default_path.is_file() and default_path.stat().st_size > 0:
            return default_path
    if RESOURCES_DIR is not None:
        for src in (RESOURCES_DIR / "icon.ico", RESOURCES_DIR / "icon.png", RESOURCES_DIR / "icons" / "icon.ico"):
            if src.is_file() and src.stat().st_size > 0:
                default_path = cache_dir / f"default{src.suffix}"
                default_path.write_bytes(src.read_bytes())
                log.info(f"  💾 Default icon cached → {default_path}")
                return default_path
    # Use any existing icon in cache as fallback
    for p in cache_dir.iterdir():
        if p.is_file() and p.suffix.lower() in (".ico", ".png", ".gif", ".jpg", ".jpeg", ".svg"):
            if p.stat().st_size > 0:
                return p
    return None


ICON_PATHS = [
    "/favicon.ico",
    "/favicon.png",
    "/apple-touch-icon.png",
    "/apple-touch-icon-precomposed.png",
]

GOOGLE_FAVICON_API = "https://www.google.com/s2/favicons?sz=64&domain={host}"


def fetch_icon_direct(session: requests.Session, base_url: str) -> bytes | None:
    """Try to download a favicon directly from common paths."""
    for path in ICON_PATHS:
        url = base_url.rstrip("/") + path
        try:
            resp = session.get(url, timeout=session.timeout, allow_redirects=True)
            if resp.status_code == 200 and len(resp.content) > 0:
                log.info(f"  ✔ Found icon at {url} ({len(resp.content)} bytes)")
                return resp.content
        except requests.RequestException as e:
            log.debug(f"  ✗ {url} → {e}")
    return None


def fetch_icon_google(session: requests.Session, host: str) -> bytes | None:
    """Fall back to Google's favicon service."""
    url = GOOGLE_FAVICON_API.format(host=host)
    try:
        resp = session.get(url, timeout=session.timeout)
        if resp.status_code == 200 and len(resp.content) > 0:
            log.info(f"  ✔ Google favicon fetched for {host} ({len(resp.content)} bytes)")
            return resp.content
    except requests.RequestException as e:
        log.warning(f"  ✗ Google favicon failed for {host}: {e}")
    return None


def save_icon(host: str, data: bytes, output_dir: Path) -> Path:
    """Save icon bytes to disk; filename is derived from the host."""
    safe_name = _safe_host_name(host)
    # Detect image type by magic bytes
    ext = "ico"
    if data[:4] == b"\x89PNG":
        ext = "png"
    elif data[:3] == b"GIF":
        ext = "gif"
    elif data[:2] in (b"\xff\xd8", b"BM"):
        ext = "jpg"
    elif data[:4] == b"<svg" or b"<svg" in data[:64]:
        ext = "svg"

    filename = output_dir / f"{safe_name}.{ext}"
    filename.write_bytes(data)
    log.info(f"  💾 Saved → {filename}")
    return filename


# ─── Main API: cache-first icon for URL ────────────────────────────────────────

def get_icon_path_for_url(
    url: str,
    use_google_fallback: bool = True,
    cache_dir: Path | None = None,
) -> tuple[Path | None, str]:
    """
    Get icon path for a URL: use cache if present, else fetch and store, else default from cache.

    Returns:
        (path, source) where source is "cache" | "direct" | "google" | "default" | "none"
    """
    base_url = extract_host(url)
    if not base_url:
        return None, "none"
    parsed = urlparse(base_url)
    host = parsed.netloc
    out_dir = cache_dir if cache_dir is not None else (get_host_icons_cache_dir() if get_host_icons_cache_dir else Path("icons"))
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1) Use existing icon from cache if present
    cached = get_cached_icon_path(host, out_dir)
    if cached is not None:
        log.debug(f"  ✔ Icon from cache for {host}")
        return cached, "cache"

    # 2) Fetch (direct then Google)
    session = make_session()
    data = fetch_icon_direct(session, base_url)
    source = "direct"
    if data is None and use_google_fallback:
        data = fetch_icon_google(session, host)
        source = "google"

    if data:
        path = save_icon(host, data, out_dir)
        return path, source

    # 3) No icon found: use existing default/any icon from cache
    default_path = ensure_default_icon(out_dir)
    if default_path is not None:
        log.info(f"  ✔ No icon for {host} — using cached default")
        return default_path, "default"
    return None, "none"


# ─── Service Entry Point ───────────────────────────────────────────────────────

def process_urls(
    urls: list[str],
    output_dir: str = "icons",
    delay: float = 0.5,
    use_google_fallback: bool = True,
) -> dict[str, dict]:
    """
    Main service function.

    Args:
        urls:                 List of URLs to process.
        output_dir:           Directory to save icon files.
        delay:                Seconds to wait between requests.
        use_google_fallback:  Use Google favicon API when direct fetch fails.

    Returns:
        Dict mapping each original URL to a result dict:
          {host, icon_path, source, success, error}
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    session = make_session()
    results = {}

    log.info(f"Processing {len(urls)} URL(s) → icons saved to '{out}/'")
    log.info("=" * 60)

    for raw_url in urls:
        log.info(f"URL: {raw_url}")
        result = {"host": None, "icon_path": None, "source": None, "success": False, "error": None}

        base_url = extract_host(raw_url)
        if not base_url:
            result["error"] = "Invalid URL"
            results[raw_url] = result
            log.warning(f"  Skipped (invalid URL)\n")
            continue

        parsed = urlparse(base_url)
        host = parsed.netloc
        result["host"] = host
        log.info(f"  Host: {host}")

        # 1) Use existing icon from cache if present
        cached = get_cached_icon_path(host, out)
        if cached is not None:
            result.update(icon_path=str(cached), source="cache", success=True)
            log.info(f"  ✔ Using cached icon")
            results[raw_url] = result
            log.info("")
            continue

        # 2) Try direct fetch, then Google
        data = fetch_icon_direct(session, base_url)
        source = "direct"
        if data is None and use_google_fallback:
            log.info(f"  Direct fetch failed — trying Google favicon API …")
            data = fetch_icon_google(session, host)
            source = "google"

        if data:
            path = save_icon(host, data, out)
            result.update(icon_path=str(path), source=source, success=True)
        else:
            # 3) No icon found: use existing default/any icon from cache
            default_path = ensure_default_icon(out)
            if default_path is not None:
                result.update(icon_path=str(default_path), source="default", success=True)
                log.info(f"  ✔ No icon for {host} — using cached default")
            else:
                result["error"] = "Icon not found"
                log.warning(f"  ✗ No icon found for {host}")

        results[raw_url] = result
        log.info("")
        time.sleep(delay)

    # Summary
    ok = sum(1 for r in results.values() if r["success"])
    log.info("=" * 60)
    log.info(f"Done — {ok}/{len(urls)} icons fetched successfully.")
    return results


# ─── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Fetch and save site icons from a list of URLs."
    )
    parser.add_argument(
        "urls",
        nargs="*",
        help="One or more URLs (e.g. https://github.com example.com)",
    )
    parser.add_argument(
        "-f", "--file",
        help="Path to a text file with one URL per line",
    )
    parser.add_argument(
        "-o", "--output",
        default="icons",
        help="Output directory for saved icons (default: ./icons)",
    )
    parser.add_argument(
        "--no-google",
        action="store_true",
        help="Disable Google favicon API fallback",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="Delay in seconds between requests (default: 0.5)",
    )
    args = parser.parse_args()

    urls = list(args.urls)
    if args.file:
        path = Path(args.file)
        if not path.exists():
            parser.error(f"File not found: {args.file}")
        urls += [line.strip() for line in path.read_text().splitlines() if line.strip()]

    if not urls:
        # Demo mode
        log.info("No URLs provided — running with demo URLs.")
        urls = [
            "https://github.com",
            "https://python.org",
            "https://stackoverflow.com",
            "reddit.com",
            "not-a-valid-url",
        ]

    results = process_urls(
        urls,
        output_dir=args.output,
        delay=args.delay,
        use_google_fallback=not args.no_google,
    )

    # Print final table
    print("\n── Results ──────────────────────────────────────────────")
    print(f"{'URL':<40} {'Host':<25} {'Status'}")
    print("-" * 80)
    for url, r in results.items():
        status = f"✔ {r['source']}" if r["success"] else f"✗ {r['error']}"
        print(f"{url[:39]:<40} {(r['host'] or ''):<25} {status}")


if __name__ == "__main__":
    main()