"""에디토리얼 라이트 테마 (ElevenLabs 레퍼런스 기반) — QSS + 팔레트.

- 오프화이트 캔버스 + 웜 near-black 잉크
- 채도 높은 CTA 색 없음: 잉크 pill 이 유일한 primary
- 파스텔 그라디언트 오브가 유일한 색 포인트(장식 전용)
- 세리프 디스플레이(Georgia/EB Garamond) + Inter 본문
- 헤어라인 + 소프트 드롭, pill 지오메트리
"""
from __future__ import annotations

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

# --- Surface / Canvas ---
CANVAS = "#f5f5f5"
CANVAS_SOFT = "#fafafa"
SURFACE_CARD = "#ffffff"
SURFACE_STRONG = "#f0efed"

# --- Ink / Text ---
INK = "#0c0a09"
INK_PRIMARY = "#292524"        # 잉크 pill CTA
INK_PRIMARY_ACTIVE = "#0c0a09"
BODY = "#4e4e4e"
MUTED = "#777169"
MUTED_SOFT = "#a8a29e"
ON_PRIMARY = "#ffffff"

# --- Hairlines ---
HAIRLINE = "#e7e5e4"
HAIRLINE_STRONG = "#d6d3d1"

# --- Semantic (상태 표시 전용, CTA 아님) ---
SUCCESS = "#16a34a"
ERROR = "#dc2626"
WARN = "#b45309"

# --- Atmospheric gradient orbs (장식 전용) ---
G_MINT = "#a7e5d3"
G_PEACH = "#f4c5a8"
G_LAVENDER = "#c8b8e0"
G_SKY = "#a8c8e8"
G_ROSE = "#e8b8c4"

# --- 하위호환 별칭 (기존 모듈이 참조하는 이름) ---
BG = CANVAS
BG_ELEVATED = CANVAS_SOFT
CARD = SURFACE_CARD
BORDER = HAIRLINE
TEXT = INK
TEXT_MUTED = MUTED
ACCENT = INK_PRIMARY           # 사용자 버블/선택 = 잉크
ACCENT_HOVER = INK_PRIMARY_ACTIVE
GREEN = SUCCESS
GREEN_HOVER = "#15803d"
RED = ERROR
YELLOW = WARN

FONT_BODY = "'Malgun Gothic', 'Inter', 'Segoe UI', sans-serif"
FONT_DISPLAY = "'Nanum Myeongjo', 'Batang', 'EB Garamond', 'Georgia', serif"

