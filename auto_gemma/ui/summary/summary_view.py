"""PDF 요약 위젯 — 텍스트 복사 가능한 PDF 를 원문의 10% / 5% 분량으로 요약.

모델 선택은 상위 MainWindow 상단바에서 받아온다(model_getter).
"""
from __future__ import annotations

import os
from collections import deque
from typing import Callable

from PySide6.QtCore import QTimer
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from auto_gemma.app.config import ChatOptions
from auto_gemma.core.summarizer import RATIOS
from auto_gemma.ui.widgets.common import general_pool
from auto_gemma.workers.base import CancellableWorker
from auto_gemma.workers.tasks import summarize_task

_FILE_FILTER = (
    "문서 (*.pdf *.docx *.hwpx *.txt *.md);;PDF (*.pdf);;Word (*.docx);;"
    "한글 (*.hwpx);;텍스트 (*.txt *.md)"
)


class SummaryView(QWidget):
    def __init__(self, model_getter: Callable[[], str], parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("root")
        self._model_getter = model_getter

        self._path: str | None = None
        self._worker: CancellableWorker | None = None
        self._pending: deque = deque()
        self._flush_timer = QTimer(self)
        self._flush_timer.setInterval(40)
        self._flush_timer.timeout.connect(self._flush_tokens)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # --- 파일 선택 줄
        file_row = QHBoxLayout()
        self.pick_btn = QPushButton("문서 선택")
        self.pick_btn.clicked.connect(self._pick_file)
        self.file_label = QLabel("선택된 파일 없음")
        self.file_label.setObjectName("muted")
        file_row.addWidget(self.pick_btn)
        file_row.addWidget(self.file_label, 1)
        root.addLayout(file_row)

        # --- 비율 + 실행 줄
        ctrl = QHBoxLayout()
        ctrl.addWidget(QLabel("요약 분량:"))
        self.ratio_group = QButtonGroup(self)
        self.r10 = QRadioButton("10%")
        self.r5 = QRadioButton("5%")
        self.r10.setChecked(True)
        self.ratio_group.addButton(self.r10)
        self.ratio_group.addButton(self.r5)
        self.r10.toggled.connect(self._on_ratio_changed)
        self.r5.toggled.connect(self._on_ratio_changed)
        ctrl.addWidget(self.r10)
        ctrl.addWidget(self.r5)
        ctrl.addStretch(1)
        self.run_btn = QPushButton("요약 시작")
        self.run_btn.setObjectName("success")
        self.run_btn.setEnabled(False)   # 문서를 선택해야 활성화
        self.run_btn.clicked.connect(self._start)
        self.stop_btn = QPushButton("중지")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop)
        ctrl.addWidget(self.run_btn)
        ctrl.addWidget(self.stop_btn)
        root.addLayout(ctrl)

        # --- 진행률 + 상태
        self.progress = QProgressBar()
        self.progress.hide()
        root.addWidget(self.progress)
        self.status = QLabel("텍스트 복사가 가능한 PDF·Word(docx)·txt·md 를 선택하고 요약 분량을 고른 뒤 [요약 시작]을 누르세요.")
        self.status.setObjectName("muted")
        self.status.setWordWrap(True)
        root.addWidget(self.status)

        # --- 결과
        self.result = QTextEdit()
        self.result.setReadOnly(True)
        self.result.setPlaceholderText("요약 결과가 여기에 표시됩니다.")
        root.addWidget(self.result, 1)

        out_row = QHBoxLayout()
        out_row.addStretch(1)
        self.docx_btn = QPushButton("DOCX")
        self.copy_btn = QPushButton("복사")
        self.save_btn = QPushButton("저장")
        self.docx_btn.clicked.connect(self._save_docx)
        self.copy_btn.clicked.connect(self._copy)
        self.save_btn.clicked.connect(self._save)
        self._out_buttons = [self.docx_btn, self.copy_btn, self.save_btn]
        for b in self._out_buttons:
            b.setEnabled(False)
            out_row.addWidget(b)
        root.addLayout(out_row)

    # ------------------------------------------------------------------ 파일
    def _pick_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "요약할 문서 선택", "", _FILE_FILTER)
        if path:
            self._path = path
            self.file_label.setText(os.path.basename(path))
            # 새 문서 선택 = 새 요약. 이전 결과는 정리하고 [요약 시작]을 다시 활성화.
            self.result.clear()
            self._enable_outputs(False)
            self.run_btn.setEnabled(True)
            self.status.setText("선택됨. 요약 분량을 고른 뒤 [요약 시작]을 누르세요.")

    def _ratio(self) -> float:
        return RATIOS["10%"] if self.r10.isChecked() else RATIOS["5%"]

    def _on_ratio_changed(self, *_) -> None:
        # 완료 후 분량(10%/5%)을 바꾸면 '새 요약'이 명확하므로 [요약 시작]을 다시 활성화
        if self._worker is None and self._path:
            self.run_btn.setEnabled(True)

    # ------------------------------------------------------------------ 실행/중지
    def _start(self) -> None:
        if self._worker is not None:
            return
        if not self._path:
            QMessageBox.information(self, "안내", "먼저 요약할 문서(PDF·Word·txt·md)를 선택하세요.")
            return

        self.result.clear()
        self._pending.clear()
        self._flush_timer.start()
        self._set_running(True)
        self.progress.show()
        self.progress.setRange(0, 0)  # 준비 단계: 불확정
        self.status.setText("문서에서 텍스트 추출 중...")

        opts = ChatOptions(temperature=0.3).to_ollama_options()
        worker = CancellableWorker(
            summarize_task, self._path, self._ratio(), self._model_getter(), opts
        )
        worker.signals.message.connect(self.status.setText)
        worker.signals.progress.connect(self._on_progress)
        worker.signals.token.connect(self._on_token)
        worker.signals.finished.connect(self._on_done)
        worker.signals.cancelled.connect(self._on_cancelled)
        worker.signals.error.connect(self._on_error)
        self._worker = worker
        general_pool().start(worker)

    def _stop(self) -> None:
        if self._worker is not None:
            self._worker.cancel()
            self.status.setText("중지하는 중...")

    def _set_running(self, on: bool) -> None:
        # run_btn 은 여기서 다시 켜지 않는다(완료 후 오해 방지). 재활성화는
        # 문서 재선택 / 분량 변경 / 취소·오류 시에만 한다.
        self.pick_btn.setEnabled(not on)
        self.r10.setEnabled(not on)
        self.r5.setEnabled(not on)
        self.stop_btn.setEnabled(on)
        if on:
            self.run_btn.setEnabled(False)
            self._enable_outputs(False)

    def _enable_outputs(self, on: bool) -> None:
        for b in self._out_buttons:
            b.setEnabled(on)

    # ------------------------------------------------------------------ 스트리밍
    def _on_progress(self, prog: dict) -> None:
        total = prog.get("total")
        completed = prog.get("completed")
        if total:
            self.progress.setRange(0, total)
            self.progress.setValue(completed or 0)

    def _on_token(self, delta: str) -> None:
        self._pending.append(delta)

    def _flush_tokens(self) -> None:
        if not self._pending:
            return
        chunk = "".join(self._pending)
        self._pending.clear()
        cur = self.result.textCursor()
        cur.movePosition(QTextCursor.MoveOperation.End)
        cur.insertText(chunk)
        self.result.setTextCursor(cur)
        self.result.ensureCursorVisible()

    def _finish_common(self) -> None:
        self._flush_tokens()
        self._flush_timer.stop()
        self.progress.hide()
        self._set_running(False)
        self._worker = None

    def _on_done(self, result) -> None:
        self._finish_common()
        if not isinstance(result, dict):
            return
        summary = result.get("summary", "")
        self.result.setPlainText(summary)  # 스트리밍 잔여를 정리된 최종본으로 대체
        src = result.get("source_chars", 0)
        out = len(summary)
        pct = (out / src * 100) if src else 0
        # 완료 시 [요약 시작]은 비활성 유지(다시 누르면 처음부터 재요약이라 오해 소지).
        # 다시 요약하려면 문서를 다시 선택하거나 분량을 바꾸면 활성화된다.
        self.status.setText(
            f"완료 · 원문 {src:,}자 → 요약 {out:,}자 ({pct:.1f}%)  "
            "· 다시 요약하려면 문서를 다시 선택하거나 분량(10%/5%)을 바꾸세요."
        )
        self._enable_outputs(bool(summary))

    def _on_cancelled(self) -> None:
        self._finish_common()
        self.status.setText("중지됨. 다시 [요약 시작]을 누를 수 있습니다.")
        self.run_btn.setEnabled(bool(self._path))
        self._enable_outputs(bool(self.result.toPlainText()))

    def _on_error(self, err: str) -> None:
        self._finish_common()
        msg = err.splitlines()[-1] if err else ""
        self.status.setText(f"⚠️ 오류: {msg}")
        self.run_btn.setEnabled(bool(self._path))
        QMessageBox.warning(self, "요약 오류", msg or "요약 중 오류가 발생했습니다.")

    # ------------------------------------------------------------------ 출력
    def _copy(self) -> None:
        QApplication.clipboard().setText(self.result.toPlainText())
        self.copy_btn.setText("복사됨!")
        QTimer.singleShot(1200, lambda: self.copy_btn.setText("복사"))

    def _default_name(self, ext: str) -> str:
        if self._path:
            return os.path.splitext(os.path.basename(self._path))[0] + f"_요약{ext}"
        return f"요약{ext}"

    def _save_docx(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Word(.docx)로 저장", self._default_name(".docx"), "Word (*.docx)"
        )
        if not path:
            return
        if not path.lower().endswith(".docx"):
            path += ".docx"
        self._write_out(path, lambda: self._write_docx(path, self.result.toPlainText()))

    def _save(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "요약 저장", self._default_name(".md"),
            "Markdown (*.md);;텍스트 (*.txt)",
        )
        if not path:
            return
        self._write_out(path, lambda: self._write_plain(path, self.result.toPlainText()))

    @staticmethod
    def _write_plain(path: str, text: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)

    def _write_out(self, path: str, writer) -> None:
        try:
            writer()
            QMessageBox.information(self, "완료", f"저장했습니다:\n{path}")
        except OSError as e:
            QMessageBox.warning(self, "오류", str(e))
        except Exception as e:  # noqa: BLE001 — 저장 실패를 사용자에게 안내
            QMessageBox.warning(self, "오류", f"저장 중 오류가 발생했습니다:\n{e}")

    @staticmethod
    def _write_docx(path: str, text: str) -> None:
        """요약 텍스트를 Word(.docx)로 저장. 앞 공백 들여쓰기를 문단 들여쓰기로 반영."""
        import docx
        from docx.shared import Inches, Pt

        doc = docx.Document()
        for raw in text.split("\n"):
            stripped = raw.lstrip(" ")
            depth = (len(raw) - len(stripped)) // 3  # 요약기 들여쓰기 단위(공백 3칸)
            para = doc.add_paragraph(stripped)
            fmt = para.paragraph_format
            if depth:
                fmt.left_indent = Inches(0.25 * depth)
            fmt.space_after = Pt(2)
        doc.save(path)

    # ------------------------------------------------------------------ 종료
    def shutdown(self) -> None:
        if self._worker is not None:
            self._worker.cancel()
