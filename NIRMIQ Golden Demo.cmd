@echo off
setlocal
cd /d "%~dp0"
echo Starting NIRMIQ Academic Intelligence golden demo preview...
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\run_local.ps1" -GoldenDemo -OpenBrowser
if errorlevel 1 (
  echo.
  echo Golden demo startup failed. The base app may still be available; check temp\runtime logs for details.
  pause
  exit /b 1
)
echo.
echo NIRMIQ golden demo is running at http://127.0.0.1:3002
timeout /t 5 >nul
