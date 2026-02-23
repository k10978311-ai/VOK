@echo off
REM Build VOK for Windows (.exe).
REM Run from project root: scripts\build_win.bat
REM Requires: uv and pyinstaller (uv pip install -e ".[dev]")

cd /d "%~dp0\.."
echo ========================================
echo   VOK — Build for Windows
echo ========================================

REM Install dev deps (includes PyInstaller)
echo Syncing dev dependencies...
uv sync --extra dev

echo [1/2] Building with PyInstaller...
uv run pyinstaller vok.spec --clean --noconfirm

if exist "dist\VOK\VOK.exe" (
  echo [2/2] Build successful!
  echo.
  echo Output: dist\VOK\VOK.exe
  echo Distribute the entire folder: dist\VOK
) else (
  echo [2/2] Build failed.
  exit /b 1
)

pause
