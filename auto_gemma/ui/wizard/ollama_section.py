"""Ollama 상태 표시 + 설치 섹션."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QProgressBar, QPushButton, QWidget

from auto_gemma.core.ollama_client import OllamaClient
from auto_gemma.ui.widgets.common import Card, muted, row
from auto_gemma.workers.base import CancellableWorker
from auto_gemma.workers.tasks import install_ollama_task


class OllamaSection(Card):
    status_changed = Signal(str)  # running | installed | absent

    def __init__(self, parent: QWidget | None = None):
        super().__init__("2. Ollama (Gemma 실행 엔진)", parent)
        self.client = OllamaClient()
        self._worker: CancellableWorker | None = None

        self.add(muted(
            "Ollama 는 Gemma 를 내 컴퓨터에서 직접 돌려주는 '엔진'입니다. "
            "이게 있어야 모델을 다운로드하고 대화할 수 있어요."
        ))

        self.status_label = QLabel("상태 확인 중...")
        self.install_btn = QPushButton("Ollama 설치")
        self.install_btn.setObjectName("primary")
        self.install_btn.clicked.connect(self.install)
        self.add_layout(row(self.status_label, None, self.install_btn))

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)  # indeterminate
        self.progress.hide()
        self.add(self.progress)

        self.log_label = muted("")
        self.add(self.log_label)

    def refresh(self) -> None:
        status = self.client.status()
        if status == "running":
            self.status_label.setText("✅ 설치됨 · 실행 중")
            self.status_label.setObjectName("green")
            self.install_btn.setEnabled(False)
            self.install_btn.setText("설치 완료")
        elif status == "installed":
            self.status_label.setText("⚠️ 설치됨 · 실행 안 됨 — 서버를 시작합니다")
            self.status_label.setObjectName("yellow")
            self.client.start_server()
            self.install_btn.setEnabled(False)
            self.install_btn.setText("실행 중...")
        else:
            self.status_label.setText("❌ 설치되어 있지 않습니다.")
            self.status_label.setObjectName("red")
            self.install_btn.setEnabled(True)
            self.install_btn.setText("Ollama 설치")
        self.status_label.setStyleSheet("")  # objectName 재적용 트리거
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)
        self.status_changed.emit(status)

    def install(self) -> None:
        self.install_btn.setEnabled(False)
        self.progress.show()
        self.log_label.setText("설치를 시작합니다...")
        worker = CancellableWorker(install_ollama_task)
        worker.signals.message.connect(self.log_label.setText)
        worker.signals.finished.connect(self._on_done)
        worker.signals.error.connect(self._on_error)
        self._worker = worker
        from auto_gemma.ui.widgets.common import download_pool
        download_pool().start(worker)

    def _on_done(self, ok: bool) -> None:
        self.progress.hide()
        if ok:
            self.log_label.setText("✅ Ollama 설치/실행 완료!")
        else:
            self.log_label.setText("❌ 설치에 실패했습니다. https://ollama.com 에서 수동 설치해 주세요.")
            self.install_btn.setEnabled(True)
        self.refresh()

    def _on_error(self, err: str) -> None:
        self.progress.hide()
        self.install_btn.setEnabled(True)
        self.log_label.setText(f"오류: {err.splitlines()[-1] if err else ''}")
