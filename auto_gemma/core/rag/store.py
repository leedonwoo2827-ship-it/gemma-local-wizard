"""sqlite + numpy 벡터 저장소 (코사인 유사도).

임베딩은 삽입 시 L2 정규화하여 검색을 단일 행렬곱으로 처리한다.
차원/모델 정보를 함께 저장해 임베딩 모델 교체 시 혼선을 방지한다.
"""
from __future__ import annotations

import sqlite3
import threading
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass
class Hit:
    doc_id: str
    source: str
    text: str
    score: float


@dataclass
class DocInfo:
    doc_id: str
    source: str
    chunks: int


class VectorStore:
    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        self._lock = threading.Lock()
        self._db = sqlite3.connect(self.db_path, check_same_thread=False)
        self._db.execute(
            """CREATE TABLE IF NOT EXISTS chunks(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id TEXT NOT NULL,
                source TEXT NOT NULL,
                ordinal INTEGER NOT NULL,
                text TEXT NOT NULL,
                embedding BLOB NOT NULL,
                dim INTEGER NOT NULL,
                model TEXT NOT NULL
            )"""
        )
        self._db.commit()
        self._cache: tuple[list[int], np.ndarray] | None = None

    # ------------------------------------------------------------------
    def close(self) -> None:
        self._db.close()

    def _invalidate(self) -> None:
        self._cache = None

    @staticmethod
    def _normalize(vec: np.ndarray) -> np.ndarray:
        n = np.linalg.norm(vec)
        return vec / n if n > 1e-9 else vec

    # ------------------------------------------------------------------ 쓰기
    def add_document(self, doc_id: str, source: str, chunks: list[str],
                     embeddings: list[list[float]], model: str) -> None:
        with self._lock:
            for i, (txt, emb) in enumerate(zip(chunks, embeddings)):
                vec = self._normalize(np.asarray(emb, dtype=np.float32))
                self._db.execute(
                    "INSERT INTO chunks(doc_id,source,ordinal,text,embedding,dim,model)"
                    " VALUES(?,?,?,?,?,?,?)",
                    (doc_id, source, i, txt, vec.tobytes(), vec.shape[0], model),
                )
            self._db.commit()
            self._invalidate()

    def delete_document(self, doc_id: str) -> None:
        with self._lock:
            self._db.execute("DELETE FROM chunks WHERE doc_id=?", (doc_id,))
            self._db.commit()
            self._invalidate()

    def clear(self) -> None:
        with self._lock:
            self._db.execute("DELETE FROM chunks")
            self._db.commit()
            self._invalidate()

    # ------------------------------------------------------------------ 조회
    def documents(self) -> list[DocInfo]:
        cur = self._db.execute(
            "SELECT doc_id, source, COUNT(*) FROM chunks GROUP BY doc_id, source ORDER BY doc_id"
        )
        return [DocInfo(d, s, n) for d, s, n in cur.fetchall()]

    def chunk_count(self) -> int:
        return self._db.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]

    def _matrix(self) -> tuple[list[int], np.ndarray]:
        if self._cache is not None:
            return self._cache
        ids: list[int] = []
        rows: list[np.ndarray] = []
        cur = self._db.execute("SELECT id, embedding, dim FROM chunks")
        for cid, blob, dim in cur.fetchall():
            ids.append(cid)
            rows.append(np.frombuffer(blob, dtype=np.float32, count=dim))
        mat = np.vstack(rows) if rows else np.zeros((0, 1), dtype=np.float32)
        self._cache = (ids, mat)
        return self._cache

    def search(self, query_vec: list[float], k: int = 5) -> list[Hit]:
        ids, mat = self._matrix()
        if mat.shape[0] == 0:
            return []
        q = self._normalize(np.asarray(query_vec, dtype=np.float32))
        if q.shape[0] != mat.shape[1]:
            # 차원 불일치 (임베딩 모델 변경) — 검색 불가
            return []
        sims = mat @ q
        k = min(k, sims.shape[0])
        top = np.argpartition(-sims, k - 1)[:k]
        top = top[np.argsort(-sims[top])]
        hits = []
        for idx in top:
            cid = ids[int(idx)]
            row = self._db.execute(
                "SELECT doc_id, source, text FROM chunks WHERE id=?", (cid,)
            ).fetchone()
            if row:
                hits.append(Hit(row[0], row[1], row[2], float(sims[idx])))
        return hits


def build_context(hits: list[Hit]) -> str:
    """검색 결과를 시스템 프롬프트용 참고 블록으로 조립."""
    if not hits:
        return ""
    lines = ["다음 참고 문서를 바탕으로 답하세요. 문서에 없으면 모른다고 하세요.\n"]
    for i, h in enumerate(hits, 1):
        lines.append(f"[문서 {i}] (출처: {h.source})\n{h.text}\n")
    return "\n".join(lines)
