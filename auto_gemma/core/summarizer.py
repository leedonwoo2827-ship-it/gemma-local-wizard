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
from auto_gemma.core.rag.chunker import chunk_text

# 계층 기호별 깊이 (앞쪽일수록 상위):
#   제목(구조): 1.  →  (1)  →  1)
#   내용(설명): ①  →  ㉠  →  ⓐ  →  •  →  -
_LEVEL_PATTERNS = [
    (re.compile(r"^\d+\."), 0),                          # 1. 2.        (최상위 제목)
    (re.compile(r"^\(\d+\)"), 1),                         # (1) (2)
    (re.compile(r"^\d+\)"), 2),                           # 1) 2)        (반괄호, 선택적 제목)
    (re.compile(r"^[①-⑳]"), 3),                 # ① ②         (내용 시작)
    (re.compile(r"^[㉠-㉭]"), 4),                 # ㉠ ㉡        (원문자)
    (re.compile(r"^[ⓐ-ⓩ]"), 5),                 # ⓐ ⓑ         (원영문)
    (re.compile(r"^[•·]"), 6),                            # • 앞점
    (re.compile(r"^[-–—]"), 7),                           # - 마이너스
]
_INDENT_UNIT = "   "  # 깊이 1단계당 공백 3칸


def _normalize_outline(text: str) -> str:
    """모델 출력의 계층 기호를 읽어 깊이에 맞는 들여쓰기를 다시 매긴다.

    모델이 들여쓰기를 빠뜨리거나 들쭉날쭉해도 기호만 맞으면 계단식으로 정렬된다.
    """
    lines: list[str] = []
    for raw in text.split("\n"):
        line = raw.strip()
        if not line:
            lines.append("")
            continue
        depth = 0
        for pattern, level in _LEVEL_PATTERNS:
            if pattern.match(line):
                depth = level
                break
        lines.append(_INDENT_UNIT * depth + line)
    return "\n".join(lines)

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
        "다음은 어떤 문서의 한 구간이다. 이 구간의 내용을 시험 대비용 '개조식 정리 노트'로 정리하라.\n"
        "[계층 기호] — 제목(구조)과 내용(설명)을 구분해 위(상위)→아래(하위) 순서로만 쓴다.\n"
        "  · 제목(구조): 1.  →  (1)  →  1)\n"
        "  · 내용(설명): ①  →  ㉠  →  ⓐ  →  •  →  -\n"
        "[형식]\n"
        "- 큰 갈래는 제목 기호(1., (1), 1))로, 실제 설명·정의·수치 등 '내용'은 ① 이하(①, ㉠, ⓐ, •, -)로 적는다.\n"
        "- 반괄호 1) 는 꼭 필요할 때만 쓰고, 구조가 단순하면 생략한다. 반괄호에는 내용을 직접 쓰지 않는다(제목 전용).\n"
        "- 정의 항목은 '① 정의 : ...' 형태로 적는다.\n"
        "- 각 항목은 한 줄로, 개조식(명사형 또는 '~이다', '~함')으로 짧고 명료하게 끝맺는다.\n"
        "- 각 항목은 줄바꿈으로 구분하고, 굵게·별표(**) 같은 서식 기호는 쓰지 않는다.\n"
        "[규칙]\n"
        "- 원문과 같은 언어로 작성한다.\n"
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


def summarize(text: str, ratio: float, model: str, options: dict | None = None,
              client: OllamaClient | None = None,
              cancel_event=None, signals=None) -> str:
    """text 를 원문의 약 `ratio` 분량으로 요약해 반환.

    반환값: 요약 전문(str). 취소 시 "cancelled".
    """
    text = (text or "").strip()
    if not text:
        raise RuntimeError("텍스트가 비어 있습니다. 텍스트 복사가 가능한 PDF 인지 확인하세요.")

    client = client or OllamaClient()
    chunks = chunk_text(text, chunk_size=MAP_CHUNK_CHARS, overlap=0)
    total = len(chunks)

    partials: list[str] = []
    for i, ch in enumerate(chunks):
        if _cancelled(cancel_event):
            return "cancelled"
        if signals:
            signals.message.emit(f"요약 중... ({i + 1}/{total} 구간)")
        target = max(MIN_TARGET_CHARS, int(len(ch) * ratio))
        out = _complete(client, model, _map_prompt(ch, target), options, cancel_event, signals)
        if _cancelled(cancel_event):
            return "cancelled"
        out = _normalize_outline(out.strip())
        if out:
            partials.append(out)
        if signals:
            signals.progress.emit({"completed": i + 1, "total": total})
            if i < total - 1:
                signals.token.emit("\n\n")  # 결과창에서 구간 사이 여백

    return "\n\n".join(partials)
