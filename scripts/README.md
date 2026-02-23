# VOK scripts

Run from **project root** (parent of `scripts/`).

| Script | Description |
|--------|-------------|
| **run.sh** (macOS/Linux) | Sync deps with `uv`, check FFmpeg, run `uv run run.py`. |
| **run.bat** (Windows) | Same for Windows. |
| **lint.sh** | Run ruff: remove unused imports, sort imports, show stats. |
| **format.sh** | Format code with `ruff format .`. |
| **build_mac.sh** | Build macOS app: `dist/VOK.app`. |
| **build_mac_installer.sh** | Build app + create install package: `dist/VOK-Install-<version>.pkg`. |
| **build_win.bat** | Build Windows exe: `dist\VOK\VOK.exe`. |

### Quick start

```bash
# macOS/Linux
./scripts/run.sh

# Windows
scripts\run.bat
```

### macOS installer (.pkg)

Build the app and a double-click installer that installs VOK into `/Applications`. The installer shows a **welcome** screen and **license** before installation.

```bash
./scripts/build_mac_installer.sh
# Output: dist/VOK-Install-0.1.0.pkg
# Open with: open dist/VOK-Install-0.1.0.pkg
```

- **Welcome and license** text live in `resources/installer/welcome.rtf` and `resources/installer/license.rtf`. Edit those to change the installer text.
- If `dist/VOK.app` already exists, only the .pkg is created. Delete `dist/VOK.app` to force a full rebuild.

**Signed and notarized distribution (optional)**  
To build a .pkg that other Macs will trust (no Gatekeeper warning), set these before running the script:

| Variable | Purpose |
|----------|---------|
| `DEVELOPER_ID_APP` | Sign the app (e.g. `"Developer ID Application: Your Name (TEAM_ID)"`) |
| `DEVELOPER_ID_INSTALLER` | Sign the .pkg (e.g. `"Developer ID Installer: Your Name (TEAM_ID)"`) |
| `NOTARY_KEYCHAIN_PROFILE` | Notary keychain profile name, **or** use the three below |
| `NOTARY_APPLE_ID` | Apple ID email for notarytool |
| `NOTARY_TEAM_ID` | Team ID |
| `NOTARY_APPLE_APP_PASSWORD` | App-specific password (from appleid.apple.com) |

Example (keychain profile for notarization):

```bash
export DEVELOPER_ID_APP="Developer ID Application: My Name (ABCD1234)"
export DEVELOPER_ID_INSTALLER="Developer ID Installer: My Name (ABCD1234)"
export NOTARY_KEYCHAIN_PROFILE="AC_PASSWORD"
./scripts/build_mac_installer.sh
```

### Lint & format

```bash
uv sync --extra dev   # installs ruff
./scripts/lint.sh
./scripts/format.sh
```
