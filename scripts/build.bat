@echo off
REM Build script for LD YouTube Automator Pro

echo ========================================
echo  LD YouTube Automator Pro - Build
echo ========================================
echo.

REM Clean previous builds
echo [1/3] Cleaning previous builds...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
echo Done.
echo.

REM Run PyInstaller
echo [2/3] Building executable with PyInstaller...
python -m uv run pyinstaller LD-YouTube-Automator-Pro.spec --clean --noconfirm
echo Done.
echo.

REM Check if build was successful
if exist "dist\LD-YouTube-Automator-Pro\LD-YouTube-Automator-Pro.exe" (
    echo [3/3] Build successful!
    echo.
    echo ========================================
    echo  Build Complete!
    echo ========================================
    echo.
    echo Executable location:
    echo   dist\LD-YouTube-Automator-Pro\LD-YouTube-Automator-Pro.exe
    echo.
    echo You can now distribute the entire "dist\LD-YouTube-Automator-Pro" folder.
    echo.
) else (
    echo [3/3] Build failed!
    echo Please check the error messages above.
    echo.
    exit /b 1
)

pause
