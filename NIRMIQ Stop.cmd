@echo off
setlocal
cd /d "%~dp0"
echo Stopping NIRMIQ Academic Intelligence local preview...
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\stop_local.ps1"
echo.
pause
