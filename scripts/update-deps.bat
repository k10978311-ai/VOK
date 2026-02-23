@echo off
chcp 65001 >nul
:: Refresh lockfile and upgrade dependencies (patch update auto)
cd /d "%~dp0\.."
echo Updating dependencies (uv lock --upgrade)...
uv lock --upgrade
if %ERRORLEVEL% neq 0 exit /b %ERRORLEVEL%
echo Syncing environment...
uv sync
echo Done.
