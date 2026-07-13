"""AI 채팅 메인 창 — 전체 기능 오케스트레이션."""
from __future__ import annotations

from collections import deque
from datetime import datetime

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from auto_gemma.app.config import (
    EMBED_MODEL,
    ChatOptions,
    data_dir,
    rag_db_path,
    spec_for,
)
from auto_gemma.core.ollama_client import OllamaClient, encode_image
from auto_gemma.core.persistence.bots import BotStore
from auto_gemma.core.persistence.conversations import (
    Conversation,
    ConversationStore,
    Message,
)
from auto_gemma.core.rag.store import VectorStore, build_context
from auto_gemma.ui.chat.composer import Composer
from auto_gemma.ui.chat.dialogs import (
    AdvancedDialog,
    BotManagerDialog,
    PromptDialog,
)
from auto_gemma.ui.chat.sidebar import Sidebar
from auto_gemma.ui.chat.transcript import TranscriptView
from auto_gemma.ui.summary.summary_view import SummaryView
from auto_gemma.ui.widgets.common import download_pool, general_pool
from auto_gemma.workers.base import CancellableWorker
from auto_gemma.workers.tasks import chat_task, embed_query_task, ingest_documents_batch_task


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class ChatWindow(QMainWindow):
    def __init__(self, default_model: str = "gemma3:4b"):
        super().__init__()
        self.setWindowTitle("AI 채팅")
        self.resize(1080, 720)

        self.client = OllamaClient()
        self.conv_store = ConversationStore()
        self.bot_store = BotStore()
        self.vec_store = VectorStore(rag_db_path())
        self.options = ChatOptions()

        self.conv: Conversation | None = None
        self._chat_worker: CancellableWorker | None = None
        self._stream_bubble = None
        self._pending = deque()
        self._flush_timer = QTimer(self)
        self._flush_timer.setInterval(40)
        self._flush_timer.timeout.connect(self._flush_tokens)

        # ---------------- 레이아웃 (탭: 채팅 / PDF 요약)
        chat_tab = QWidget()
        chat_tab.setObjectName("root")
        root = QHBoxLayout(chat_tab)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        self.sidebar = Sidebar(self.conv_store, self.vec_store)
        root.addWidget(self.sidebar)

        right = QVBoxLayout()
        right.addLayout(self._toolbar(default_model))
        right.addLayout(self._options_bar())
        self.transcript = TranscriptView()
        right.addWidget(self.transcript, 1)
        self.composer = Composer()
        right.addWidget(self.composer)
        self.save_label = QLabel(f"저장됨: {data_dir()}")
        self.save_label.setObjectName("muted")
        right.addWidget(self.save_label)
        root.addLayout(right, 1)

        # PDF 요약 탭 (모델은 채팅 탭의 모델 선택을 공유)
        self.summary_view = SummaryView(self.current_model)

        self.tabs = QTabWidget()
        self.tabs.addTab(chat_tab, "채팅")
        self.tabs.addTab(self.summary_view, "PDF 요약")
        self.setCentralWidget(self.tabs)

        # ---------------- 시그널
        self.sidebar.conversations.new_requested.connect(self.new_conversation)
        self.sidebar.conversations.selected.connect(self.load_conversation)
        self.sidebar.conversations.rename_requested.connect(self._rename_conv)
        self.sidebar.conversations.delete_requested.connect(self._delete_conv)
        self.sidebar.library.ingest_requested.connect(self._ingest_docs)
        self.sidebar.library.docs_changed.connect(self._update_rag_label)

        self.composer.send_requested.connect(self.send_message)
        self.composer.stop_requested.connect(self.stop_generation)
        self.composer.regenerate_requested.connect(self.regenerate)

        self.refresh_models()
        self._update_rag_label()
        self.new_conversation()

    # ------------------------------------------------------------------ 툴바
    def _toolbar(self, default_model: str):
        bar = QHBoxLayout()
        self.model_combo = QComboBox()
        self.model_combo.currentTextChanged.connect(self._on_model_changed)
        self._default_model = default_model

        self.bot_combo = QComboBox()
        self._reload_bots()

        bot_mgr = QPushButton("봇 관리")
        adv = QPushButton("고급")
        prompt = QPushButton("프롬프트")
        export = QPushButton("내보내기")
        bot_mgr.clicked.connect(self._open_bot_manager)
        adv.clicked.connect(self._open_advanced)
        prompt.clicked.connect(self._open_prompt)
        export.clicked.connect(self._export)

        bar.addWidget(QLabel("모델:"))
        bar.addWidget(self.model_combo)
        bar.addWidget(QLabel("봇:"))
        bar.addWidget(self.bot_combo)
        bar.addWidget(bot_mgr)
        bar.addStretch(1)
        bar.addWidget(adv)
        bar.addWidget(prompt)
        bar.addWidget(export)
        return bar

    def _options_bar(self):
        bar = QHBoxLayout()
        self.image_check = QCheckBox("이미지")
        self.image_check.toggled.connect(self._on_image_toggle)
        self.rag_check = QCheckBox("지식 도서관 사용")
        self.rag_label = QLabel("")
        self.rag_label.setObjectName("muted")
        bar.addWidget(self.image_check)
        bar.addWidget(self.rag_check)
        bar.addWidget(self.rag_label)
        bar.addStretch(1)
        return bar

    # ------------------------------------------------------------------ 모델/봇
    def refresh_models(self) -> None:
        self.model_combo.blockSignals(True)
        self.model_combo.clear()
        installed = []
        if self.client.is_running():
            try:
                installed = [m.name for m in self.client.list_models()]
            except Exception:  # noqa: BLE001
                installed = []
        # 임베딩 모델은 채팅 목록에서 제외
        chat_models = [m for m in installed if EMBED_MODEL not in m]
        if not chat_models:
            self.model_combo.addItem(self._default_model)
        else:
            self.model_combo.addItems(chat_models)
            if self._default_model in chat_models:
                self.model_combo.setCurrentText(self._default_model)
        self.model_combo.blockSignals(False)
        self._on_model_changed(self.model_combo.currentText())

    def current_model(self) -> str:
        return self.model_combo.currentText()

    def _on_model_changed(self, tag: str) -> None:
        spec = spec_for(tag)
        vision = spec.vision if spec else True
        self.image_check.setEnabled(vision)
        if not vision:
            self.image_check.setChecked(False)
            self.image_check.setToolTip("이 모델은 이미지를 지원하지 않습니다 (텍스트 전용).")
        else:
            self.image_check.setToolTip("")

    def _reload_bots(self) -> None:
        self.bot_combo.clear()
        self.bot_combo.addItems([b.name for b in self.bot_store.list_all()])

    def _on_image_toggle(self, on: bool) -> None:
        if on:
            self.composer.add_image()
            if not self.composer.images:
                self.image_check.setChecked(False)
        else:
            self.composer.clear_images()

    def _update_rag_label(self) -> None:
        n = self.vec_store.chunk_count()
        docs = len(self.vec_store.documents())
        self.rag_label.setText(f"지식 도서관 사용 중 · 문서 {docs}개" if docs else "문서 없음")

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
        if conv.model:
            idx = self.model_combo.findText(conv.model)
            if idx >= 0:
                self.model_combo.setCurrentIndex(idx)
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
            self.conv.bot = self.bot_combo.currentText()
            self.conv_store.save(self.conv, ts=_now())

    # ------------------------------------------------------------------ 전송
    def _build_messages(self, user_text: str, images: list[str]) -> list[dict]:
        msgs: list[dict] = []
        system_parts = []
        bot = self.bot_store.get(self.bot_combo.currentText())
        if bot.system:
            system_parts.append(bot.system)

        # RAG 컨텍스트 (동기 임베딩 — 질의 1건이라 빠름)
        if self.rag_check.isChecked() and self.vec_store.chunk_count() > 0:
            try:
                qvec = self.client.embed(EMBED_MODEL, [user_text])[0]
                hits = self.vec_store.search(qvec, k=5)
                ctx = build_context(hits)
                if ctx:
                    system_parts.append(ctx)
            except Exception:  # noqa: BLE001
                pass

        if system_parts:
            msgs.append({"role": "system", "content": "\n\n".join(system_parts)})

        # 과거 히스토리
        for m in self.conv.messages:
            if m.role in ("user", "assistant"):
                msgs.append({"role": m.role, "content": m.content})

        entry = {"role": "user", "content": user_text}
        if images:
            entry["images"] = [encode_image(p) for p in images]
        msgs.append(entry)
        return msgs

    def send_message(self, text: str) -> None:
        if self._chat_worker is not None:
            return
        images = list(self.composer.images)
        messages = self._build_messages(text, images)

        # 화면 + 저장
        self.transcript.add_message("user", text + (f"\n📎 이미지 {len(images)}개" if images else ""))
        self.conv.messages.append(Message(role="user", content=text, images=images))
        if self.conv.title in ("새 대화", "") and text.strip():
            self.conv.title = text.strip()[:30]
            self.sidebar.conversations.reload()
            self.sidebar.conversations.select_id(self.conv.id)

        self.composer.clear_input()
        self.composer.clear_images()
        self.image_check.setChecked(False)

        self._start_stream(messages)

    def regenerate(self) -> None:
        if not self.conv or not self.conv.messages:
            return
        # 마지막 assistant 메시지 제거 후 마지막 user 로 재요청
        if self.conv.messages and self.conv.messages[-1].role == "assistant":
            self.conv.messages.pop()
            self.transcript.remove_last_assistant()
        last_user = next((m for m in reversed(self.conv.messages) if m.role == "user"), None)
        if not last_user:
            return
        # 히스토리에서 마지막 user 를 잠시 빼고 재구성
        history = self.conv.messages[:-1] if self.conv.messages[-1].role == "user" else self.conv.messages
        saved = self.conv.messages
        self.conv.messages = history
        messages = self._build_messages(last_user.content, last_user.images)
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

    # ------------------------------------------------------------------ RAG
    def _ingest_docs(self, paths: list) -> None:
        if not paths:
            return
        lib = self.sidebar.library
        lib.set_busy(True, f"{len(paths)}개 문서 처리 준비 중...")
        worker = CancellableWorker(
            ingest_documents_batch_task, self.vec_store, list(paths), EMBED_MODEL
        )
        worker.signals.message.connect(lib.status.setText)
        worker.signals.progress.connect(self._on_ingest_progress)
        worker.signals.finished.connect(self._on_ingest_done)
        worker.signals.error.connect(
            lambda e: lib.set_busy(False, f"오류: {e.splitlines()[-1] if e else ''}")
        )
        download_pool().start(worker)

    def _on_ingest_progress(self, prog: dict) -> None:
        total = prog.get("total")
        completed = prog.get("completed")
        if total:
            self.sidebar.library.progress.setRange(0, total)
            self.sidebar.library.progress.setValue(completed or 0)

    def _on_ingest_done(self, result) -> None:
        lib = self.sidebar.library
        if isinstance(result, dict):
            msg = f"✅ 완료: {result.get('ok', 0)}개 추가"
            if result.get("failed"):
                msg += f" · 실패 {result['failed']}개"
            msg += f" · 총 {result.get('chunks', 0)}조각"
        else:
            msg = "완료"
        lib.set_busy(False, msg)
        lib.reload()
        self.rag_check.setChecked(True)

    # ------------------------------------------------------------------ 다이얼로그
    def _open_bot_manager(self) -> None:
        dlg = BotManagerDialog(self.bot_store, self)
        dlg.exec()
        self._reload_bots()

    def _open_advanced(self) -> None:
        dlg = AdvancedDialog(self.options, self)
        if dlg.exec():
            self.options = dlg.result_options()

    def _open_prompt(self) -> None:
        dlg = PromptDialog(self)
        if dlg.exec() and dlg.chosen:
            cur = self.composer.input.toPlainText()
            self.composer.input.setPlainText(dlg.chosen + cur)
            self.composer.input.setFocus()

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

    def closeEvent(self, event) -> None:
        self.stop_generation()
        self.summary_view.shutdown()
        self._persist()
        super().closeEvent(event)
