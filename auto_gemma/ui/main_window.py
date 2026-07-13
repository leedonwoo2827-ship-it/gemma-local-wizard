"""메인 창 — 상단바(모델/Ollama 상태) + 탭(채팅 · PDF 요약)."""
from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from auto_gemma.app.config import DEFAULT_MODEL
from auto_gemma.core.ollama_client import OllamaClient
from auto_gemma.ui.chat.chat_window import ChatView
from auto_gemma.ui.summary.summary_view import SummaryView


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gemma PDF 요약 & 채팅")
        self.resize(1080, 720)

        self.client = OllamaClient()

        central = QWidget()
        central.setObjectName("root")
        root = QVBoxLayout(central)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)
        root.addLayout(self._topbar())

        self.tabs = QTabWidget()
        self.chat_view = ChatView(self.current_model)
        self.summary_view = SummaryView(self.current_model)
        self.tabs.addTab(self.chat_view, "채팅")
        self.tabs.addTab(self.summary_view, "PDF 요약")
        root.addWidget(self.tabs, 1)

        self.setCentralWidget(central)

        self.refresh_status()
        self.refresh_models()

    # ------------------------------------------------------------------ 상단바
    def _topbar(self):
        bar = QHBoxLayout()
        self.model_combo = QComboBox()
        self.model_combo.setMinimumWidth(200)
        refresh = QPushButton("새로고침")
        refresh.clicked.connect(self._on_refresh)
        self.status_label = QLabel("")
        self.status_label.setObjectName("muted")

        bar.addWidget(QLabel("모델:"))
        bar.addWidget(self.model_combo)
        bar.addWidget(refresh)
        bar.addStretch(1)
        bar.addWidget(self.status_label)
        return bar

    def current_model(self) -> str:
        return self.model_combo.currentText() or DEFAULT_MODEL

    # ------------------------------------------------------------------ 상태/모델
    def _on_refresh(self) -> None:
        self.refresh_status()
        self.refresh_models()

    def refresh_status(self) -> None:
        st = self.client.status()
        if st == "running":
            self.status_label.setText("● Ollama 실행 중")
            self.status_label.setObjectName("green")
        elif st == "installed":
            self.status_label.setText("○ Ollama 시작 중...")
            self.status_label.setObjectName("yellow")
            self.client.start_server()
            QTimer.singleShot(1500, self._recheck_after_start)
        else:
            self.status_label.setText("× Ollama 없음 — ollama.com 에서 설치하세요")
            self.status_label.setObjectName("red")
        self._restyle(self.status_label)

    def _recheck_after_start(self) -> None:
        if self.client.is_running():
            self.status_label.setText("● Ollama 실행 중")
            self.status_label.setObjectName("green")
        else:
            self.status_label.setText("× Ollama 응답 없음 — 잠시 후 [새로고침]")
            self.status_label.setObjectName("red")
        self._restyle(self.status_label)
        self.refresh_models()

    def refresh_models(self) -> None:
        current = self.model_combo.currentText()
        self.model_combo.blockSignals(True)
        self.model_combo.clear()
        models: list[str] = []
        if self.client.is_running():
            try:
                models = [m.name for m in self.client.list_models() if m.name.startswith("gemma")]
            except Exception:  # noqa: BLE001
                models = []
        if not models:
            self.model_combo.addItem(DEFAULT_MODEL)
        else:
            self.model_combo.addItems(models)
            target = current if current in models else (
                DEFAULT_MODEL if DEFAULT_MODEL in models else models[0]
            )
            self.model_combo.setCurrentText(target)
        self.model_combo.blockSignals(False)

    @staticmethod
    def _restyle(w: QWidget) -> None:
        """objectName 변경 후 QSS 재적용."""
        w.style().unpolish(w)
        w.style().polish(w)

    # ------------------------------------------------------------------ 종료
    def closeEvent(self, event) -> None:
        self.chat_view.shutdown()
        self.summary_view.shutdown()
        super().closeEvent(event)
