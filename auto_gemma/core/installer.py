"""Windows 용 Ollama 무음 설치 (Qt 비의존).

전략: winget 우선 → 실패 시 OllamaSetup.exe 다운로드/번들 후 무음 실행.
설치 후 /api/version 폴링으로 성공을 확인한다.
"""
from __future__ import annotations

import platform
import shutil
import subprocess
import time
from pathlib import Path
from typing import Callable

import httpx

from auto_gemma.app.config import OLLAMA_HOST, resources_dir

_CREATE_NO_WINDOW = 0x08000000 if platform.system() == "Windows" else 0
_INSTALLER_URL = "https://ollama.com/download/OllamaSetup.exe"

Log = Callable[[str], None]


def _log(cb: Log | None, msg: str) -> None:
    if cb:
        cb(msg)


def _server_up(timeout: float = 1.0) -> bool:
    try:
        r = httpx.get(f"{OLLAMA_HOST}/api/version", timeout=timeout)
        return r.status_code == 200
    except httpx.HTTPError:
        return False


def wait_for_server(max_wait: float = 30.0, cancel=None, log: Log | None = None) -> bool:
    """서버가 뜰 때까지 폴링."""
    deadline = time.monotonic() + max_wait
    while time.monotonic() < deadline:
        if cancel is not None and cancel.is_set():
            return False
        if _server_up():
            _log(log, "Ollama 서버 응답 확인됨.")
            return True
        time.sleep(1.0)
    return False


def _winget_available() -> bool:
    return shutil.which("winget") is not None


def _install_via_winget(log: Log | None, cancel=None) -> bool:
    if not _winget_available():
        _log(log, "winget 을 찾을 수 없습니다.")
        return False
    _log(log, "winget 으로 Ollama 설치 중... (몇 분 걸릴 수 있어요)")
    try:
        proc = subprocess.run(
            [
                "winget", "install", "--id", "Ollama.Ollama", "-e",
                "--silent", "--accept-package-agreements",
                "--accept-source-agreements",
            ],
            capture_output=True, text=True, timeout=900,
            creationflags=_CREATE_NO_WINDOW,
        )
        if proc.returncode == 0:
            _log(log, "winget 설치 명령 완료.")
            return True
        _log(log, f"winget 설치 실패 (코드 {proc.returncode}).")
    except (OSError, subprocess.SubprocessError) as e:
        _log(log, f"winget 오류: {e}")
    return False


def _bundled_installer() -> Path | None:
    p = resources_dir() / "OllamaSetup.exe"
    return p if p.exists() else None


def _download_installer(dest: Path, log: Log | None, cancel=None) -> bool:
    _log(log, "Ollama 설치 파일 다운로드 중...")
    try:
        with httpx.stream("GET", _INSTALLER_URL, timeout=None, follow_redirects=True) as r:
            r.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in r.iter_bytes(chunk_size=1 << 16):
                    if cancel is not None and cancel.is_set():
                        return False
                    f.write(chunk)
        return dest.exists() and dest.stat().st_size > 0
    except (httpx.HTTPError, OSError) as e:
        _log(log, f"다운로드 실패: {e}")
        return False


def _install_via_setup(log: Log | None, cancel=None) -> bool:
    exe = _bundled_installer()
    if exe is None:
        exe = resources_dir() / "OllamaSetup.exe"
        exe.parent.mkdir(parents=True, exist_ok=True)
        if not _download_installer(exe, log, cancel):
            return False
    _log(log, "설치 프로그램 실행 중 (무음)...")
    try:
        proc = subprocess.run(
            [str(exe), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"],
            capture_output=True, text=True, timeout=900,
            creationflags=_CREATE_NO_WINDOW,
        )
        return proc.returncode == 0
    except (OSError, subprocess.SubprocessError) as e:
        _log(log, f"설치 실행 오류: {e}")
        return False


def install_ollama(log: Log | None = None, cancel=None) -> bool:
    """Ollama 설치. 성공 시 True. (Qt 비의존 — 워커에서 호출)"""
    if platform.system() != "Windows":
        _log(log, "자동 설치는 Windows 만 지원합니다. https://ollama.com 에서 수동 설치하세요.")
        return False

    if _server_up():
        _log(log, "이미 Ollama 가 실행 중입니다.")
        return True

    ok = _install_via_winget(log, cancel)
    if not ok:
        _log(log, "winget 실패 → 설치 파일 방식으로 재시도합니다.")
        ok = _install_via_setup(log, cancel)

    if not ok:
        _log(log, "Ollama 설치에 실패했습니다.")
        return False

    _log(log, "설치 완료. 서버 기동 대기 중...")
    # 설치 직후 서버가 자동 기동되지 않으면 직접 띄운다
    if not wait_for_server(15.0, cancel, log):
        from auto_gemma.core.ollama_client import OllamaClient
        OllamaClient().start_server()
        return wait_for_server(20.0, cancel, log)
    return True
