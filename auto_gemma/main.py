"""애플리케이션 진입점.

    python -m auto_gemma.main
"""
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from auto_gemma.app import config, theme
from auto_gemma.ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("AutoGemmaStarter")
    app.setOrganizationName("AutoGemmaStarter")
    # Qt(Windows)가 창 제목 뒤에 applicationDisplayName 을 자동으로 덧붙이는데,
    # 미설정 시 applicationName 으로 폴백되어 " - AutoGemmaStarter" 가 붙는다.
    # 빈 문자열로 명시해 자동 덧붙임을 차단한다.
    app.setApplicationDisplayName("")
    config.apply_ollama_env()  # 저장된 모델 위치(OLLAMA_MODELS)를 환경에 반영
    theme.apply(app)

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
