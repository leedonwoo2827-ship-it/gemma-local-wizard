"""문서 요약 (map 방식, Qt 비의존).

긴 문서(수백 페이지 책 등)는 한 번에 모델 컨텍스트에 넣을 수 없으므로,
텍스트를 구간(청크)으로 나눠 각 구간을 목표 분량으로 요약한 뒤 이어 붙인다.
구간별 목표 분량을 원문 대비 `ratio`(0.10 / 0.05)로 잡으면 전체 요약도
대략 원문의 10% / 5% 분량이 된다.

스트리밍: 요약 델타를 signals.token 으로 실시간 방출한다(호출자가 결과창에
append). 진행률은 signals.progress 로 {"completed","total"} 를 방출한다.
호출자가 cancel_event 를 set 하면 즉시 중단하고 "cancelled" 를 반환한다.
"""
from __future__ import annotations

import re

from auto_gemma.core.ollama_client import OllamaClient

# 계층 기호별 깊이 (앞쪽일수록 상위):
#   1.  →  (1)  →  1)  →  ①  →  ㉠  →  ⓐ  →  가.  →  A.
_LEVEL_PATTERNS = [
    (re.compile(r"^\d+\.(?!\d)"), 0),                          # 1. 2.
    (re.compile(r"^\(\d+\)"), 1),                               # (1) (2)
    (re.compile(r"^\d+\)"), 2),                                 # 1) 2)
    (re.compile(r"^[①-⑳]"), 3),                       # ① ②
    (re.compile(r"^[㉠-㉭]"), 4),                       # ㉠ ㉡
    (re.compile(r"^[ⓐ-ⓩ]"), 5),                       # ⓐ ⓑ
    (re.compile(r"^[가나다라마바사아자차카타파하]\.(?=\s|$)"), 6),  # 가. 나.
    (re.compile(r"^[A-Z]\.(?=\s|$)"), 7),                       # A. B.
]
_INDENT_UNIT = "   "  # 깊이 1단계당 공백 3칸

# 모델이 프롬프트의 형식 설명을 그대로 베껴 출력하는 경우(프롬프트 누출)를 걸러낸다.
# 우리 지시문에만 등장하는 고유 문구라 실제 요약 내용과 충돌할 위험이 낮다.
_ECHO_MARKERS = (
    "계층 기호",
    "위계",
    "개조식 정리 노트",
    "반괄호",
)
# 굵게/강조용 마크다운 기호(**, __, *) — 서식 없이 쓰기로 했으므로 제거한다.
_EMPHASIS = re.compile(r"\*\*|__|\*(?=\S)|(?<=\S)\*")
# 줄 앞머리의 불릿/대시 기호(•, ·, -, *, ● 등) — 이번 위계에선 쓰지 않으므로 떼어낸다.
_LEADING_BULLET = re.compile(r"^[\-–—•·▪●○◦*]\s+")


def _clean_line(line: str) -> str:
    """마크다운 강조 기호와 앞머리 불릿/대시를 제거하고 공백을 정리한다."""
    line = _EMPHASIS.sub("", line).strip()
    line = _LEADING_BULLET.sub("", line).strip()
    return line


def _normalize_outline(text: str) -> str:
    """모델 출력의 계층 기호를 읽어 깊이에 맞는 들여쓰기를 다시 매긴다.

    - 프롬프트 형식 설명을 베낀 줄(프롬프트 누출)은 제거한다.
    - 마크다운 강조 기호(**)·앞머리 불릿(•, -)은 제거한다.
    - 계층 기호(1./(1)/1)/①/㉠/ⓐ/가./A.)에 맞춰 계단식으로 들여쓴다.
    - 기호가 없는 줄은 직전 계층보다 한 단계 아래로 붙인다.
    """
    lines: list[str] = []
    last_marked_depth = -1
    for raw in text.split("\n"):
        line = _clean_line(raw)
        if not line:
            lines.append("")
            continue
        if any(marker in line for marker in _ECHO_MARKERS):
            continue  # 형식 설명 누출 줄 제거
        depth = None
        for pattern, level in _LEVEL_PATTERNS:
            if pattern.match(line):
                depth = level
                last_marked_depth = level
                break
        if depth is None:
            depth = min(last_marked_depth + 1, len(_LEVEL_PATTERNS) - 1)
        lines.append(_INDENT_UNIT * depth + line)
    # 누출 줄 제거로 생긴 연속 빈 줄을 하나로 압축
    out: list[str] = []
    for ln in lines:
        if ln == "" and (not out or out[-1] == ""):
            continue
        out.append(ln)
    return "\n".join(out).strip("\n")

# 한 번에 모델에 넣을 구간 크기(문자). gemma3 기본 num_ctx(8192)에 여유를 둔다.
MAP_CHUNK_CHARS = 8000
# 구간 요약 최소 목표 분량(너무 짧은 구간도 최소한의 요약은 남긴다).
MIN_TARGET_CHARS = 80

# 지원 비율
RATIOS = {"10%": 0.10, "5%": 0.05}


def _cancelled(cancel_event) -> bool:
    return bool(cancel_event and cancel_event.is_set())


