"""QRunnable 기반 워커 인프라 — 전 기능 응답성의 backbone.

core/ 의 순수 로직을 백그라운드 스레드에서 돌리고 결과를 Qt 신호로 UI 에 전달한다.
UI 위젯은 절대 워커 스레드에서 직접 건드리지 않는다(신호/슬롯만 사용).
"""
from __future__ import annotations

import threading
import traceback
from typing import Callable

from PySide6.QtCore import QObject, QRunnable, Signal, Slot


class WorkerSignals(QObject):
    started = Signal()
    progress = Signal(dict)      # 임의 진행 상황 dict
    message = Signal(str)        # 로그/상태 문자열
    token = Signal(str)          # 채팅 토큰 델타
    finished = Signal(object)    # 최종 결과
    error = Signal(str)
    cancelled = Signal()


class CancellableWorker(QRunnable):
    """fn(*args, cancel_event=..., signals=..., **kwargs) 형태의 함수를 실행."""

    def __init__(self, fn: Callable, *args, **kwargs):
        super().__init__()
        self.signals = WorkerSignals()
        self._fn = fn
        self._args = args
        self._kwargs = kwargs
        self._cancel = threading.Event()

    def cancel(self) -> None:
        self._cancel.set()

    @property
    def is_cancelled(self) -> bool:
        return self._cancel.is_set()

    @Slot()
    def run(self) -> None:
        self.signals.started.emit()
        try:
            result = self._fn(
                *self._args,
                cancel_event=self._cancel,
                signals=self.signals,
                **self._kwargs,
            )
            if self._cancel.is_set():
                self.signals.cancelled.emit()
            else:
                self.signals.finished.emit(result)
        except Exception:  # noqa: BLE001 — UI 로 안전 전달
            self.signals.error.emit(traceback.format_exc())
