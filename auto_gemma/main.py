"""애플리케이션 진입점.

    python -m auto_gemma.main
"""
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from auto_gemma import __version__
from auto_gemma.app import theme
from auto_gemma.ui.wizard.wizard_window import WizardWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("AutoGemmaStarter")
    app.setApplicationDisplayName(f"Auto Gemma Starter v{__version__}")
    app.setOrganizationName("AutoGemmaStarter")
    theme.apply(app)

    window = WizardWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
