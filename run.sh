#!/bin/bash
# Linux launcher. First time: chmod +x run.sh
cd "$(dirname "$0")"

PY=python3
command -v $PY >/dev/null 2>&1 || PY=python

echo "[Gemma] Installing required libraries..."
$PY -m pip install -q -r requirements.txt

echo "[Gemma] Launching the app..."
$PY -m auto_gemma.main
