"""좌측 사이드바 — 채팅 목록 탭 + 지식 도서관(RAG) 탭."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from auto_gemma.core.persistence.conversations import Conversation, ConversationStore
from auto_gemma.core.rag.loaders import SUPPORTED
from auto_gemma.core.rag.store import VectorStore


class ConversationList(QWidget):
    new_requested = Signal()
    selected = Signal(str)          # conv_id
    rename_requested = Signal(str, str)
    delete_requested = Signal(str)

    def __init__(self, store: ConversationStore, parent: QWidget | None = None):
        super().__init__(parent)
        self.store = store
        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 6, 6, 6)

        new_btn = QPushButton("+ 새 대화")
        new_btn.setObjectName("success")
        new_btn.clicked.connect(self.new_requested)
        lay.addWidget(new_btn)

        self.search = QLineEdit()
        self.search.setPlaceholderText("대화 검색...")
        self.search.textChanged.connect(self.reload)
        lay.addWidget(self.search)

        self.list = QListWidget()
        self.list.itemClicked.connect(self._on_click)
        lay.addWidget(self.list, 1)

        btns = QHBoxLayout()
        self.rename_btn = QPushButton("이름변경")
        self.delete_btn = QPushButton("삭제")
        self.delete_btn.setObjectName("danger")
        self.rename_btn.clicked.connect(self._rename)
        self.delete_btn.clicked.connect(self._delete)
        btns.addWidget(self.rename_btn)
        btns.addWidget(self.delete_btn)
        lay.addLayout(btns)

        self.reload()

    def reload(self) -> None:
        self.list.clear()
        convs = self.store.search(self.search.text())
        for c in convs:
            it = QListWidgetItem(c.title or "새 대화")
            it.setData(Qt.ItemDataRole.UserRole, c.id)
            self.list.addItem(it)

    def _current_id(self) -> str | None:
        it = self.list.currentItem()
        return it.data(Qt.ItemDataRole.UserRole) if it else None

    def select_id(self, conv_id: str) -> None:
        for i in range(self.list.count()):
            if self.list.item(i).data(Qt.ItemDataRole.UserRole) == conv_id:
                self.list.setCurrentRow(i)
                return

    def _on_click(self, item: QListWidgetItem) -> None:
        self.selected.emit(item.data(Qt.ItemDataRole.UserRole))

    def _rename(self) -> None:
        cid = self._current_id()
        if not cid:
            return
        text, ok = QInputDialog.getText(self, "이름변경", "새 제목:")
        if ok and text.strip():
            self.rename_requested.emit(cid, text.strip())
            self.reload()

    def _delete(self) -> None:
        cid = self._current_id()
        if cid:
            self.delete_requested.emit(cid)
            self.reload()


class KnowledgeLibrary(QWidget):
    """지식 도서관(RAG): 문서 추가/삭제 목록."""

    ingest_requested = Signal(list)  # 파일 경로 리스트
    docs_changed = Signal()

    def __init__(self, store: VectorStore, parent: QWidget | None = None):
        super().__init__(parent)
        self.store = store
        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 6, 6, 6)

        lay.addWidget(QLabel("업로드한 문서로 답변 근거를 만듭니다 (RAG)."))
        btn_row = QHBoxLayout()
        add_btn = QPushButton("+ 파일 추가")
        add_btn.setObjectName("success")
        add_btn.clicked.connect(self._add)
        folder_btn = QPushButton("+ 폴더 추가")
        folder_btn.clicked.connect(self._add_folder)
        btn_row.addWidget(add_btn)
        btn_row.addWidget(folder_btn)
        lay.addLayout(btn_row)

        self.progress = QProgressBar()
        self.progress.hide()
        lay.addWidget(self.progress)
        self.status = QLabel("")
        self.status.setObjectName("muted")
        self.status.setWordWrap(True)
        lay.addWidget(self.status)

        self.list = QListWidget()
        lay.addWidget(self.list, 1)

        del_btn = QPushButton("선택 문서 삭제")
        del_btn.setObjectName("danger")
        del_btn.clicked.connect(self._delete)
        lay.addWidget(del_btn)

        self.reload()

    def reload(self) -> None:
        self.list.clear()
        for d in self.store.documents():
            it = QListWidgetItem(f"{d.source}  ({d.chunks}조각)")
            it.setData(Qt.ItemDataRole.UserRole, d.doc_id)
            self.list.addItem(it)
        self.docs_changed.emit()

    def _add(self) -> None:
        exts = " ".join(f"*{e}" for e in sorted(SUPPORTED))
        paths, _ = QFileDialog.getOpenFileNames(self, "문서 선택 (여러 개 가능)", "", f"문서 ({exts})")
        if paths:
            self.ingest_requested.emit(paths)

    def _add_folder(self) -> None:
        from pathlib import Path
        d = QFileDialog.getExistingDirectory(self, "폴더 선택 (하위 문서 모두 추가)")
        if not d:
            return
        files = [
            str(p) for p in sorted(Path(d).rglob("*"))
            if p.is_file() and p.suffix.lower() in SUPPORTED
        ]
        if files:
            self.ingest_requested.emit(files)
        else:
            self.set_busy(False, "폴더에서 지원 문서를 찾지 못했습니다.")

    def _delete(self) -> None:
        it = self.list.currentItem()
        if it:
            self.store.delete_document(it.data(Qt.ItemDataRole.UserRole))
            self.reload()

    def set_busy(self, on: bool, msg: str = "") -> None:
        if on:
            self.progress.show()
            self.progress.setRange(0, 0)
        else:
            self.progress.hide()
        self.status.setText(msg)


class Sidebar(QTabWidget):
    def __init__(self, conv_store: ConversationStore, vec_store: VectorStore,
                 parent: QWidget | None = None):
        super().__init__(parent)
        self.conversations = ConversationList(conv_store)
        self.library = KnowledgeLibrary(vec_store)
        self.addTab(self.conversations, "채팅")
        self.addTab(self.library, "지식 도서관 (RAG)")
        self.setMaximumWidth(300)
