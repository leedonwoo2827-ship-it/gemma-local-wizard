#!/bin/bash
# macOS 더블클릭 실행용. 최초 실행 시: chmod +x run.command
cd "$(dirname "$0")"

PY=python3
command -v $PY >/dev/null 2>&1 || PY=python

echo "[Auto Gemma Starter] 필요한 라이브러리 확인 중..."
$PY -m pip install -q -r requirements.txt

echo "[Auto Gemma Starter] 앱을 실행합니다..."
$PY -m auto_gemma.main