QSS = f"""
* {{
    font-family: {FONT_BODY};
    font-size: 13px;
    color: {INK};
    letter-spacing: 0.15px;
}}
QMainWindow, QDialog, QWidget#root {{
    background: {CANVAS};
}}
QScrollArea {{ border: none; background: transparent; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}

QFrame#card {{
    background: {SURFACE_CARD};
    border: 1px solid {HAIRLINE};
    border-radius: 16px;
}}
QLabel#sectionTitle {{
    font-family: {FONT_DISPLAY};
    font-size: 21px;
    font-weight: 400;
    color: {INK};
    letter-spacing: -0.2px;
}}
QLabel#muted {{ color: {MUTED}; }}
QLabel#accent {{ color: {INK}; font-weight: 600; }}
QLabel#green {{ color: {SUCCESS}; font-weight: 600; }}
QLabel#red {{ color: {ERROR}; font-weight: 600; }}
QLabel#yellow {{ color: {WARN}; font-weight: 500; }}
QLabel#badge {{
    background: {SURFACE_STRONG};
    border: none;
    border-radius: 9999px;
    padding: 3px 12px;
    color: {MUTED};
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.9px;
}}

/* 기본 버튼 = 아웃라인 pill */
QPushButton {{
    background: transparent;
    border: 1px solid {HAIRLINE_STRONG};
    border-radius: 9999px;
    padding: 9px 18px;
    color: {INK};
    font-weight: 500;
}}
QPushButton:hover {{ background: {SURFACE_STRONG}; border-color: {INK}; }}
QPushButton:disabled {{ color: {MUTED_SOFT}; border-color: {HAIRLINE}; background: transparent; }}

/* primary / success(주요 CTA) = 잉크 pill */
QPushButton#primary, QPushButton#success {{
    background: {INK_PRIMARY}; border: none; color: {ON_PRIMARY}; font-weight: 500;
}}
QPushButton#primary:hover, QPushButton#success:hover {{ background: {INK_PRIMARY_ACTIVE}; }}
QPushButton#primary:disabled, QPushButton#success:disabled {{
    background: {SURFACE_STRONG}; color: {MUTED_SOFT};
}}

/* danger = 아웃라인 pill + 에러색 텍스트 */
QPushButton#danger {{ color: {ERROR}; border-color: {HAIRLINE_STRONG}; }}
QPushButton#danger:hover {{ border-color: {ERROR}; background: #fef2f2; }}

QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox, QPlainTextEdit, QTextEdit {{
    background: {SURFACE_CARD};
    border: 1px solid {HAIRLINE_STRONG};
    border-radius: 8px;
    padding: 7px 12px;
    color: {INK};
    selection-background-color: {INK_PRIMARY};
    selection-color: {ON_PRIMARY};
}}
QComboBox:focus, QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus,
QSpinBox:focus, QDoubleSpinBox:focus {{
    border: 2px solid {INK};
    padding: 6px 11px;
}}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{
    background: {SURFACE_CARD};
    border: 1px solid {HAIRLINE};
    border-radius: 8px;
    selection-background-color: {SURFACE_STRONG};
    selection-color: {INK};
    outline: none;
}}

QListWidget {{
    background: {SURFACE_CARD};
    border: 1px solid {HAIRLINE};
    border-radius: 12px;
    padding: 5px;
}}
QListWidget::item {{ padding: 9px; border-radius: 8px; color: {BODY}; }}
QListWidget::item:selected {{ background: {SURFACE_STRONG}; color: {INK}; }}
QListWidget::item:hover {{ background: {CANVAS_SOFT}; }}

QProgressBar {{
    background: {SURFACE_STRONG};
    border: none;
    border-radius: 9999px;
    text-align: center;
    height: 16px;
    color: {INK};
    font-size: 11px;
}}
QProgressBar::chunk {{ background: {INK_PRIMARY}; border-radius: 9999px; }}

QCheckBox {{ spacing: 7px; color: {BODY}; }}
QCheckBox::indicator {{
    width: 17px; height: 17px; border-radius: 5px;
    border: 1px solid {HAIRLINE_STRONG}; background: {SURFACE_CARD};
}}
QCheckBox::indicator:checked {{ background: {INK_PRIMARY}; border-color: {INK_PRIMARY}; }}

QTabBar::tab {{
    background: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    padding: 9px 16px;
    color: {MUTED};
    font-weight: 500;
}}
QTabBar::tab:selected {{ color: {INK}; border-bottom-color: {INK}; }}
QTabWidget::pane {{ border: none; }}

QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {HAIRLINE_STRONG}; border-radius: 5px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {MUTED}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {HAIRLINE_STRONG}; border-radius: 5px; min-width: 30px; }}

QToolTip {{
    background: {INK}; color: {ON_PRIMARY}; border: none;
    padding: 6px 10px; border-radius: 6px;
}}
QMessageBox, QInputDialog, QFileDialog {{ background: {CANVAS}; }}
"""


def apply(app: QApplication) -> None:
    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window, QColor(CANVAS))
    pal.setColor(QPalette.ColorRole.Base, QColor(SURFACE_CARD))
    pal.setColor(QPalette.ColorRole.AlternateBase, QColor(CANVAS_SOFT))
    pal.setColor(QPalette.ColorRole.Text, QColor(INK))
    pal.setColor(QPalette.ColorRole.WindowText, QColor(INK))
    pal.setColor(QPalette.ColorRole.Button, QColor(SURFACE_CARD))
    pal.setColor(QPalette.ColorRole.ButtonText, QColor(INK))
    pal.setColor(QPalette.ColorRole.Highlight, QColor(INK_PRIMARY))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor(ON_PRIMARY))
    pal.setColor(QPalette.ColorRole.ToolTipBase, QColor(INK))
    pal.setColor(QPalette.ColorRole.ToolTipText, QColor(ON_PRIMARY))
    app.setPalette(pal)
    app.setStyleSheet(QSS)
