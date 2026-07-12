#!/bin/bash
# macOS double-click launcher. First time: chmod +x run.command
cd "$(dirname "$0")"

PY=python3
command -v $PY >/dev/null 2>&1 || PY=python

echo "[Auto Gemma Starter] Installing required libraries..."
$PY -m pip install -q -r requirements.txt

echo "[Auto Gemma Starter] Launching the app..."
$PY -m auto_gemma.main
