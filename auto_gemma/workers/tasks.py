"""워커에서 실행할 작업 함수들. 모두 (cancel_event, signals) 를 키워드로 받는다."""
from __future__ import annotations

from auto_gemma.core import summarizer
from auto_gemma.core.ollama_client import OllamaClient
from auto_gemma.core.rag import loaders


# --------------------------------------------------------------------- 채팅
def chat_task(model: str, messages: list[dict], options: dict | None = None,
              cancel_event=None, signals=None):
    client = OllamaClient()
    full = []
    for delta in client.chat(model, messages, options):
        if cancel_event and cancel_event.is_set():
            break
        full.append(delta)
        if signals:
            signals.token.emit(delta)
    return "".join(full)


# --------------------------------------------------------------------- PDF 요약
def summarize_task(path: str, ratio: float, model: str, options: dict | None = None,
                   cancel_event=None, signals=None):
    """PDF/txt/md 파일을 읽어 원문의 약 ratio 분량으로 요약한다.

    반환: {"summary": str, "source_chars": int} 또는 "cancelled".
    """
    if signals:
        signals.message.emit("문서에서 텍스트 추출 중...")
    text = loaders.load_text(path)
    if cancel_event and cancel_event.is_set():
        return "cancelled"

    result = summarizer.summarize(
        text, ratio, model, options,
        cancel_event=cancel_event, signals=signals,
    )
    if result == "cancelled":
        return "cancelled"
    return {"summary": result, "source_chars": len(text.strip())}


# --------------------------------------------------------------------- 모델 pull(폴백)
def pull_model_task(model: str, cancel_event=None, signals=None):
    """모델이 없을 때 UI 에서 내려받기 위한 폴백."""
    client = OllamaClient()
    if signals:
        signals.message.emit(f"{model} 다운로드 시작...")
    for prog in client.pull(model):
        if cancel_event and cancel_event.is_set():
            return "cancelled"
        if signals:
            signals.progress.emit(prog)
    return model
