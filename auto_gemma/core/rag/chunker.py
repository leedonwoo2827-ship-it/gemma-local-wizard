"""재귀 문자 분할 (LangChain 불필요, 자체 구현)."""
from __future__ import annotations

_SEPARATORS = ["\n\n", "\n", ". ", "。", " ", ""]


def chunk_text(text: str, chunk_size: int = 900, overlap: int = 150) -> list[str]:
    text = text.strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]

    chunks = _split(text, chunk_size, _SEPARATORS)
    # 오버랩 적용
    if overlap <= 0 or len(chunks) <= 1:
        return chunks
    out = []
    for i, c in enumerate(chunks):
        if i == 0:
            out.append(c)
        else:
            tail = chunks[i - 1][-overlap:]
            out.append((tail + " " + c).strip())
    return out


def _split(text: str, size: int, seps: list[str]) -> list[str]:
    if len(text) <= size:
        return [text] if text.strip() else []
    sep = seps[0] if seps else ""
    rest = seps[1:] if len(seps) > 1 else [""]

    if sep == "":
        # 강제 분할
        return [text[i:i + size] for i in range(0, len(text), size)]

    parts = text.split(sep)
    chunks: list[str] = []
    buf = ""
    for part in parts:
        piece = part + sep
        if len(buf) + len(piece) <= size:
            buf += piece
        else:
            if buf.strip():
                chunks.append(buf.strip())
            if len(piece) > size:
                chunks.extend(_split(part, size, rest))
                buf = ""
            else:
                buf = piece
    if buf.strip():
        chunks.append(buf.strip())
    return [c for c in chunks if c.strip()]
