@echo off
setlocal
cd /d "%~dp0"
echo Starting NIRMIQ ResearchOS local preview...
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\run_local.ps1" -OpenBrowser
if errorlevel 1 (
  echo.
  echo NIRMIQ failed to start. Check temp\runtime logs for details.
  pause
  exit /b 1
)
echo.
echo NIRMIQ is running at http://127.0.0.1:3002
echo You can close this window after the browser opens.
timeout /t 5 >nul
