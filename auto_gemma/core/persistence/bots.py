"""봇(페르소나) 관리: 이름 + 시스템 프롬프트. JSON 저장 (Qt 비의존)."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from auto_gemma.app.config import bots_path

DEFAULT_BOTS = [
    {"name": "기본", "system": ""},
    {"name": "요약 도우미", "system": "당신은 핵심만 간결하게 요약하는 도우미입니다. 불필요한 수식어 없이 요점을 정리하세요."},
    {"name": "문제집 출제자", "system": "당신은 교육 콘텐츠 출제 전문가입니다. 주어진 자료로 학습용 문제와 상세한 해설을 만듭니다."},
    {"name": "번역가", "system": "당신은 자연스러운 한국어/영어 번역가입니다. 문맥을 살려 번역하세요."},
]


@dataclass
class Bot:
    name: str
    system: str = ""


class BotStore:
    def __init__(self, path: Path | None = None):
        self.path = path or bots_path()
        if not self.path.exists():
            self._write(DEFAULT_BOTS)

    def _write(self, data: list[dict]) -> None:
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def list_all(self) -> list[Bot]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return [Bot(**b) for b in data]
        except (json.JSONDecodeError, OSError, TypeError):
            return [Bot(**b) for b in DEFAULT_BOTS]

    def get(self, name: str) -> Bot:
        for b in self.list_all():
            if b.name == name:
                return b
        return Bot("기본", "")

    def save(self, bot: Bot) -> None:
        bots = self.list_all()
        for i, b in enumerate(bots):
            if b.name == bot.name:
                bots[i] = bot
                break
        else:
            bots.append(bot)
        self._write([asdict(b) for b in bots])

    def delete(self, name: str) -> None:
        if name == "기본":
            return
        bots = [b for b in self.list_all() if b.name != name]
        self._write([asdict(b) for b in bots])
