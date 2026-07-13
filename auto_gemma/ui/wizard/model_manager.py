"""Gemma 모델 선택/설치/업데이트/삭제/실행 섹션."""
from __future__ import annotations

import platform
import subprocess

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QLabel,
    QProgressBar,
    QPushButton,
    QWidget,
)

from auto_gemma.app.config import GEMMA_CATALOG, spec_for
from auto_gemma.core.ollama_client import OllamaClient
from auto_gemma.ui.widgets.common import Card, muted, row
from auto_gemma.workers.base import CancellableWorker
from auto_gemma.workers.tasks import delete_model_task, pull_model_task


class ModelManager(Card):
    models_changed = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__("3. Gemma 모델 선택 및 관리", parent)
        self.client = OllamaClient()
        self._worker: CancellableWorker | None = None

        self.hint = muted("")
        self.add(self.hint)

        self.combo = QComboBox()
        for m in GEMMA_CATALOG:
            self.combo.addItem(f"{m.label}", m.tag)
        self.combo.currentIndexChanged.connect(self._update_spec)
        self.spec_label = QLabel("")
        self.spec_label.setObjectName("muted")
        self.add_layout(row(QLabel("모델:"), self.combo, None))
        self.add(self.spec_label)

        self.install_btn = QPushButton("설치 (Ollama 포함)")
        self.install_btn.setObjectName("success")
        self.update_btn = QPushButton("업데이트")
        self.delete_btn = QPushButton("삭제")
        self.delete_btn.setObjectName("danger")
        self.run_btn = QPushButton("실행 (터미널)")
        self.install_btn.clicked.connect(lambda: self._pull(update=False))
        self.update_btn.clicked.connect(lambda: self._pull(update=True))
        self.delete_btn.clicked.connect(self._delete)
        self.run_btn.clicked.connect(self._run_terminal)
        self.add_layout(row(self.install_btn, self.update_btn,
                            self.delete_btn, self.run_btn))

        self.progress = QProgressBar()
        self.progress.hide()
        self.add(self.progress)
        self.status_label = muted("")
        self.add(self.status_label)

        self._update_spec()

    # --------------------------------------------------------------- 상태
    def set_ollama_available(self, available: bool) -> None:
        if available:
            self.hint.setText("설치된 모델을 관리하거나 새 모델을 내려받으세요.")
        else:
            self.hint.setText("⚠️ Ollama 가 아직 없어요 — 아래 '설치' 버튼이 Ollama 설치까지 자동으로 해드립니다.")
        self.refresh_installed()

    def select_model(self, tag: str) -> None:
        idx = self.combo.findData(tag)
        if idx >= 0:
            self.combo.setCurrentIndex(idx)

    def current_tag(self) -> str:
        return self.combo.currentData()

    def _update_spec(self) -> None:
        spec = spec_for(self.current_tag())
        if spec:
            self.spec_label.setText(spec.spec_line())
        self.refresh_installed()

    def refresh_installed(self) -> None:
        tag = self.current_tag()
        installed = self.client.has_model(tag) if self.client.is_running() else False
        self.update_btn.setEnabled(installed)
        self.delete_btn.setEnabled(installed)
        self.run_btn.setEnabled(installed)
        self.install_btn.setText("재설치" if installed else "설치 (Ollama 포함)")

    # --------------------------------------------------------------- 동작
    def _busy(self, on: bool) -> None:
        for b in (self.install_btn, self.update_btn, self.delete_btn, self.run_btn, self.combo):
            b.setEnabled(not on)
        if on:
            self.progress.show()
            self.progress.setRange(0, 0)
        else:
            self.progress.hide()
            self.refresh_installed()

    def _pull(self, update: bool) -> None:
        tag = self.current_tag()
        self._busy(True)
        self.status_label.setText(f"{tag} {'업데이트' if update else '설치'} 준비 중...")
        worker = CancellableWorker(pull_model_task, tag, ensure_ollama=not update)
        worker.signals.message.connect(self.status_label.setText)
        worker.signals.progress.connect(self._on_progress)
        worker.signals.finished.connect(self._on_pull_done)
        worker.signals.error.connect(self._on_error)
        self._worker = worker
        from auto_gemma.ui.widgets.common import download_pool
        download_pool().start(worker)

    def _on_progress(self, prog: dict) -> None:
        total = prog.get("total")
        completed = prog.get("completed")
        status = prog.get("status", "")
        if total and completed is not None:
            pct = int(completed / total * 100)
            self.progress.setRange(0, 100)
            self.progress.setValue(pct)
            self.status_label.setText(f"{status} — {pct}%")
        elif status:
            self.status_label.setText(status)

    def _on_pull_done(self, result) -> None:
        self._busy(False)
        self.status_label.setText(f"✅ {result} 준비 완료!")
        self.models_changed.emit()

    def _delete(self) -> None:
        tag = self.current_tag()
        self._busy(True)
        worker = CancellableWorker(delete_model_task, tag)
        worker.signals.finished.connect(lambda r: (self._busy(False),
                                                   self.status_label.setText(f"🗑️ {r} 삭제됨"),
                                                   self.models_changed.emit()))
        worker.signals.error.connect(self._on_error)
        from auto_gemma.ui.widgets.common import general_pool
        general_pool().start(worker)

    def _run_terminal(self) -> None:
        tag = self.current_tag()
        exe = OllamaClient.find_executable() or "ollama"
        system = platform.system()
        try:
            if system == "Windows":
                subprocess.Popen(["cmd", "/k", exe, "run", tag], creationflags=0x00000010)  # CREATE_NEW_CONSOLE
            elif system == "Darwin":
                # Terminal.app 에서 실행
                script = f'tell application "Terminal" to do script "{exe} run {tag}"'
                subprocess.Popen(["osascript", "-e", script])
            else:
                # Linux: 사용 가능한 터미널을 순차 시도
                import shutil as _sh
                for term in ("x-terminal-emulator", "gnome-terminal", "konsole", "xterm"):
                    if _sh.which(term):
                        subprocess.Popen([term, "-e", exe, "run", tag])
                        break
                else:
                    self.status_label.setText("터미널을 찾지 못했습니다. 직접 'ollama run' 을 실행하세요.")
        except OSError as e:
            self.status_label.setText(f"터미널 실행 실패: {e}")

    def _on_error(self, err: str) -> None:
        self._busy(False)
        self.status_label.setText(f"오류: {err.splitlines()[-1] if err else ''}")
