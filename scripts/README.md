# VOK scripts

Run from **project root** (parent of `scripts/`).

| Script | Description |
|--------|-------------|
| **run.sh** (macOS/Linux) | Sync deps with `uv`, check FFmpeg, run `uv run run.py`. |
| **run.bat** (Windows) | Same for Windows. |
| **lint.sh** | Run ruff: remove unused imports, sort imports, show stats. |
| **format.sh** | Format code with `ruff format .`. |
| **build_mac.sh** | Build macOS app: `dist/VOK.app`. |
| **build_win.bat** | Build Windows exe: `dist\VOK\VOK.exe`. |

### Quick start

```bash
# macOS/Linux
./scripts/run.sh

# Windows
scripts\run.bat
```

### Lint & format

```bash
uv sync --extra dev   # installs ruff
./scripts/lint.sh
./scripts/format.sh
```
