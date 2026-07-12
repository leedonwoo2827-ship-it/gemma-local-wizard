"""대화 저장/불러오기/검색/이름변경/삭제 (JSON 파일, Qt 비의존).

각 대화는 <문서>/GemmaChat/conversations/<id>.json 에 저장된다.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path

from auto_gemma.app.config import conversations_dir


@dataclass
class Message:
    role: str                       # user | assistant | system
    content: str
    images: list[str] = field(default_factory=list)  # 첨부 이미지 경로(표시용)


@dataclass
class Conversation:
    id: str
    title: str
    model: str = ""
    bot: str = "기본"
    messages: list[Message] = field(default_factory=list)
    created: str = ""
    updated: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Conversation":
        msgs = [Message(**m) for m in d.get("messages", [])]
        return cls(
            id=d["id"], title=d.get("title", "새 대화"),
            model=d.get("model", ""), bot=d.get("bot", "기본"),
            messages=msgs, created=d.get("created", ""), updated=d.get("updated", ""),
        )


class ConversationStore:
    def __init__(self, directory: Path | None = None):
        self.dir = directory or conversations_dir()
        self.dir.mkdir(parents=True, exist_ok=True)

    def _path(self, conv_id: str) -> Path:
        return self.dir / f"{conv_id}.json"

    def new(self, title: str = "새 대화", model: str = "", ts: str = "") -> Conversation:
        conv = Conversation(id=uuid.uuid4().hex[:12], title=title, model=model,
                            created=ts, updated=ts)
        self.save(conv)
        return conv

    def save(self, conv: Conversation, ts: str = "") -> None:
        if ts:
            conv.updated = ts
        self._path(conv.id).write_text(
            json.dumps(conv.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def load(self, conv_id: str) -> Conversation | None:
        p = self._path(conv_id)
        if not p.exists():
            return None
        try:
            return Conversation.from_dict(json.loads(p.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, KeyError):
            return None

    def delete(self, conv_id: str) -> None:
        self._path(conv_id).unlink(missing_ok=True)

    def rename(self, conv_id: str, title: str) -> None:
        conv = self.load(conv_id)
        if conv:
            conv.title = title
            self.save(conv)

    def list_all(self) -> list[Conversation]:
        convs = []
        for p in self.dir.glob("*.json"):
            try:
                convs.append(Conversation.from_dict(json.loads(p.read_text(encoding="utf-8"))))
            except (json.JSONDecodeError, KeyError):
                continue
        convs.sort(key=lambda c: c.updated or c.created, reverse=True)
        return convs

    def search(self, query: str) -> list[Conversation]:
        q = query.strip().lower()
        if not q:
            return self.list_all()
        result = []
        for c in self.list_all():
            if q in c.title.lower() or any(q in m.content.lower() for m in c.messages):
                result.append(c)
        return result
