# VOK — Video Downloader & Social Analytics

A desktop application for downloading videos and scraping social media content, built with PyQt5 and a Fluent Design UI.

---

## Features

### Download Tab
| Feature | Details |
|---|---|
| **HD Video Download** | 4K / 2160p, HD 1080p, HD 720p, Best (video+audio) |
| **Photo / Image Download** | Downloads image posts and saves thumbnails |
| **Audio Download** | MP3 extraction, best audio |
| **Bulk Download** | Toggle bulk mode — paste one URL per line |
| **Selective Download** | Preview a playlist, tick the items you want, download only those |
| **Playlist Support** | Toggle single-video mode on/off |
| **Parallel Downloads** | Up to 4 concurrent jobs (configurable) |
| **Cookies Support** | Authenticated downloads via Netscape cookies file |

### Analytics Tab
| Feature | Details |
|---|---|
| **Post Statistics** | Views, likes, dislikes, comments, upload date, duration, tags |
| **Follower / Subscriber Count** | Shown when available from the platform |
| **Comments Scraping** | Fetch up to 1 000 comments per post — export to CSV |
| **Content Search** | Search YouTube, TikTok, SoundCloud, or Bilibili by keyword |
| **Hashtag Scraping** | Toggle hashtag mode to search by `#tag` |
| **Sort by Engagement** | Sort results by views (high→low) or likes (high→low) |
| **Sort by Date** | Sort results newest or oldest first |
| **Content Translation** | Translate any text to 16 languages (free, no API key) |

### Supported Platforms
YouTube · TikTok · Douyin · Kuaishou · Instagram · Facebook · Pinterest · Twitter / X · ok.ru · VK · Twitch · Vimeo · Dailymotion · SoundCloud · Bilibili · Reddit · and **1 000+ more** via yt-dlp

---

## Requirements

- **Python** 3.12+
- **FFmpeg** — required for MP3 extraction and some merging operations
- **uv** — recommended package manager (or use `pip`)

### Install FFmpeg (Windows)
```bat
winget install ffmpeg
```
Or download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to your `PATH`.

---

## Installation

### Option 1 — uv (recommended)
```bat
git clone <repo-url>
cd VOK
uv sync
uv run python run.py
```

### Option 2 — pip
```bat
git clone <repo-url>
cd VOK
python -m venv .venv
.venv\Scripts\activate
pip install -e .
python run.py
```

---

## Building for distribution

Standalone executables can be built with PyInstaller. **Build on macOS for a Mac app; build on Windows for a Windows .exe.**

1. Install dev dependencies (includes PyInstaller):
   ```bash
   uv sync --extra dev
   ```

2. **macOS** — from project root:
   ```bash
   ./scripts/build_mac.sh
   ```
   Output: `dist/VOK.app`

3. **Windows** — from project root:
   ```bat
   scripts\build_win.bat
   ```
   Output: `dist\VOK\VOK.exe` (distribute the entire `dist\VOK` folder).

Users still need **FFmpeg** installed for audio/video merging.

---

## Project Structure

```
VOK/
├── app/
│   ├── common/
│   │   ├── paths.py          # Path constants
│   │   └── state.py          # In-memory log buffer & recent downloads
│   ├── config/
│   │   └── store.py          # JSON settings persistence
│   ├── core/
│   │   ├── download.py       # yt-dlp download worker (QThread)
│   │   ├── manager.py        # Parallel download manager
│   │   └── scraper.py        # Analytics workers (metadata, comments, search, translate)
│   └── ui/
│       ├── main_window.py    # FluentWindow with navigation
│       ├── components/       # Reusable widgets (CardHeader, StatusTable)
│       └── views/
│           ├── dashboard.py  # Recent downloads overview
│           ├── downloader.py # Download tab (single / bulk / selective)
│           ├── scraper.py    # Analytics tab (stats / comments / search / translate)
│           ├── logs.py       # Application log viewer
│           └── settings.py  # App settings
├── resources/
│   └── icons/
├── scripts/
├── run.py                    # Entry point
└── pyproject.toml
```

---

## Configuration

Settings are stored in `vok_settings.json` in the project root. You can change them from the **Settings** tab inside the app.

| Setting | Default | Description |
|---|---|---|
| `download_path` | `downloads/` | Output folder for all downloads |
| `single_video_default` | `true` | Skip playlist by default |
| `theme` | `Dark` | `Auto` / `Light` / `Dark` |
| `theme_color` | `#0078D4` | Accent colour |
| `concurrent_downloads` | `2` | Parallel download jobs (1–4) |
| `concurrent_fragments` | `4` | Fragments per download (1–16) |
| `cookies_file` | *(empty)* | Path to Netscape cookies file for auth |

### Using a Cookies File (authenticated platforms)

Export cookies from your browser using the [Get cookies.txt LOCALLY](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc) extension (Chrome/Edge) or equivalent, then point **Settings → Cookies file** to the saved `.txt` file.

---

## Download Formats

| Format | Description |
|---|---|
| Best (video+audio) | Highest quality, any codec |
| HD 1080p | Up to 1080p resolution |
| HD 720p | Up to 720p resolution |
| 4K / 2160p | Up to 4K resolution |
| Best video | Video stream only (no audio) |
| Best audio | Audio stream only |
| Video (mp4) | MP4 container preferred |
| Audio (mp3) | Extracts audio as MP3 192kbps (FFmpeg required) |
| Photo / Image | Image posts; also saves thumbnails |

---

## Analytics — Feature Notes

### Post Statistics
Paste any video URL and click **Fetch Stats** to see views, likes, comments count, follower/subscriber count, upload date, duration, tags, and description. The description is automatically copied to the Translation input.

### Comments Scraper
- Set **Max** (10–1 000) before fetching.
- Works best with YouTube; also supports TikTok with cookies.
- Click **Export CSV** to save all comments to a spreadsheet-compatible file.

### Content Search
- Select a platform, type a keyword, and click **Search**.
- Toggle **Hashtag** to prefix the query with `#`.
- Use **Sort by** to re-order results by views, likes, or date without re-fetching.
- Double-click any row to copy its URL to the clipboard.

### Content Translation
- Supports auto-detection of the source language.
- Powered by [MyMemory](https://mymemory.translated.net/) (free tier: 1 000 requests/day, no API key required).
- 16 target languages: English, Spanish, French, German, Japanese, Korean, Chinese, Arabic, Portuguese, Russian, Italian, Hindi, Turkish, Vietnamese, Thai, Indonesian.

---

## Dependencies

| Package | Purpose |
|---|---|
| `PyQt5` | UI framework |
| `PyQt-Fluent-Widgets` | Fluent Design components |
| `yt-dlp` | Video/audio downloading & metadata extraction |
| `requests` | HTTP requests |
| `beautifulsoup4` + `lxml` | HTML parsing |
| `playwright` | Browser automation (advanced scraping) |
| `aiohttp` | Async HTTP |
| `Pillow` | Image processing |
| `apscheduler` | Task scheduling |

---

## License

MIT
