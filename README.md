# VOK — Video Downloader

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
git clone https://github.com/k10978311-ai/VOK.git
cd VOK
uv sync
uv run python run.py
```

### Option 2 — pip
```bat
git clone https://github.com/k10978311-ai/VOK.git
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

## Dependency updates (auto)

- **GitHub**: Dependabot is enabled (`.github/dependabot.yml`) and will open weekly PRs for dependency updates. Review and merge as needed.
- **Local**: From the project root, refresh the lockfile and upgrade all deps:
  ```bash
  uv lock --upgrade && uv sync
  ```
  Or run:
  - Windows: `scripts\update-deps.bat`
  - Unix: `./scripts/update-deps.sh`

---
<!-- 
## License

MIT -->
