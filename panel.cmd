@echo off
REM Friendly launcher for the LinkedIn control panel.
REM Double-click this file, or run:  panel review  /  panel approve 1  etc.
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" panel.py %*
) else (
    python panel.py %*
)
if "%~1"=="" (
    echo.
    pause
)
