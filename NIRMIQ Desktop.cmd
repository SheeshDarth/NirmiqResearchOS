@echo off
setlocal
cd /d "%~dp0"
echo Starting NIRMIQ Academic Intelligence desktop app...
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start_desktop.ps1"
if errorlevel 1 (
  echo.
  echo NIRMIQ desktop did not start.
  echo If this is your first run, install desktop dependencies once:
  echo powershell -NoProfile -ExecutionPolicy Bypass -File scripts\start_desktop.ps1 -Install
  pause
  exit /b 1
)
