"""AI 채팅 위젯 — 스트리밍 대화 + 대화 저장/불러오기/내보내기.

모델 선택은 상위 MainWindow 상단바에서 관리하고, 여기서는 model_getter()
콜백으로 현재 모델 태그를 받아 사용한다.
"""
from __future__ import annotations

from collections import deque
from datetime import datetime
from typing import Callable

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from auto_gemma.app.config import ChatOptions, data_dir
from auto_gemma.core.persistence.conversations import (
    Conversation,
    ConversationStore,
    Message,
)
from auto_gemma.ui.chat.composer import Composer
from auto_gemma.ui.chat.dialogs import AdvancedDialog
from auto_gemma.ui.chat.sidebar import Sidebar
from auto_gemma.ui.chat.transcript import TranscriptView
from auto_gemma.ui.widgets.common import general_pool
from auto_gemma.workers.base import CancellableWorker
from auto_gemma.workers.tasks import chat_task


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class ChatView(QWidget):
    def __init__(self, model_getter: Callable[[], str], parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("root")
        self._model_getter = model_getter

        self.conv_store = ConversationStore()
        self.options = ChatOptions()

        self.conv: Conversation | None = None
        self._chat_worker: CancellableWorker | None = None
        self._stream_bubble = None
        self._pending: deque = deque()
        self._flush_timer = QTimer(self)
        self._flush_timer.setInterval(40)
        self._flush_timer.timeout.connect(self._flush_tokens)

        # ---------------- 레이아웃
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        self.sidebar = Sidebar(self.conv_store)
        root.addWidget(self.sidebar)

        right = QVBoxLayout()
        right.addLayout(self._toolbar())
        self.transcript = TranscriptView()
        right.addWidget(self.transcript, 1)
        self.composer = Composer()
        right.addWidget(self.composer)
        self.save_label = QLabel(f"저장됨: {data_dir()}")
        self.save_label.setObjectName("muted")
        right.addWidget(self.save_label)
        root.addLayout(right, 1)

        # ---------------- 시그널
        self.sidebar.conversations.new_requested.connect(self.new_conversation)
        self.sidebar.conversations.selected.connect(self.load_conversation)
        self.sidebar.conversations.rename_requested.connect(self._rename_conv)
        self.sidebar.conversations.delete_requested.connect(self._delete_conv)

        self.composer.send_requested.connect(self.send_message)
        self.composer.stop_requested.connect(self.stop_generation)
        self.composer.regenerate_requested.connect(self.regenerate)

        self.new_conversation()

    # ------------------------------------------------------------------ 툴바
    def _toolbar(self):
        bar = QHBoxLayout()
        adv = QPushButton("고급")
        export = QPushButton("내보내기")
        adv.clicked.connect(self._open_advanced)
        export.clicked.connect(self._export)
        bar.addStretch(1)
        bar.addWidget(adv)
        bar.addWidget(export)
        return bar

    def current_model(self) -> str:
        return self._model_getter()

    # ------------------------------------------------------------------ 대화 관리
    def new_conversation(self) -> None:
        self.conv = self.conv_store.new(title="새 대화", model=self.current_model(), ts=_now())
        self.transcript.clear()
        self.sidebar.conversations.reload()
        self.sidebar.conversations.select_id(self.conv.id)

    def load_conversation(self, conv_id: str) -> None:
        conv = self.conv_store.load(conv_id)
        if not conv:
            return
        self.conv = conv
        self.transcript.clear()
        for m in conv.messages:
            if m.role in ("user", "assistant"):
                self.transcript.add_message(m.role, m.content)
        self.transcript.scroll_to_bottom()

    def _rename_conv(self, conv_id: str, title: str) -> None:
        self.conv_store.rename(conv_id, title)
        if self.conv and self.conv.id == conv_id:
            self.conv.title = title

    def _delete_conv(self, conv_id: str) -> None:
        self.conv_store.delete(conv_id)
        if self.conv and self.conv.id == conv_id:
            self.new_conversation()

    def _persist(self) -> None:
        if self.conv:
            self.conv.model = self.current_model()
            self.conv_store.save(self.conv, ts=_now())

    # ------------------------------------------------------------------ 전송
    def _build_messages(self, user_text: str) -> list[dict]:
        msgs: list[dict] = []
        if self.options.system_prompt.strip():
            msgs.append({"role": "system", "content": self.options.system_prompt})
        for m in self.conv.messages:
            if m.role in ("user", "assistant"):
                msgs.append({"role": m.role, "content": m.content})
        msgs.append({"role": "user", "content": user_text})
        return msgs

    def send_message(self, text: str) -> None:
        if self._chat_worker is not None:
            return
        messages = self._build_messages(text)

        self.transcript.add_message("user", text)
        self.conv.messages.append(Message(role="user", content=text))
        if self.conv.title in ("새 대화", "") and text.strip():
            self.conv.title = text.strip()[:30]
            self.sidebar.conversations.reload()
            self.sidebar.conversations.select_id(self.conv.id)

        self.composer.clear_input()
        self._start_stream(messages)

    def regenerate(self) -> None:
        if not self.conv or not self.conv.messages or self._chat_worker is not None:
            return
        if self.conv.messages[-1].role == "assistant":
            self.conv.messages.pop()
            self.transcript.remove_last_assistant()
        last_user = next((m for m in reversed(self.conv.messages) if m.role == "user"), None)
        if not last_user:
            return
        saved = self.conv.messages
        self.conv.messages = self.conv.messages[:-1]
        messages = self._build_messages(last_user.content)
        self.conv.messages = saved
        self._start_stream(messages)

    def _start_stream(self, messages: list[dict]) -> None:
        self._stream_bubble = self.transcript.add_message("assistant", "")
        self.composer.set_generating(True)
        self._pending.clear()
        self._flush_timer.start()

        worker = CancellableWorker(chat_task, self.current_model(), messages,
                                   self.options.to_ollama_options())
        worker.signals.token.connect(self._on_token)
        worker.signals.finished.connect(self._on_stream_done)
        worker.signals.cancelled.connect(self._on_stream_cancelled)
        worker.signals.error.connect(self._on_stream_error)
        self._chat_worker = worker
        general_pool().start(worker)

    def _on_token(self, delta: str) -> None:
        self._pending.append(delta)

    def _flush_tokens(self) -> None:
        if not self._pending or self._stream_bubble is None:
            return
        chunk = "".join(self._pending)
        self._pending.clear()
        self._stream_bubble.append(chunk)
        self.transcript.scroll_to_bottom()

    def _finish_common(self) -> None:
        self._flush_tokens()
        self._flush_timer.stop()
        self.composer.set_generating(False)
        self._chat_worker = None

    def _on_stream_done(self, full_text: str) -> None:
        self._finish_common()
        if self._stream_bubble is not None:
            self.conv.messages.append(Message(role="assistant", content=self._stream_bubble.text()))
            self._persist()
        self._stream_bubble = None

    def _on_stream_cancelled(self) -> None:
        self._finish_common()
        if self._stream_bubble is not None:
            txt = self._stream_bubble.text()
            if txt:
                self.conv.messages.append(Message(role="assistant", content=txt + "\n\n[중지됨]"))
                self._persist()
        self._stream_bubble = None

    def _on_stream_error(self, err: str) -> None:
        self._finish_common()
        if self._stream_bubble is not None:
            self._stream_bubble.set_text(f"⚠️ 오류: {err.splitlines()[-1] if err else ''}")
        self._stream_bubble = None

    def stop_generation(self) -> None:
        if self._chat_worker is not None:
            self._chat_worker.cancel()

    # ------------------------------------------------------------------ 다이얼로그
    def _open_advanced(self) -> None:
        dlg = AdvancedDialog(self.options, self)
        if dlg.exec():
            self.options = dlg.result_options()

    def _export(self) -> None:
        if not self.conv or not self.conv.messages:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "대화 내보내기", f"{self.conv.title}.md", "Markdown (*.md);;텍스트 (*.txt)"
        )
        if not path:
            return
        lines = [f"# {self.conv.title}\n"]
        for m in self.conv.messages:
            who = "나" if m.role == "user" else "Gemma"
            lines.append(f"**{who}:**\n\n{m.content}\n")
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            QMessageBox.information(self, "완료", f"내보냈습니다:\n{path}")
        except OSError as e:
            QMessageBox.warning(self, "오류", str(e))

    # ------------------------------------------------------------------ 종료 처리
    def shutdown(self) -> None:
        self.stop_generation()
        self._persist()
