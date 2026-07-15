@echo off
setlocal
title NIRMIQ Safe Diagnostics
cd /d "%~dp0"

echo Creating a privacy-safe local diagnostics bundle...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\export_diagnostics.ps1" -OpenFolder
if errorlevel 1 (
  echo.
  echo Diagnostics export failed. Run NIRMIQ Doctor and try again.
  pause
  exit /b 1
)

echo.
echo The diagnostics folder has been opened. No documents, prompts, answers, database, or raw logs were included.
pause
