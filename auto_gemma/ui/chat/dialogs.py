"""봇 관리 · 고급 설정 · 프롬프트 템플릿 다이얼로그."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from auto_gemma.app.config import ChatOptions
from auto_gemma.core.persistence.bots import Bot, BotStore


class BotManagerDialog(QDialog):
    def __init__(self, store: BotStore, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("봇 관리")
        self.resize(560, 440)
        self.store = store

        lay = QHBoxLayout(self)
        self.list = QListWidget()
        self.list.currentTextChanged.connect(self._load_bot)
        lay.addWidget(self.list, 1)

        right = QVBoxLayout()
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("봇 이름")
        self.system_edit = QPlainTextEdit()
        self.system_edit.setPlaceholderText("시스템 프롬프트 (이 봇의 성격/역할)")
        right.addWidget(QLabel("이름"))
        right.addWidget(self.name_edit)
        right.addWidget(QLabel("시스템 프롬프트"))
        right.addWidget(self.system_edit, 1)

        btns = QHBoxLayout()
        save_btn = QPushButton("저장")
        save_btn.setObjectName("primary")
        new_btn = QPushButton("새 봇")
        del_btn = QPushButton("삭제")
        del_btn.setObjectName("danger")
        save_btn.clicked.connect(self._save)
        new_btn.clicked.connect(self._new)
        del_btn.clicked.connect(self._delete)
        for b in (new_btn, save_btn, del_btn):
            btns.addWidget(b)
        right.addLayout(btns)

        reset_btn = QPushButton("기본 봇 복원")
        reset_btn.clicked.connect(self._reset)
        right.addWidget(reset_btn)
        lay.addLayout(right, 2)

        self._reload()

    def _reload(self) -> None:
        self.list.clear()
        for b in self.store.list_all():
            self.list.addItem(b.name)
        if self.list.count():
            self.list.setCurrentRow(0)

    def _load_bot(self, name: str) -> None:
        if not name:
            return
        b = self.store.get(name)
        self.name_edit.setText(b.name)
        self.system_edit.setPlainText(b.system)

    def _new(self) -> None:
        self.name_edit.setText("새 봇")
        self.system_edit.clear()

    def _save(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            return
        self.store.save(Bot(name=name, system=self.system_edit.toPlainText()))
        self._reload()

    def _delete(self) -> None:
        name = self.name_edit.text().strip()
        if name:
            self.store.delete(name)
            self._reload()

    def _reset(self) -> None:
        ok = QMessageBox.question(
            self, "기본 봇 복원",
            "기본 봇 세트(기본 + SQLD 6종)로 되돌립니다.\n직접 추가/수정한 봇은 사라집니다. 계속할까요?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ok == QMessageBox.StandardButton.Yes:
            self.store.reset_defaults()
            self._reload()


class AdvancedDialog(QDialog):
    def __init__(self, options: ChatOptions, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("고급 설정")
        self.options = options
        form = QFormLayout(self)

        self.temp = QDoubleSpinBox()
        self.temp.setRange(0.0, 2.0)
        self.temp.setSingleStep(0.1)
        self.temp.setValue(options.temperature)
        self.top_p = QDoubleSpinBox()
        self.top_p.setRange(0.0, 1.0)
        self.top_p.setSingleStep(0.05)
        self.top_p.setValue(options.top_p)
        self.ctx = QSpinBox()
        self.ctx.setRange(512, 131072)
        self.ctx.setSingleStep(512)
        self.ctx.setValue(options.num_ctx)

        form.addRow("Temperature (창의성)", self.temp)
        form.addRow("Top-p", self.top_p)
        form.addRow("컨텍스트 길이 (num_ctx)", self.ctx)

        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        form.addRow(bb)

    def result_options(self) -> ChatOptions:
        self.options.temperature = self.temp.value()
        self.options.top_p = self.top_p.value()
        self.options.num_ctx = self.ctx.value()
        return self.options


PROMPT_TEMPLATES = {
    "요약 요청": "다음 내용을 핵심 위주로 3~5줄로 요약해줘:\n\n",
    "문제집 만들기": "다음 내용으로 학습용 문제 5개와 각 문제의 상세 해설을 만들어줘:\n\n",
    "쉽게 설명": "다음 개념을 중학생도 이해할 수 있게 쉽게 설명해줘:\n\n",
    "번역 (한→영)": "다음 한국어 문장을 자연스러운 영어로 번역해줘:\n\n",
    "코드 리뷰": "다음 코드를 리뷰하고 개선점을 알려줘:\n\n",
}


class PromptDialog(QDialog):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("프롬프트 템플릿")
        self.resize(420, 320)
        self.chosen: str | None = None
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("템플릿을 선택하면 입력창에 삽입됩니다."))
        self.list = QListWidget()
        self.list.addItems(list(PROMPT_TEMPLATES.keys()))
        self.list.itemDoubleClicked.connect(lambda *_: self._pick())
        lay.addWidget(self.list, 1)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self._pick)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def _pick(self) -> None:
        item = self.list.currentItem()
        if item:
            self.chosen = PROMPT_TEMPLATES[item.text()]
            self.accept()
