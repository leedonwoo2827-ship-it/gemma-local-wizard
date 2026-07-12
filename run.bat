@echo off
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (set "PY=py") else (set "PY=python")

echo [Auto Gemma Starter] Installing required libraries...
%PY% -m pip install -q -r requirements.txt

echo [Auto Gemma Starter] Launching the app...
%PY% -m auto_gemma.main

if errorlevel 1 (
    echo.
    echo An error occurred. See the messages above.
    pause
)
