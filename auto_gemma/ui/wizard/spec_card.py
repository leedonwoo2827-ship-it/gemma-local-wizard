"""내 컴퓨터 사양 카드 + VRAM 기반 추천 모델 표시."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from auto_gemma.core.recommend import Recommendation, recommend
from auto_gemma.core.system_info import SystemInfo
from auto_gemma.ui.widgets.common import Card
from auto_gemma.workers.base import CancellableWorker
from auto_gemma.workers.tasks import detect_system


class SpecCard(Card):
    """사양 감지 결과와 추천 모델을 보여준다. 추천 태그를 시그널로 알린다."""

    recommendation_ready = Signal(object)  # Recommendation

    def __init__(self, parent: QWidget | None = None):
        super().__init__("1. 내 컴퓨터 사양", parent)
        self.info: SystemInfo | None = None
        self.rec: Recommendation | None = None

        self.hw_label = QLabel("사양을 감지하는 중...")
        self.hw_label.setWordWrap(True)
        self.gpu_label = QLabel("")
        self.gpu_label.setWordWrap(True)

        self.rec_label = QLabel("")
        self.rec_label.setObjectName("accent")
        self.rec_label.setWordWrap(True)
        self.rec_sub = QLabel("")
        self.rec_sub.setObjectName("muted")
        self.rec_sub.setWordWrap(True)
        self.limit_label = QLabel("")
        self.limit_label.setObjectName("yellow")
        self.limit_label.setWordWrap(True)

        for w in (self.hw_label, self.gpu_label, self.rec_label,
                  self.rec_sub, self.limit_label):
            self.add(w)

    def detect_async(self) -> None:
        worker = CancellableWorker(detect_system)
        worker.signals.finished.connect(self._on_detected)
        worker.signals.error.connect(lambda e: self.hw_label.setText(f"사양 감지 오류:\n{e}"))
        from auto_gemma.ui.widgets.common import general_pool
        general_pool().start(worker)

    def _on_detected(self, info: SystemInfo) -> None:
        self.info = info
        if info.unified_memory:
            vram_field = f"<b>통합 메모리</b> 🔒: {info.vram_gb:g} GB (RAM 공유)"
        elif info.vram_gb:
            vram_field = f"<b>VRAM</b> 🔒: {info.vram_gb:g} GB"
        else:
            vram_field = "<b>VRAM</b> 🔒: 감지 안됨(통합 추정)"
        self.hw_label.setText(
            f"<b>OS</b>: {info.os_line}   |   "
            f"<b>RAM</b>: {info.ram_gb:g} GB   |   "
            f"{vram_field}"
        )
        self.gpu_label.setText(f"<b>GPU</b>: {info.gpu_line}")

        self.rec = recommend(info.vram_gb, info.ram_gb)
        self.rec_label.setText(f"🔥 추천 모델: {self.rec.summary()}")
        self.rec_sub.setText("균형형. 일반 노트북에 무난함. — 사양에 맞춰 자동 추천된 모델입니다.")
        self.limit_label.setText(f"🔒 {self.rec.limit_text()}")
        self.recommendation_ready.emit(self.rec)
