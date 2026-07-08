@echo off
setlocal
cd /d "%~dp0"
echo Running NIRMIQ ResearchOS ship check...
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\ship_check.ps1"
if errorlevel 1 (
  echo.
  echo NIRMIQ ship check failed. Review the output above and temp\runtime logs.
  pause
  exit /b 1
)
echo.
echo NIRMIQ ship check passed.
pause
