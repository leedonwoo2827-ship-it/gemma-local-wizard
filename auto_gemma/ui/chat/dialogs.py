"""고급 설정 다이얼로그 (온도 / top-p / 컨텍스트 길이)."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QSpinBox,
    QWidget,
)

from auto_gemma.app.config import ChatOptions


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
