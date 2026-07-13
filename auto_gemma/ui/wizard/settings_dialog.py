"""설정 다이얼로그 — 모델/데이터 저장 위치 지정.

C: 용량이 부족할 때 큰 모델 파일을 D: 등 다른 드라이브에 저장하도록 한다.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from auto_gemma.app import config
from auto_gemma.ui.widgets.common import download_pool, muted
from auto_gemma.workers.base import CancellableWorker
from auto_gemma.workers.tasks import set_models_dir_task


def _default_models_dir() -> str:
    """여유 공간이 가장 큰 드라이브를 추천 (Windows: C: 외 우선)."""
    if os.name == "nt":
        best, best_free = None, -1
        for letter in "DEFGCH":
            root = f"{letter}:\\"
            if os.path.exists(root):
                try:
                    free = shutil.disk_usage(root).free
                except OSError:
                    continue
                # C: 는 마지막 순위로 밀기 위해 약간 감점
                score = free - (50 * 1024 ** 3 if letter == "C" else 0)
                if score > best_free:
                    best_free, best = score, letter
        if best:
            return f"{best}:\\AutoGemma\\models"
    return str(Path.home() / "AutoGemma" / "models")


class SettingsDialog(QDialog):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("설정")
        self.resize(620, 380)
        self._worker: CancellableWorker | None = None

        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 20, 22, 20)
        lay.setSpacing(10)

        title = QLabel("저장 위치 설정")
        title.setObjectName("sectionTitle")
        lay.addWidget(title)
        lay.addWidget(muted(
            "모델 파일은 용량이 큽니다(4B≈3.3GB, 12B≈8GB). C: 드라이브 용량이 부족하면 "
            "여유 있는 드라이브(예: D:)로 지정하세요. 모델을 내려받기 전에 지정하는 것을 권장합니다."
        ))

        # 모델 저장 위치
        lay.addWidget(QLabel("① Ollama 모델 저장 위치 (OLLAMA_MODELS)"))
        self.models_edit = QLineEdit(config.get_models_dir() or "")
        self.models_edit.setPlaceholderText("미설정 시 기본 위치(사용자 폴더의 .ollama)")
        pick_models = QPushButton("폴더 선택")
        pick_models.clicked.connect(self._pick_models)
        suggest = QPushButton("추천 위치")
        suggest.clicked.connect(lambda: self.models_edit.setText(_default_models_dir()))
        row1 = QHBoxLayout()
        row1.addWidget(self.models_edit, 1)
        row1.addWidget(suggest)
        row1.addWidget(pick_models)
        lay.addLayout(row1)

        # 데이터(대화/지식도서관) 저장 위치
        lay.addWidget(QLabel("② 대화·지식도서관 데이터 위치"))
        cur_data = config.load_settings().get("data_dir", "")
        self.data_edit = QLineEdit(cur_data)
        self.data_edit.setPlaceholderText(str(config.documents_dir() / "GemmaChat") + " (기본)")
        pick_data = QPushButton("폴더 선택")
        pick_data.clicked.connect(self._pick_data)
        row2 = QHBoxLayout()
        row2.addWidget(self.data_edit, 1)
        row2.addWidget(pick_data)
        lay.addLayout(row2)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()
        lay.addWidget(self.progress)
        self.status = muted("")
        lay.addWidget(self.status)
        lay.addStretch(1)

        btns = QHBoxLayout()
        btns.addStretch(1)
        self.save_btn = QPushButton("저장 및 적용")
        self.save_btn.setObjectName("primary")
        close_btn = QPushButton("닫기")
        self.save_btn.clicked.connect(self._save)
        close_btn.clicked.connect(self.reject)
        btns.addWidget(close_btn)
        btns.addWidget(self.save_btn)
        lay.addLayout(btns)

    def _pick_models(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "모델 저장 폴더 선택")
        if d:
            self.models_edit.setText(d)

    def _pick_data(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "데이터 저장 폴더 선택")
        if d:
            self.data_edit.setText(d)

    def _save(self) -> None:
        # 데이터 위치는 즉시 반영
        data_path = self.data_edit.text().strip()
        config.update_setting("data_dir", data_path or None)

        models_path = self.models_edit.text().strip()
        if not models_path:
            config.update_setting("models_dir", None)
            os.environ.pop("OLLAMA_MODELS", None)
            self.status.setText("✅ 기본 위치로 설정했습니다.")
            return

        # 모델 위치 변경은 서버 재시작이 필요할 수 있어 워커로 처리
        self.save_btn.setEnabled(False)
        self.progress.show()
        self.status.setText("적용 중...")
        worker = CancellableWorker(set_models_dir_task, models_path)
        worker.signals.message.connect(self.status.setText)
        worker.signals.finished.connect(self._on_done)
        worker.signals.error.connect(self._on_error)
        self._worker = worker
        download_pool().start(worker)

    def _on_done(self, ok) -> None:
        self.progress.hide()
        self.save_btn.setEnabled(True)
        self.status.setText("✅ 저장 위치가 적용되었습니다." if ok else "❌ 적용 실패")

    def _on_error(self, err: str) -> None:
        self.progress.hide()
        self.save_btn.setEnabled(True)
        self.status.setText(f"오류: {err.splitlines()[-1] if err else ''}")
