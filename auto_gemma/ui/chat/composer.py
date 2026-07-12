"""입력 영역 — 텍스트 입력 + 전송/중지/재생성 + 이미지 첨부."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class InputBox(QPlainTextEdit):
    submitted = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setPlaceholderText("Gemma 에게 메시지 보내기...  (Enter 전송 · Shift+Enter 줄바꿈)")
        self.setFixedHeight(90)

    def keyPressEvent(self, e: QKeyEvent) -> None:
        if e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and not (e.modifiers() & Qt.KeyboardModifier.ShiftModifier):
            self.submitted.emit()
            e.accept()
            return
        super().keyPressEvent(e)


class Composer(QWidget):
    send_requested = Signal(str)      # 텍스트
    stop_requested = Signal()
    regenerate_requested = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.images: list[str] = []

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        self.image_label = QLabel("")
        self.image_label.setObjectName("muted")
        self.image_label.hide()
        lay.addWidget(self.image_label)

        row = QHBoxLayout()
        self.input = InputBox()
        self.input.submitted.connect(self._on_submit)
        row.addWidget(self.input, 1)

        btn_col = QVBoxLayout()
        self.send_btn = QPushButton("전송")
        self.send_btn.setObjectName("success")
        self.stop_btn = QPushButton("중지")
        self.stop_btn.setEnabled(False)
        self.regen_btn = QPushButton("재생성")
        self.send_btn.clicked.connect(self._on_submit)
        self.stop_btn.clicked.connect(self.stop_requested)
        self.regen_btn.clicked.connect(self.regenerate_requested)
        for b in (self.send_btn, self.stop_btn, self.regen_btn):
            b.setFixedWidth(80)
            btn_col.addWidget(b)
        row.addLayout(btn_col)
        lay.addLayout(row)

    def _on_submit(self) -> None:
        text = self.input.toPlainText().strip()
        if not text and not self.images:
            return
        self.send_requested.emit(text)

    def clear_input(self) -> None:
        self.input.clear()

    def add_image(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, "이미지 선택", "", "이미지 (*.png *.jpg *.jpeg *.webp *.gif)"
        )
        if paths:
            self.images.extend(paths)
            self._refresh_images()

    def clear_images(self) -> None:
        self.images.clear()
        self._refresh_images()

    def _refresh_images(self) -> None:
        if self.images:
            names = ", ".join(p.rsplit("/", 1)[-1].rsplit("\\", 1)[-1] for p in self.images)
            self.image_label.setText(f"📎 첨부 이미지 {len(self.images)}개: {names}")
            self.image_label.show()
        else:
            self.image_label.hide()

    def set_generating(self, on: bool) -> None:
        self.send_btn.setEnabled(not on)
        self.regen_btn.setEnabled(not on)
        self.stop_btn.setEnabled(on)
        self.input.setEnabled(not on)
