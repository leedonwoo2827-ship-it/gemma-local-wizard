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
    return "\n\n".join(_load_pdf_pages(p))


def _load_pdf_pages(p: Path) -> list[str]:
    from pypdf import PdfReader

    reader = PdfReader(str(p))
    return [(page.extract_text() or "") for page in reader.pages]


def load_pages(path: str | Path) -> list[str]:
    """문서를 페이지 단위 텍스트 리스트로 반환.

    PDF 는 실제 페이지별로 나뉜다. txt/md/docx 는 페이지 개념이 없어
    전체를 한 요소짜리 리스트로 반환한다(→ 페이지 표기 생략됨).
    """
    p = Path(path)
    ext = p.suffix.lower()
    if ext == ".pdf":
        return _load_pdf_pages(p)
    return [load_text(p)]


def _load_docx(p: Path) -> str:
    import docx  # python-docx

    d = docx.Document(str(p))
    return "\n".join(para.text for para in d.paragraphs)
