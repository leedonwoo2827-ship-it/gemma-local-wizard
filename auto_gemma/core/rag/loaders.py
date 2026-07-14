"""문서 로더: txt / md / pdf / docx → 순수 텍스트."""
from __future__ import annotations

from pathlib import Path

SUPPORTED = {".txt", ".md", ".markdown", ".pdf", ".docx", ".hwpx"}


def load_text(path: str | Path) -> str:
    p = Path(path)
    ext = p.suffix.lower()
    if ext in (".txt", ".md", ".markdown"):
        return p.read_text(encoding="utf-8", errors="ignore")
    if ext == ".pdf":
        return _load_pdf(p)
    if ext == ".docx":
        return _load_docx(p)
    if ext == ".hwpx":
        return _load_hwpx(p)
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


def _load_hwpx(p: Path) -> str:
    """신형 한글 문서(.hwpx)에서 본문 텍스트를 추출.

    hwpx 는 ZIP 컨테이너이며 본문은 Contents/section*.xml(OWPML) 에 있다.
    한글 프로그램 없이 표준 라이브러리로 문단(hp:p)·텍스트(hp:t) 단위로 읽는다.
    """
    import zipfile
    from xml.etree import ElementTree as ET

    def localname(tag: str) -> str:
        return tag.rsplit("}", 1)[-1]  # 네임스페이스 접두사 제거

    def walk(elem, out: list[str]) -> None:
        tag = localname(elem.tag)
        if tag == "p":            # 문단 시작 → 줄바꿈
            out.append("\n")
        if tag == "t" and elem.text:  # 실제 텍스트 조각
            out.append(elem.text)
        for child in elem:
            walk(child, out)

    parts: list[str] = []
    with zipfile.ZipFile(str(p)) as z:
        sections = sorted(
            n for n in z.namelist()
            if n.startswith("Contents/section") and n.endswith(".xml")
        )
        for name in sections:
            try:
                root = ET.fromstring(z.read(name))
            except ET.ParseError:
                continue
            walk(root, parts)
            parts.append("\n")  # 섹션 사이 여백
    text = "".join(parts)
    # 과도한 빈 줄 정리
    lines = [ln.rstrip() for ln in text.split("\n")]
    return "\n".join(lines).strip()
