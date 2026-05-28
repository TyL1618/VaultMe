"""
theme.py - VaultMe 色盤、樣式表、共用 UI 元件
與 WealthMatrix 相同的 Cyberpunk 深色風格
"""
from PyQt6.QtWidgets import QFrame, QLabel
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtCore import Qt

SCALE = 1.0

def set_scale(s: float):
    global SCALE
    SCALE = max(0.5, min(3.0, s))

def S(n):
    return int(round(n * SCALE))

def Sf(n):
    return n * SCALE

CP = {
    "bg":        "#05080f",
    "panel":     "#090f1a",
    "border":    "#1a3a55",
    "cyan":      "#00f5ff",
    "cyan_dim":  "#00a8b0",
    "green":     "#00ff88",
    "green_dim": "#00aa55",
    "pink":      "#ff2d78",
    "red":       "#ff4444",
    "blue":      "#1a6fff",
    "text":      "#c8e0f0",
    "muted":     "#7aaabb",
    "gold":      "#ffd700",
    "panel2":    "#0b1422",
    "orange":    "#ff9500",
}

CATEGORY_COLORS = {
    "銀行": "#ffd700",
    "社群": "#00f5ff",
    "Email": "#ff9500",
    "娛樂": "#c084fc",
    "購物": "#fb923c",
    "政府": "#94a3b8",
    "軟體": "#00ff88",
    "其他": "#7aaabb",
}

def get_stylesheet():
    return _build_stylesheet()

def _build_stylesheet():
    return f"""
QMainWindow, QWidget {{
    background-color: {CP['bg']};
    color: {CP['text']};
    font-family: 'Courier New', monospace;
    font-size: {S(13)}px;
}}
QLabel {{
    color: {CP['text']};
    background: transparent;
}}
QLabel#title {{
    color: {CP['cyan']};
    font-size: {S(22)}px;
    font-weight: bold;
    letter-spacing: {S(6)}px;
}}
QLabel#section_title {{
    color: {CP['cyan_dim']};
    font-size: {S(11)}px;
    letter-spacing: {S(3)}px;
    font-weight: bold;
}}
QLabel#muted {{
    color: {CP['muted']};
    font-size: {S(12)}px;
}}

QPushButton {{
    background-color: transparent;
    border: 1px solid {CP['cyan_dim']};
    color: {CP['cyan']};
    border-radius: {S(4)}px;
    padding: {S(5)}px {S(14)}px;
    font-family: 'Courier New', monospace;
    font-size: {S(11)}px;
    letter-spacing: 1px;
}}
QPushButton:hover {{
    background-color: rgba(0,245,255,0.1);
}}
QPushButton:pressed {{
    background-color: rgba(0,245,255,0.2);
}}
QPushButton#btn_green {{
    border-color: rgba(0,255,136,0.4);
    color: {CP['green']};
}}
QPushButton#btn_green:hover {{ background-color: rgba(0,255,136,0.1); }}
QPushButton#btn_pink {{
    border-color: rgba(255,45,120,0.4);
    color: {CP['pink']};
    border-radius: {S(3)}px;
    padding: {S(4)}px {S(10)}px;
}}
QPushButton#btn_pink:hover {{ background-color: rgba(255,45,120,0.1); }}
QPushButton#btn_gold {{
    border-color: rgba(255,215,0,0.4);
    color: {CP['gold']};
}}
QPushButton#btn_gold:hover {{ background-color: rgba(255,215,0,0.1); }}
QPushButton#btn_muted {{
    border-color: {CP['border']};
    color: {CP['muted']};
}}
QPushButton#btn_muted:hover {{ background-color: rgba(255,255,255,0.04); }}
QPushButton#category_btn {{
    border: none;
    border-left: 2px solid transparent;
    border-radius: 0;
    color: {CP['muted']};
    text-align: left;
    padding: {S(8)}px {S(16)}px;
    font-size: {S(12)}px;
    letter-spacing: 1px;
}}
QPushButton#category_btn:hover {{
    background-color: rgba(0,245,255,0.06);
    color: {CP['text']};
}}
QPushButton#category_btn[active="true"] {{
    border-left: 2px solid {CP['cyan']};
    color: {CP['cyan']};
    background-color: rgba(0,245,255,0.08);
}}

QLineEdit {{
    background-color: rgba(0,245,255,0.04);
    border: 1px solid {CP['border']};
    border-radius: {S(4)}px;
    color: {CP['text']};
    font-family: 'Courier New', monospace;
    font-size: {S(13)}px;
    padding: {S(6)}px {S(10)}px;
    selection-background-color: {CP['cyan_dim']};
    min-height: {S(28)}px;
}}
QLineEdit:focus {{
    border-color: {CP['cyan_dim']};
}}

QComboBox {{
    background-color: rgba(0,245,255,0.04);
    border: 1px solid {CP['border']};
    border-radius: {S(4)}px;
    color: {CP['text']};
    font-family: 'Courier New', monospace;
    font-size: {S(13)}px;
    padding: {S(4)}px {S(10)}px;
    min-height: {S(28)}px;
}}
QComboBox::drop-down {{
    border: none;
    width: {S(24)}px;
}}
QComboBox QAbstractItemView {{
    background-color: {CP['panel2']};
    border: 1px solid {CP['border']};
    color: {CP['text']};
    font-size: {S(13)}px;
    selection-background-color: {CP['cyan_dim']};
}}

QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{
    background: {CP['panel']};
    width: {S(10)}px;
    border-radius: {S(5)}px;
    border: 1px solid rgba(0,245,255,0.10);
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 {CP['pink']}, stop:1 {CP['cyan']});
    border-radius: {S(4)}px;
    min-height: {S(28)}px;
    border: 1px solid rgba(0,245,255,0.55);
}}
QScrollBar::handle:vertical:hover {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #ff6ba0, stop:1 #40faff);
    border: 1px solid {CP['cyan']};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; border: none; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}

QDialog {{
    background-color: #0a1525;
    border: 1px solid {CP['cyan_dim']};
    border-radius: {S(8)}px;
}}
QFormLayout QLabel {{
    color: {CP['muted']};
    font-size: {S(12)}px;
    letter-spacing: 1px;
}}
"""

