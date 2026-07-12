@echo off
chcp 65001 >nul
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (set "PY=py") else (set "PY=python")

echo [Auto Gemma Starter] 필요한 라이브러리 확인 중...
%PY% -m pip install -q -r requirements.txt

echo [Auto Gemma Starter] 앱을 실행합니다...
%PY% -m auto_gemma.main

if errorlevel 1 (
    echo.
    echo 오류가 발생했습니다. 위 메시지를 확인하세요.
    pause
)
