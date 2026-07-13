"""애플리케이션 진입점.

    python -m auto_gemma.main
"""
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from auto_gemma.app import config, theme
from auto_gemma.ui.widgets.common import center_on_active_screen
from auto_gemma.ui.wizard.wizard_window import WizardWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Gemma")
    app.setOrganizationName("Gemma")
    # Qt(Windows)가 창 제목 뒤에 applicationDisplayName 을 자동으로 덧붙이는 것을 차단.
    app.setApplicationDisplayName("")
    config.apply_ollama_env()  # 저장된 모델 위치(OLLAMA_MODELS)를 환경에 반영
    theme.apply(app)

    window = WizardWindow()
    window.show()
    center_on_active_screen(window)  # 다중 모니터에서 화면 밖 생성 방지
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
