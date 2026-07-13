"""문서 로더: txt / md / pdf / docx → 순수 텍스트."""
from __future__ import annotations

from pathlib import Path

SUPPORTED = {".txt", ".md", ".markdown", ".pdf", ".docx"}


def load_text(path: str | Path) -> str:
    p = Path(path)
    ext = p.suffix.lower()
    if ext in (".txt", ".md", ".markdown"):
        return p.read_text(encoding="utf-8", errors="ignore")
    if ext == ".pdf":
        return _load_pdf(p)
    if ext == ".docx":
        return _load_docx(p)
    raise ValueError(f"지원하지 않는 형식입니다: {ext}")


def _load_pdf(p: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(p))
    parts = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
    return "\n\n".join(parts)


def _load_docx(p: Path) -> str:
    import docx  # python-docx

    d = docx.Document(str(p))
    return "\n".join(para.text for para in d.paragraphs)