def _map_prompt(chunk: str, target_chars: int) -> str:
    return (
        "다음은 어떤 문서의 한 구간이다. 이 구간의 내용을 시험 대비용 개조식 정리 노트로 정리하라.\n"
        "[위계 기호] — 상위에서 하위로 이 순서만 사용한다(필요한 깊이까지만).\n"
        "  1.  →  (1)  →  1)  →  ①  →  ㉠  →  ⓐ  →  가.  →  A.\n"
        "[형식]\n"
        "- 상위 개념일수록 앞쪽 기호(1., (1))를, 하위·세부일수록 뒤쪽 기호(㉠, ⓐ, 가., A.)를 쓴다.\n"
        "- 정의 항목은 '① 정의 : ...' 형태로 적는다.\n"
        "- 각 항목은 한 줄로, 개조식(명사형 또는 '~이다', '~함')으로 짧고 명료하게 끝맺는다.\n"
        "- 위 8가지 위계 기호만 쓴다. 불릿(•, -, *)·굵게(**) 등 다른 기호는 절대 쓰지 않는다.\n"
        "[규칙]\n"
        "- 원문과 같은 언어로 작성한다.\n"
        "- 위 [위계 기호]·[형식]·[규칙] 설명 문구 자체는 출력에 절대 포함하지 마라. 오직 아래 문서 내용만 정리한다.\n"
        "- '정리:'·'요약:' 같은 머리말이나 인사말 없이 정리 본문만 출력한다.\n"
        "- 예시·중복·군더더기는 생략하고 핵심(정의·수치·주장·결론)만 남긴다.\n"
        f"- 전체 분량은 약 {target_chars}자 내외로 한다.\n\n"
        "=== 구간 시작 ===\n"
        f"{chunk}\n"
        "=== 구간 끝 ==="
    )


def _complete(client, model, prompt, options, cancel_event, signals) -> str:
    """단일 요청을 스트리밍으로 완료. 토큰을 signals.token 으로 방출."""
    parts: list[str] = []
    for delta in client.chat(model, [{"role": "user", "content": prompt}], options):
        if _cancelled(cancel_event):
            break
        parts.append(delta)
        if signals:
            signals.token.emit(delta)
    return "".join(parts)


def _page_header(page: int) -> str:
    return f"── p.{page} ──"


# ---------------------------------------------------------------- 페이지 청킹
def _chunk_pages(pages: list[str], chunk_size: int) -> list[tuple[int, str]]:
    """페이지 리스트를 (시작페이지, 구간텍스트) 목록으로 묶는다.

    페이지 경계를 지키며 chunk_size 근처까지 모은다. 한 페이지가 너무 크면
    쪼개되 시작페이지 번호는 유지한다.
    """
    chunks: list[tuple[int, str]] = []
    buf = ""
    buf_start = 1
    for idx, page in enumerate(pages, start=1):
        page = (page or "").strip()
        if not page:
            continue
        if not buf:
            buf, buf_start = page, idx
        elif len(buf) + 2 + len(page) <= chunk_size:
            buf += "\n\n" + page
        else:
            chunks.append((buf_start, buf))
            buf, buf_start = page, idx
        while len(buf) > chunk_size:
            chunks.append((buf_start, buf[:chunk_size]))
            buf = buf[chunk_size:]
    if buf.strip():
        chunks.append((buf_start, buf))
    return chunks


def summarize(pages: list[str] | str, ratio: float, model: str, options: dict | None = None,
              client: OllamaClient | None = None,
              cancel_event=None, signals=None) -> str:
    """문서(페이지 리스트)를 원문의 약 `ratio` 분량으로 요약해 반환.

    pages 가 문자열이면 페이지 구분 없는 단일 문서로 간주한다.
    반환값: 요약 전문(str). 취소 시 "cancelled".
    """
    if isinstance(pages, str):
        pages = [pages]
    pages = [p for p in (pages or []) if (p or "").strip()]
    if not pages:
        raise RuntimeError("텍스트가 비어 있습니다. 텍스트 복사가 가능한 PDF 인지 확인하세요.")

    client = client or OllamaClient()
    chunks = _chunk_pages(pages, MAP_CHUNK_CHARS)
    total = len(chunks)
    show_pages = len(pages) > 1  # 실제 페이지가 여러 개일 때만 페이지 표기

    partials: list[str] = []
    for i, (start_page, ch) in enumerate(chunks):
        if _cancelled(cancel_event):
            return "cancelled"
        if signals:
            signals.message.emit(f"요약 중... ({i + 1}/{total} 구간, p.{start_page}~)")
        target = max(MIN_TARGET_CHARS, int(len(ch) * ratio))
        header = _page_header(start_page) if show_pages else ""
        if signals and header:
            signals.token.emit(header + "\n")
        out = _complete(client, model, _map_prompt(ch, target), options, cancel_event, signals)
        if _cancelled(cancel_event):
            return "cancelled"
        out = _normalize_outline(out.strip())
        if out:
            partials.append((header + "\n" + out).strip("\n") if header else out)
        if signals:
            signals.progress.emit({"completed": i + 1, "total": total})
            if i < total - 1:
                signals.token.emit("\n\n")  # 결과창에서 구간 사이 여백

    return "\n\n".join(partials)
