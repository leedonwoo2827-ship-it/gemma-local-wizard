"""문서 로더: txt / md / pdf → 순수 텍스트.

요약 기능은 '텍스트 복사가 가능한' PDF 를 전제로 한다(스캔 이미지 PDF 는
텍스트가 거의 추출되지 않는다). pypdf 의 extract_text() 를 사용한다.
"""
from __future__ import annotations

from pathlib import Path

SUPPORTED = {".txt", ".md", ".markdown", ".pdf"}


def load_text(path: str | Path) -> str:
    p = Path(path)
    ext = p.suffix.lower()
    if ext in (".txt", ".md", ".markdown"):
        return p.read_text(encoding="utf-8", errors="ignore")
    if ext == ".pdf":
        return _load_pdf(p)
    raise ValueError(f"지원하지 않는 형식입니다: {ext}")


def _load_pdf(p: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(p))
    parts = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
    return "\n\n".join(parts)
