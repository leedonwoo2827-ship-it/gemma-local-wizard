"""다크 테마 QSS + 팔레트."""
from __future__ import annotations

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

# 색상 팔레트 (레퍼런스 앱의 딥 네이비 다크 톤)
BG = "#0d1220"
BG_ELEVATED = "#151b2e"
CARD = "#1a2236"
BORDER = "#2a3450"
TEXT = "#e6ebf5"
TEXT_MUTED = "#9aa7c7"
ACCENT = "#3b82f6"
ACCENT_HOVER = "#2f6fe0"
GREEN = "#22c55e"
GREEN_HOVER = "#16a34a"
RED = "#ef4444"
YELLOW = "#eab308"

QSS = f"""
* {{
    font-family: "Malgun Gothic", "Segoe UI", sans-serif;
    font-size: 13px;
    color: {TEXT};
}}
QMainWindow, QDialog, QWidget#root {{
    background: {BG};
}}
QScrollArea {{ border: none; background: transparent; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}

QFrame#card {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 12px;
}}
QLabel#sectionTitle {{
    font-size: 15px;
    font-weight: 700;
    color: {TEXT};
}}
QLabel#muted {{ color: {TEXT_MUTED}; }}
QLabel#accent {{ color: {ACCENT}; font-weight: 600; }}
QLabel#green {{ color: {GREEN}; font-weight: 600; }}
QLabel#red {{ color: {RED}; font-weight: 600; }}
QLabel#yellow {{ color: {YELLOW}; }}
QLabel#badge {{
    background: {BG_ELEVATED};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 2px 8px;
    color: {TEXT_MUTED};
}}

QPushButton {{
    background: {BG_ELEVATED};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 8px 14px;
    color: {TEXT};
}}
QPushButton:hover {{ background: {CARD}; border-color: {ACCENT}; }}
QPushButton:disabled {{ color: {TEXT_MUTED}; background: {BG}; border-color: {BORDER}; }}

QPushButton#primary {{
    background: {ACCENT}; border: none; color: white; font-weight: 600;
}}
QPushButton#primary:hover {{ background: {ACCENT_HOVER}; }}
QPushButton#primary:disabled {{ background: #26365c; color: {TEXT_MUTED}; }}

QPushButton#success {{
    background: {GREEN}; border: none; color: white; font-weight: 600;
}}
QPushButton#success:hover {{ background: {GREEN_HOVER}; }}

QPushButton#danger {{ color: {RED}; }}
QPushButton#danger:hover {{ border-color: {RED}; }}

QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox, QPlainTextEdit, QTextEdit {{
    background: {BG_ELEVATED};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 6px 10px;
    selection-background-color: {ACCENT};
}}
QComboBox:focus, QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus {{
    border-color: {ACCENT};
}}
QComboBox QAbstractItemView {{
    background: {BG_ELEVATED};
    border: 1px solid {BORDER};
    selection-background-color: {ACCENT};
}}

QListWidget {{
    background: {BG_ELEVATED};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 4px;
}}
QListWidget::item {{ padding: 8px; border-radius: 6px; }}
QListWidget::item:selected {{ background: {ACCENT}; color: white; }}
QListWidget::item:hover {{ background: {CARD}; }}

QProgressBar {{
    background: {BG_ELEVATED};
    border: 1px solid {BORDER};
    border-radius: 8px;
    text-align: center;
    height: 18px;
}}
QProgressBar::chunk {{ background: {ACCENT}; border-radius: 7px; }}

QCheckBox {{ spacing: 6px; }}
QCheckBox::indicator {{
    width: 16px; height: 16px; border-radius: 4px;
    border: 1px solid {BORDER}; background: {BG_ELEVATED};
}}
QCheckBox::indicator:checked {{ background: {GREEN}; border-color: {GREEN}; }}

QTabBar::tab {{
    background: {BG_ELEVATED};
    border: 1px solid {BORDER};
    padding: 8px 16px;
    border-top-left-radius: 8px; border-top-right-radius: 8px;
}}
QTabBar::tab:selected {{ background: {CARD}; border-bottom-color: {CARD}; color: {ACCENT}; }}
QTabWidget::pane {{ border: 1px solid {BORDER}; border-radius: 8px; top: -1px; }}

QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {BORDER}; border-radius: 5px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {TEXT_MUTED}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {BORDER}; border-radius: 5px; min-width: 30px; }}
"""


def apply(app: QApplication) -> None:
    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window, QColor(BG))
    pal.setColor(QPalette.ColorRole.Base, QColor(BG_ELEVATED))
    pal.setColor(QPalette.ColorRole.Text, QColor(TEXT))
    pal.setColor(QPalette.ColorRole.WindowText, QColor(TEXT))
    pal.setColor(QPalette.ColorRole.Button, QColor(BG_ELEVATED))
    pal.setColor(QPalette.ColorRole.ButtonText, QColor(TEXT))
    pal.setColor(QPalette.ColorRole.Highlight, QColor(ACCENT))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor("white"))
    app.setPalette(pal)
    app.setStyleSheet(QSS)
