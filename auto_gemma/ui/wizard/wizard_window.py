"""메인 설치 마법사 창."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from auto_gemma import __version__
from auto_gemma.core.recommend import Recommendation
from auto_gemma.ui.widgets.common import Card, muted
from auto_gemma.ui.wizard.model_manager import ModelManager
from auto_gemma.ui.wizard.ollama_section import OllamaSection
from auto_gemma.ui.wizard.spec_card import SpecCard


class WizardWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Gemma 로컬 설치 마법사 — Auto Gemma Starter v{__version__}")
        self.resize(920, 860)
        self._chat_window = None

        root = QWidget()
        root.setObjectName("root")
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)

        outer.addWidget(self._header())

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content.setObjectName("root")
        lay = QVBoxLayout(content)
        lay.setContentsMargins(20, 12, 20, 20)
        lay.setSpacing(14)

        self.spec_card = SpecCard()
        self.ollama_section = OllamaSection()
        self.model_manager = ModelManager()
        self.chat_card = self._chat_card()

        lay.addWidget(self.spec_card)
        lay.addWidget(self.ollama_section)
        lay.addWidget(self.model_manager)
        lay.addWidget(self.chat_card)
        lay.addStretch(1)

        scroll.setWidget(content)
        outer.addWidget(scroll, 1)
        self.setCentralWidget(root)

        # 시그널 연결
        self.spec_card.recommendation_ready.connect(self._on_recommend)
        self.ollama_section.status_changed.connect(self._on_ollama_status)
        self.model_manager.models_changed.connect(self.model_manager.refresh_installed)

        # 초기 감지
        self.spec_card.detect_async()
        self.ollama_section.refresh()

    # ------------------------------------------------------------------
    def _header(self) -> QWidget:
        w = QWidget()
        w.setObjectName("root")
        lay = QHBoxLayout(w)
        lay.setContentsMargins(20, 16, 20, 8)
        title = QLabel("💎  Gemma 로컬 설치 마법사")
        title.setStyleSheet("font-size:20px; font-weight:800;")
        sub = QLabel("버튼 몇 번으로 내 컴퓨터에 나만의 AI 를 설치하세요")
        sub.setObjectName("muted")
        box = QVBoxLayout()
        box.addWidget(title)
        box.addWidget(sub)
        lay.addLayout(box)
        lay.addStretch(1)
        ver = QLabel(f"v{__version__}")
        ver.setObjectName("badge")
        lay.addWidget(ver, alignment=Qt.AlignmentFlag.AlignTop)
        return w

    def _chat_card(self) -> Card:
        card = Card("4. AI 채팅 (앱 내장 · Docker 불필요)")
        card.add(muted("모델 설치가 끝나면 앱에 내장된 채팅으로 바로 로컬 AI 와 대화할 수 있어요."))
        self.open_chat_btn = QPushButton("채팅 열기")
        self.open_chat_btn.setObjectName("primary")
        self.open_chat_btn.clicked.connect(self.open_chat)
        card.add(self.open_chat_btn)
        return card

    # ------------------------------------------------------------------
    def _on_recommend(self, rec: Recommendation) -> None:
        self.model_manager.select_model(rec.model.tag)

    def _on_ollama_status(self, status: str) -> None:
        self.model_manager.set_ollama_available(status == "running")

    def open_chat(self) -> None:
        from auto_gemma.ui.chat.chat_window import ChatWindow
        if self._chat_window is None:
            default_model = self.model_manager.current_tag()
            self._chat_window = ChatWindow(default_model=default_model)
        self._chat_window.show()
        self._chat_window.raise_()
        self._chat_window.activateWindow()