class _LazyStyle:
    def __init__(self, fn):
        self._fn = fn
    def __str__(self):
        return self._fn()
    def __format__(self, spec):
        return format(str(self), spec)

STYLESHEET = _LazyStyle(get_stylesheet)

def get_dialog_style():
    return f"""
    QDialog {{
        background-color: #0a1525;
        border: 1px solid {CP['cyan_dim']};
    }}
    QLabel {{ color: {CP['muted']}; font-size: {S(12)}px; letter-spacing: 1px; }}
    QLabel#field_label {{ color: {CP['muted']}; font-size: {S(11)}px; }}
    QLineEdit, QComboBox, QTextEdit {{
        background: rgba(0,245,255,0.04);
        border: 1px solid {CP['border']};
        border-radius: {S(4)}px;
        color: {CP['text']};
        font-family: 'Courier New', monospace;
        font-size: {S(13)}px;
        padding: {S(6)}px {S(10)}px;
        min-height: {S(28)}px;
    }}
    QTextEdit {{
        min-height: {S(60)}px;
    }}
    QLineEdit:focus, QComboBox:focus, QTextEdit:focus {{
        border-color: {CP['cyan_dim']};
    }}
    QComboBox::drop-down {{ border: none; width: {S(24)}px; }}
    QComboBox QAbstractItemView {{
        background-color: {CP['panel2']};
        border: 1px solid {CP['border']};
        color: {CP['text']};
        selection-background-color: {CP['cyan_dim']};
    }}
    QPushButton {{
        background: transparent;
        border: 1px solid {CP['cyan_dim']};
        color: {CP['cyan']};
        border-radius: {S(4)}px;
        padding: {S(8)}px 0;
        font-family: 'Courier New', monospace;
        font-size: {S(12)}px;
        letter-spacing: 1px;
    }}
    QPushButton:hover {{ background: rgba(0,245,255,0.12); }}
    QPushButton#btn_cancel {{
        border-color: {CP['border']};
        color: {CP['muted']};
    }}
    QPushButton#btn_cancel:hover {{ background: rgba(255,255,255,0.04); }}
    QPushButton#btn_pink {{
        border-color: rgba(255,45,120,0.4);
        color: {CP['pink']};
    }}
    QPushButton#btn_pink:hover {{ background: rgba(255,45,120,0.1); }}
    QPushButton#btn_small {{
        padding: {S(3)}px {S(8)}px;
        font-size: {S(10)}px;
        min-height: 0;
    }}
"""

DIALOG_STYLE = _LazyStyle(get_dialog_style)


class CpPanel(QFrame):
    def __init__(self, accent=None, parent=None):
        super().__init__(parent)
        if accent is None:
            accent = CP["cyan"]
        self.accent = QColor(accent)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {CP['panel']};
                border: 1px solid #1a3a55;
                border-radius: {S(6)}px;
            }}
        """)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self.accent)
        painter.drawRoundedRect(0, 0, self.width(), S(3), 2, 2)


def section_label(text):
    lbl = QLabel(text)
    lbl.setObjectName("section_title")
    return lbl


def muted_label(text):
    lbl = QLabel(text)
    lbl.setObjectName("muted")
    return lbl
