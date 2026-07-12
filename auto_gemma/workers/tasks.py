"""워커에서 실행할 작업 함수들. 모두 (cancel_event, signals) 를 키워드로 받는다."""
from __future__ import annotations

from auto_gemma.core import installer, system_info
from auto_gemma.core.ollama_client import OllamaClient
from auto_gemma.core.rag import chunker, loaders
from auto_gemma.core.rag.store import VectorStore


# --------------------------------------------------------------------- 시스템
def detect_system(cancel_event=None, signals=None):
    return system_info.detect()


# --------------------------------------------------------------------- 설치
def install_ollama_task(cancel_event=None, signals=None):
    def log(msg: str):
        if signals:
            signals.message.emit(msg)
    return installer.install_ollama(log=log, cancel=cancel_event)


# --------------------------------------------------------------------- pull
def pull_model_task(model: str, ensure_ollama: bool = False,
                    cancel_event=None, signals=None):
    client = OllamaClient()
    if ensure_ollama and not client.is_running():
        if signals:
            signals.message.emit("Ollama 가 없어 먼저 설치합니다...")

        def log(m):
            if signals:
                signals.message.emit(m)

        if not installer.install_ollama(log=log, cancel=cancel_event):
            raise RuntimeError("Ollama 설치 실패로 모델을 내려받을 수 없습니다.")

    if signals:
        signals.message.emit(f"{model} 다운로드 시작...")
    for prog in client.pull(model):
        if cancel_event and cancel_event.is_set():
            return "cancelled"
        if signals:
            signals.progress.emit(prog)
    return model


# --------------------------------------------------------------------- 삭제
def delete_model_task(model: str, cancel_event=None, signals=None):
    OllamaClient().delete(model)
    return model


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


# --------------------------------------------------------------------- 임베딩(문서 추가)
def ingest_document_task(store: VectorStore, doc_id: str, source: str, path: str,
                         embed_model: str, cancel_event=None, signals=None):
    if signals:
        signals.message.emit(f"문서 읽는 중: {source}")
    text = loaders.load_text(path)
    chunks = chunker.chunk_text(text)
    if not chunks:
        raise RuntimeError("문서에서 텍스트를 추출하지 못했습니다.")

    client = OllamaClient()
    # 임베딩 모델 확보
    if not client.has_model(embed_model):
        if signals:
            signals.message.emit(f"임베딩 모델({embed_model}) 다운로드 중...")
        for _ in client.pull(embed_model):
            if cancel_event and cancel_event.is_set():
                return "cancelled"

    if signals:
        signals.message.emit(f"임베딩 생성 중... ({len(chunks)}개 청크)")
    embeddings: list[list[float]] = []
    batch = 16
    for i in range(0, len(chunks), batch):
        if cancel_event and cancel_event.is_set():
            return "cancelled"
        embeddings.extend(client.embed(embed_model, chunks[i:i + batch]))
        if signals:
            signals.progress.emit({"completed": min(i + batch, len(chunks)), "total": len(chunks)})

    store.add_document(doc_id, source, chunks, embeddings, embed_model)
    return {"doc_id": doc_id, "chunks": len(chunks)}


def embed_query_task(query: str, embed_model: str, cancel_event=None, signals=None):
    return OllamaClient().embed(embed_model, [query])[0]
