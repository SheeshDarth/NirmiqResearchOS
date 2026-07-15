@echo off
setlocal
cd /d "%~dp0"
echo Checking NIRMIQ local runtime...
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\release_doctor.ps1"
if errorlevel 1 (
  echo.
  echo NIRMIQ needs attention. Follow the required actions above.
  pause
  exit /b 1
)
echo.
echo NIRMIQ is ready for local startup.
pause
