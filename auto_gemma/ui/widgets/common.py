"""재사용 UI 위젯: 카드 프레임, 배지 라벨 등."""
from __future__ import annotations

from PySide6.QtCore import Qt, QThreadPool
from PySide6.QtGui import QCursor, QGuiApplication
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


def center_on_active_screen(widget: QWidget) -> None:
    """위젯을 (마우스가 있는) 화면 중앙에 배치.

    다중 모니터 환경에서 창이 보이지 않는(화면 밖) 위치에 생성되는 문제를 방지한다.
    show() 이후 호출해야 프레임 크기가 반영된다.
    """
    screen = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
    if screen is None:
        return
    geo = screen.availableGeometry()
    frame = widget.frameGeometry()
    frame.moveCenter(geo.center())
    top_left = frame.topLeft()
    # 창이 화면보다 크면 중앙 정렬 시 위/왼쪽이 잘린다 → 최소 화면 안쪽으로 클램프
    top_left.setX(max(geo.left(), top_left.x()))
    top_left.setY(max(geo.top(), top_left.y()))
    widget.move(top_left)


# 다운로드 전용 스레드풀 (채팅/임베딩과 분리해 pull 이 채팅을 막지 않도록)
_download_pool: QThreadPool | None = None


def download_pool() -> QThreadPool:
    global _download_pool
    if _download_pool is None:
        _download_pool = QThreadPool()
        _download_pool.setMaxThreadCount(2)
    return _download_pool


def general_pool() -> QThreadPool:
    pool = QThreadPool.globalInstance()
    if pool.maxThreadCount() < 4:
        pool.setMaxThreadCount(8)
    return pool


class Card(QFrame):
    """둥근 모서리 카드 컨테이너."""

    def __init__(self, title: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("card")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(18, 16, 18, 16)
        self._layout.setSpacing(10)
        if title:
            lbl = QLabel(title)
            lbl.setObjectName("sectionTitle")
            self._layout.addWidget(lbl)

    def body(self) -> QVBoxLayout:
        return self._layout

    def add(self, widget: QWidget) -> QWidget:
        self._layout.addWidget(widget)
        return widget

    def add_layout(self, layout) -> None:
        self._layout.addLayout(layout)


def muted(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("muted")
    lbl.setWordWrap(True)
    return lbl


def row(*widgets: QWidget, spacing: int = 8) -> QHBoxLayout:
    lay = QHBoxLayout()
    lay.setSpacing(spacing)
    for w in widgets:
        if w is None:
            lay.addStretch(1)
        else:
            lay.addWidget(w)
    return lay


def hline() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setStyleSheet("color:#2a3450; background:#2a3450; max-height:1px;")
    f.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    return f
