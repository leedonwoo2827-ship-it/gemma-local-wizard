"""Ollama HTTP 클라이언트 (raw httpx, Qt 비의존).

스트리밍 취소는 서버 API 가 아닌 '연결 종료'로만 가능하다. 따라서 스트리밍
메서드는 제너레이터이며, 호출자가 중간에 break 하면 with 컨텍스트가 닫히면서
소켓이 끊기고 Ollama 가 생성을 중단한다.
"""
from __future__ import annotations

import base64
import json
import os
import platform
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import httpx

from auto_gemma.app.config import OLLAMA_HOST

_CREATE_NO_WINDOW = 0x08000000 if platform.system() == "Windows" else 0
_DETACHED = 0x00000008 if platform.system() == "Windows" else 0


@dataclass
class InstalledModel:
    name: str
    size_bytes: int = 0
    parameter_size: str = ""
    quantization: str = ""

    @property
    def size_gb(self) -> float:
        return round(self.size_bytes / (1024 ** 3), 2)


class OllamaError(RuntimeError):
    pass


class OllamaClient:
    def __init__(self, host: str = OLLAMA_HOST):
        self.host = host.rstrip("/")
        self._client = httpx.Client(base_url=self.host, timeout=10.0)

    def close(self) -> None:
        self._client.close()

    # ------------------------------------------------------------------ 상태
    def version(self, timeout: float = 1.0) -> str | None:
        """서버가 응답하면 버전 문자열, 아니면 None."""
        try:
            r = httpx.get(f"{self.host}/api/version", timeout=timeout)
            if r.status_code == 200:
                return r.json().get("version", "")
        except httpx.HTTPError:
            pass
        return None

    def is_running(self) -> bool:
        return self.version() is not None

    @staticmethod
    def find_executable() -> str | None:
        exe = shutil.which("ollama")
        if exe:
            return exe
        if platform.system() == "Windows":
            cand = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe"
            if cand.exists():
                return str(cand)
        return None

    def status(self) -> str:
        """running | installed | absent"""
        if self.is_running():
            return "running"
        return "installed" if self.find_executable() else "absent"

    def start_server(self) -> bool:
        """설치돼 있으나 미실행일 때 서버를 백그라운드로 띄운다."""
        exe = self.find_executable()
        if not exe:
            return False
        try:
            subprocess.Popen(
                [exe, "serve"],
                creationflags=_CREATE_NO_WINDOW | _DETACHED,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        except OSError:
            return False

    # ------------------------------------------------------------------ 모델
    def list_models(self) -> list[InstalledModel]:
        try:
            r = self._client.get("/api/tags")
            r.raise_for_status()
        except httpx.HTTPError as e:
            raise OllamaError(f"모델 목록 조회 실패: {e}") from e
        result = []
        for m in r.json().get("models", []):
            details = m.get("details", {}) or {}
            result.append(InstalledModel(
                name=m.get("name", ""),
                size_bytes=m.get("size", 0),
                parameter_size=details.get("parameter_size", ""),
                quantization=details.get("quantization_level", ""),
            ))
        return result

    def has_model(self, tag: str) -> bool:
        try:
            names = {m.name for m in self.list_models()}
        except OllamaError:
            return False
        return tag in names or any(n.split(":")[0] == tag.split(":")[0] and ":" not in tag for n in names)

    def pull(self, model: str) -> Iterator[dict]:
        """모델 다운로드. NDJSON 진행 상황을 yield. 호출자가 break 하면 취소."""
        with httpx.stream(
            "POST", f"{self.host}/api/pull",
            json={"model": model, "stream": True},
            timeout=None,
        ) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue

    def delete(self, model: str) -> None:
        try:
            # httpx 의 .delete() 는 body 를 막으므로 request 사용
            r = self._client.request("DELETE", "/api/delete", json={"model": model})
            r.raise_for_status()
        except httpx.HTTPError as e:
            raise OllamaError(f"모델 삭제 실패: {e}") from e

    # ------------------------------------------------------------------ 채팅
    def chat(self, model: str, messages: list[dict], options: dict | None = None) -> Iterator[str]:
        """스트리밍 채팅. content 델타를 yield. 호출자가 break 하면 생성 중단.

        messages: [{"role","content","images"?:[base64...]}]
        """
        payload = {"model": model, "messages": messages, "stream": True}
        if options:
            payload["options"] = options
        with httpx.stream(
            "POST", f"{self.host}/api/chat", json=payload, timeout=None,
        ) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if obj.get("error"):
                    raise OllamaError(obj["error"])
                delta = (obj.get("message") or {}).get("content", "")
                if delta:
                    yield delta
                if obj.get("done"):
                    break

    # --------------------------------------------------------------- 임베딩
    def embed(self, model: str, texts: list[str]) -> list[list[float]]:
        """배치 임베딩. 신형 /api/embed 우선, 구형 /api/embeddings 폴백."""
        try:
            r = self._client.post("/api/embed", json={"model": model, "input": texts}, timeout=120.0)
            if r.status_code == 200:
                return r.json().get("embeddings", [])
        except httpx.HTTPError:
            pass
        # 폴백: 한 건씩
        out = []
        for t in texts:
            r = self._client.post("/api/embeddings", json={"model": model, "prompt": t}, timeout=120.0)
            r.raise_for_status()
            out.append(r.json().get("embedding", []))
        return out


def encode_image(path: str | Path) -> str:
    """이미지 파일 → base64 문자열 (data URL 프리픽스 없이)."""
    return base64.b64encode(Path(path).read_bytes()).decode("ascii")
