@echo off
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (set "PY=py") else (set "PY=python")

echo [Gemma] Installing required libraries...
%PY% -m pip install -q -r requirements.txt

echo [Gemma] Launching the app...
%PY% -m auto_gemma.main

if errorlevel 1 (
    echo.
    echo An error occurred. See the messages above.
    pause
)
