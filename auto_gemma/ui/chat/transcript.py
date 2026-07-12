"""채팅 대화 표시 영역 — 메시지 버블 + 스트리밍 + 복사."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from auto_gemma.app import theme


class MessageBubble(QFrame):
    def __init__(self, role: str, text: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self.role = role
        self._raw = text
        is_user = role == "user"
        bg = theme.ACCENT if is_user else theme.CARD
        self.setStyleSheet(
            f"QFrame {{ background:{bg}; border-radius:12px; }}"
        )
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(4)

        name = QLabel("나" if is_user else "Gemma")
        name.setStyleSheet(f"font-weight:700; color:{'white' if is_user else theme.ACCENT};")
        lay.addWidget(name)

        self.body = QLabel()
        self.body.setWordWrap(True)
        self.body.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.body.setStyleSheet(f"color:{'white' if is_user else theme.TEXT}; background:transparent;")
        self.body.setTextFormat(Qt.TextFormat.MarkdownText)
        self.body.setText(text)
        lay.addWidget(self.body)

        if not is_user:
            self.copy_btn = QPushButton("복사")
            self.copy_btn.setFixedWidth(56)
            self.copy_btn.setStyleSheet("padding:2px 6px; font-size:11px;")
            self.copy_btn.clicked.connect(self._copy)
            bar = QHBoxLayout()
            bar.addStretch(1)
            bar.addWidget(self.copy_btn)
            lay.addLayout(bar)

    def set_text(self, text: str) -> None:
        self._raw = text
        self.body.setText(text)

    def append(self, delta: str) -> None:
        self._raw += delta
        self.body.setText(self._raw)

    def text(self) -> str:
        return self._raw

    def _copy(self) -> None:
        QApplication.clipboard().setText(self._raw)
        self.copy_btn.setText("복사됨!")


class TranscriptView(QScrollArea):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self._container = QWidget()
        self._container.setObjectName("root")
        self._lay = QVBoxLayout(self._container)
        self._lay.setContentsMargins(16, 16, 16, 16)
        self._lay.setSpacing(12)
        self._lay.addStretch(1)
        self.setWidget(self._container)
        self._bubbles: list[MessageBubble] = []

    def clear(self) -> None:
        for b in self._bubbles:
            b.setParent(None)
            b.deleteLater()
        self._bubbles.clear()

    def add_message(self, role: str, text: str = "") -> MessageBubble:
        bubble = MessageBubble(role, text)
        wrap = QHBoxLayout()
        if role == "user":
            wrap.addStretch(1)
            wrap.addWidget(bubble, 4)
        else:
            wrap.addWidget(bubble, 4)
            wrap.addStretch(1)
        # 스트레치 앞에 삽입
        self._lay.insertLayout(self._lay.count() - 1, wrap)
        self._bubbles.append(bubble)
        self._scroll_to_bottom()
        return bubble

    def last_assistant(self) -> MessageBubble | None:
        for b in reversed(self._bubbles):
            if b.role == "assistant":
                return b
        return None

    def remove_last_assistant(self) -> None:
        b = self.last_assistant()
        if b:
            self._bubbles.remove(b)
            parent_layout = b.parent()
            b.setParent(None)
            b.deleteLater()

    def _scroll_to_bottom(self) -> None:
        bar = self.verticalScrollBar()
        bar.setValue(bar.maximum())

    def scroll_to_bottom(self) -> None:
        self._scroll_to_bottom()
