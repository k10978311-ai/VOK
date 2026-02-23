@echo off
chcp 65001 >nul
setlocal

:: VOK — Sync dependencies and run the app (Windows).
:: Run from project root: scripts\run.bat  OR  from scripts/: run.bat

set "SCRIPT_DIR=%~dp0"
set "ROOT_DIR=%SCRIPT_DIR%.."
cd /d "%ROOT_DIR%"

if not exist "run.py" (
    echo [ERROR] run.py not found. Run from project root.
    pause
    exit /b 1
)
if not exist "pyproject.toml" (
    echo [ERROR] pyproject.toml not found. Run from project root.
    pause
    exit /b 1
)
if not exist "app" (
    echo [ERROR] app folder not found. Run from project root.
    pause
    exit /b 1
)

echo.
echo ==========================================
echo   VOK — Video Downloader ^& Scraper
echo ==========================================
echo.

:: Check uv
where uv >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing uv...
    powershell -ExecutionPolicy ByPass -NoProfile -Command "irm https://astral.sh/uv/install.ps1 | iex"
    set "PATH=%USERPROFILE%\.local\bin;%PATH%"
    set "PATH=%LOCALAPPDATA%\uv\bin;%PATH%"
)
where uv >nul 2>&1
if errorlevel 1 (
    echo [ERROR] uv not found. Install from https://docs.astral.sh/uv/
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('uv --version 2^>nul') do echo [OK] %%v

:: Sync dependencies
echo [INFO] Syncing dependencies...
uv sync
if errorlevel 1 (
    echo [ERROR] uv sync failed.
    pause
    exit /b 1
)
echo [OK] Dependencies ready.
echo.

:: FFmpeg check
where ffmpeg >nul 2>&1
if errorlevel 1 (
    echo [WARN] FFmpeg not found ^(recommended for MP3 and merging^)
    echo   Install: winget install ffmpeg
    echo.
)

:: Run
echo [INFO] Starting VOK...
echo.
uv run run.py
if errorlevel 1 pause
exit /b 0
