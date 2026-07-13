"""앱 전역 설정: 경로, Gemma 모델 카탈로그, 상수.

이 모듈은 Qt(QStandardPaths)를 사용해 사용자 문서 폴더를 찾는다. 그 외
로직 계층(core/)은 이 파일에 의존하지 않는다.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from PySide6.QtCore import QStandardPaths

APP_NAME = "AutoGemmaStarter"
OLLAMA_HOST = "http://127.0.0.1:11434"

# 기본 채팅/요약 모델 (없으면 UI 에서 안내)
DEFAULT_MODEL = "gemma3:4b"


# ---------------------------------------------------------------------------
# 설정 (settings.json — 모델/데이터 저장 위치 등)
# ---------------------------------------------------------------------------
def settings_path() -> Path:
    p = Path.home() / ".auto_gemma"
    p.mkdir(parents=True, exist_ok=True)
    return p / "settings.json"


def load_settings() -> dict:
    try:
        return json.loads(settings_path().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_settings(data: dict) -> None:
    settings_path().write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def update_setting(key: str, value) -> None:
    s = load_settings()
    if value is None:
        s.pop(key, None)
    else:
        s[key] = value
    save_settings(s)


def get_models_dir() -> str | None:
    """Ollama 모델 저장 위치 (OLLAMA_MODELS). 미설정이면 None(기본 위치 사용)."""
    return load_settings().get("models_dir")


def apply_ollama_env() -> None:
    """저장된 모델 위치를 현재 프로세스 환경변수에 반영. 앱 시작 시 호출."""
    md = get_models_dir()
    if md:
        os.environ["OLLAMA_MODELS"] = md


# ---------------------------------------------------------------------------
# 경로 (한글 "문서" 폴더 로컬라이즈 대응 — QStandardPaths 사용)
# ---------------------------------------------------------------------------
def documents_dir() -> Path:
    loc = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)
    if not loc:
        loc = str(Path.home() / "Documents")
    return Path(loc)


def data_dir() -> Path:
    """대화·지식도서관 데이터 저장 루트. 설정에 data_dir 이 있으면 그 위치, 없으면 <문서>/GemmaChat"""
    custom = load_settings().get("data_dir")
    d = Path(custom) if custom else (documents_dir() / "GemmaChat")
    d.mkdir(parents=True, exist_ok=True)
    return d


def conversations_dir() -> Path:
    d = data_dir() / "conversations"
    d.mkdir(parents=True, exist_ok=True)
    return d


def resources_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "resources"


# ---------------------------------------------------------------------------
# Gemma 모델 카탈로그
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ModelSpec:
    tag: str            # ollama 태그 (예: gemma3:4b)
    label: str          # 표시 이름 (예: Gemma 3 (4B))
    params: str         # 파라미터 규모 (예: 4B)
    disk_gb: float      # 대략 디스크 사용량
    ram_gb: int         # 권장 최소 RAM
    vram_gb: float      # 전체 GPU 로드 권장 VRAM
    vision: bool        # 멀티모달(이미지) 지원 여부

    def spec_line(self) -> str:
        return (
            f"{self.params} · 디스크 약 {self.disk_gb:g}GB · "
            f"RAM {self.ram_gb}GB+ · VRAM {self.vram_gb:g}GB+"
        )


GEMMA_CATALOG: list[ModelSpec] = [
    ModelSpec("gemma3:1b", "Gemma 3 (1B)", "1B", 0.8, 2, 2.0, vision=False),
    ModelSpec("gemma3:4b", "Gemma 3 (4B)", "4B", 3.3, 8, 5.8, vision=True),
    ModelSpec("gemma3:12b", "Gemma 3 (12B)", "12B", 8.1, 12, 11.0, vision=True),
    ModelSpec("gemma3:27b", "Gemma 3 (27B)", "27B", 17.0, 24, 22.0, vision=True),
]

CATALOG_BY_TAG: dict[str, ModelSpec] = {m.tag: m for m in GEMMA_CATALOG}


def spec_for(tag: str) -> ModelSpec | None:
    """정확 일치 우선, 없으면 베이스 태그(gemma3:4b-it 등)로 근사 매칭."""
    if tag in CATALOG_BY_TAG:
        return CATALOG_BY_TAG[tag]
    base = tag.split("-")[0]
    return CATALOG_BY_TAG.get(base)


# ---------------------------------------------------------------------------
# 고급 채팅 옵션 기본값
# ---------------------------------------------------------------------------
@dataclass
class ChatOptions:
    temperature: float = 0.7
    num_ctx: int = 8192
    top_p: float = 0.9
    system_prompt: str = ""

    def to_ollama_options(self) -> dict:
        return {
            "temperature": self.temperature,
            "num_ctx": self.num_ctx,
            "top_p": self.top_p,
        }
