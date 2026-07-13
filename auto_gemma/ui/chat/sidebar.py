"""좌측 사이드바 — 채팅 목록."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from auto_gemma.core.persistence.conversations import ConversationStore


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


class Sidebar(QWidget):
    """대화 목록만 담는 사이드바. chat_window 는 self.conversations 로 접근."""

    def __init__(self, conv_store: ConversationStore, parent: QWidget | None = None):
        super().__init__(parent)
        self.conversations = ConversationList(conv_store)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.conversations)
        self.setMaximumWidth(280)
