"""파스텔 그라디언트 오브 배경 위젯 — 에디토리얼 라이트 테마의 시그니처.

색은 순수 장식(atmosphere)으로만 쓰이며 텍스트/버튼 색으로는 쓰지 않는다.
"""
from __future__ import annotations

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QRadialGradient
from PySide6.QtWidgets import QWidget

from auto_gemma.app import theme

# (상대 x, 상대 y, 반지름 px, 색, 중심 알파)
_DEFAULT_ORBS = [
    (0.12, 0.35, 260, theme.G_SKY, 90),
    (0.62, 0.15, 300, theme.G_PEACH, 80),
    (0.88, 0.70, 240, theme.G_MINT, 80),
    (0.40, 0.85, 220, theme.G_LAVENDER, 70),
]


class AtmosphereWidget(QWidget):
    """자식 레이아웃을 담으면서 배경에 파스텔 오브를 그린다."""

    def __init__(self, orbs=None, base=theme.CANVAS, parent: QWidget | None = None):
        super().__init__(parent)
        self._orbs = orbs if orbs is not None else _DEFAULT_ORBS
        self._base = base
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.fillRect(self.rect(), QColor(self._base))
        w, h = self.width(), self.height()
        p.setPen(Qt.PenStyle.NoPen)
        for rx, ry, rad, col, alpha in self._orbs:
            cx, cy = w * rx, h * ry
            grad = QRadialGradient(cx, cy, rad)
            c0 = QColor(col)
            c0.setAlpha(alpha)
            c1 = QColor(col)
            c1.setAlpha(0)
            grad.setColorAt(0.0, c0)
            grad.setColorAt(1.0, c1)
            p.setBrush(grad)
            p.drawEllipse(QPointF(cx, cy), rad, rad)
        p.end()
