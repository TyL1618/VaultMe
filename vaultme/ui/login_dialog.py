"""
login_dialog.py - 啟動時主密碼視窗
  首次使用 → 設定主密碼 + 密碼提示
  之後     → 輸入密碼解鎖 + 忘記密碼提示
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QMessageBox
)
from PyQt6.QtCore import Qt

from vaultme.theme import CP, S, get_dialog_style
from vaultme.core import data_manager


def _base_style():
    return get_dialog_style() + f"""
        QDialog {{
            background-color: #07101e;
            border: 1px solid {CP['cyan_dim']};
            border-radius: {S(10)}px;
        }}
    """


class LoginDialog(QDialog):
    """解鎖視窗（回訪使用者）"""

    def __init__(self, parent=None, error_msg: str = ""):
        super().__init__(parent)
        self.setWindowTitle("VaultMe")
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setModal(True)
        self.setMinimumWidth(S(380))
        self.setStyleSheet(_base_style())
        self._password = ""
        self._build_ui(error_msg)

    def _build_ui(self, error_msg: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(S(36), S(36), S(36), S(32))
        layout.setSpacing(S(16))

        # ── Logo ──────────────────────────────────────────────────────
        _add_logo(layout)

        # ── 錯誤訊息 ───────────────────────────────────────────────────
        if error_msg:
            err = QLabel(f"⚠  {error_msg}")
            err.setWordWrap(True)
            err.setAlignment(Qt.AlignmentFlag.AlignCenter)
            err.setStyleSheet(f"""
                color:{CP['pink']};font-size:{S(11)}px;
                background:rgba(255,45,120,.08);
                border:1px solid rgba(255,45,120,.3);
                border-radius:{S(4)}px;padding:{S(6)}px {S(10)}px;
            """)
            layout.addWidget(err)

        # ── 密碼輸入 ───────────────────────────────────────────────────
        layout.addWidget(_field_label("主密碼"))
        pwd_row = QHBoxLayout()
        pwd_row.setSpacing(S(6))
        self.pwd_input = QLineEdit()
        self.pwd_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pwd_input.setPlaceholderText("輸入主密碼…")
        self.pwd_input.returnPressed.connect(self._on_ok)
        pwd_row.addWidget(self.pwd_input)
        pwd_row.addWidget(_eye_btn(self.pwd_input))
        layout.addLayout(pwd_row)

        # ── 忘記密碼 ───────────────────────────────────────────────────
        hint_btn = QPushButton("忘記密碼？")
        hint_btn.setStyleSheet(f"""
            QPushButton {{
                background:transparent;border:none;
                color:{CP['muted']};font-size:{S(11)}px;
                text-decoration:underline;padding:0;
            }}
            QPushButton:hover {{ color:{CP['cyan_dim']}; }}
        """)
        hint_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        hint_btn.clicked.connect(self._show_hint)
        layout.addWidget(hint_btn, alignment=Qt.AlignmentFlag.AlignRight)

        # ── 解鎖按鈕 ───────────────────────────────────────────────────
        layout.addWidget(_unlock_btn(self._on_ok))

        self.pwd_input.setFocus()

    def _show_hint(self):
        hint = data_manager.get_hint()
        if hint:
            QMessageBox.information(self, "密碼提示", f"你當初設定的提示：\n\n  {hint}")
        else:
            QMessageBox.information(self, "密碼提示",
                "沒有儲存提示。\n\n如果真的忘了，只能刪除 vault.enc 重設（資料會遺失）。")

    def _on_ok(self):
        pwd = self.pwd_input.text().strip()
        if not pwd:
            return
        self._password = pwd
        self.accept()

    def get_password(self) -> str:
        return self._password


# ────────────────────────────────────────────────────────────────────────
class RegisterDialog(QDialog):
    """首次使用：設定主密碼 + 密碼提示"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("VaultMe - 初次設定")
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setModal(True)
        self.setMinimumWidth(S(400))
        self.setStyleSheet(_base_style())
        self._password = ""
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(S(36), S(36), S(36), S(32))
        layout.setSpacing(S(14))

        # ── Logo ──────────────────────────────────────────────────────
        _add_logo(layout)

        # ── 說明 ───────────────────────────────────────────────────────
        info = QLabel("第一次使用，請設定主密碼。\n主密碼是你所有資料的加密金鑰，請務必記住。")
        info.setWordWrap(True)
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info.setStyleSheet(f"""
            color:{CP['muted']};font-size:{S(11)}px;
            background:rgba(0,245,255,.04);
            border:1px solid {CP['border']};
            border-radius:{S(4)}px;padding:{S(8)}px;
        """)
        layout.addWidget(info)

        # ── 新密碼 ─────────────────────────────────────────────────────
        layout.addWidget(_field_label("設定主密碼"))
        row1 = QHBoxLayout(); row1.setSpacing(S(6))
        self.pwd1 = QLineEdit()
        self.pwd1.setEchoMode(QLineEdit.EchoMode.Password)
        self.pwd1.setPlaceholderText("輸入主密碼…")
        row1.addWidget(self.pwd1)
        row1.addWidget(_eye_btn(self.pwd1))
        layout.addLayout(row1)

        # ── 確認密碼 ───────────────────────────────────────────────────
        layout.addWidget(_field_label("確認主密碼"))
        row2 = QHBoxLayout(); row2.setSpacing(S(6))
        self.pwd2 = QLineEdit()
        self.pwd2.setEchoMode(QLineEdit.EchoMode.Password)
        self.pwd2.setPlaceholderText("再輸入一次…")
        self.pwd2.returnPressed.connect(self._on_ok)
        row2.addWidget(self.pwd2)
        row2.addWidget(_eye_btn(self.pwd2))
        layout.addLayout(row2)

        # ── 密碼提示 ───────────────────────────────────────────────────
        layout.addWidget(_field_label("密碼提示（選填，忘記時顯示，不是密碼本身）"))
        self.hint_input = QLineEdit()
        self.hint_input.setPlaceholderText("例：我家附近那條街 + 生日 (可不填)")
        layout.addWidget(self.hint_input)

        # ── 錯誤訊息 ───────────────────────────────────────────────────
        self.err_lbl = QLabel()
        self.err_lbl.setWordWrap(True)
        self.err_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.err_lbl.setStyleSheet(f"""
            color:{CP['pink']};font-size:{S(11)}px;
            background:rgba(255,45,120,.08);
            border:1px solid rgba(255,45,120,.3);
            border-radius:{S(4)}px;padding:{S(6)}px;
        """)
        self.err_lbl.hide()
        layout.addWidget(self.err_lbl)

        # ── 設定按鈕 ───────────────────────────────────────────────────
        layout.addWidget(_unlock_btn(self._on_ok, text="建立保險箱  →"))

        self.pwd1.setFocus()

    def _on_ok(self):
        p1 = self.pwd1.text()
        p2 = self.pwd2.text()

        if not p1:
            self._show_err("密碼不能為空"); return
        if len(p1) < 4:
            self._show_err("密碼至少 4 個字元"); return
        if p1 != p2:
            self._show_err("兩次輸入的密碼不一致"); return

        # 儲存提示
        hint = self.hint_input.text().strip()
        if hint:
            data_manager.save_hint(hint)

        self._password = p1
        self.accept()

    def _show_err(self, msg: str):
        self.err_lbl.setText(f"⚠  {msg}")
        self.err_lbl.show()

    def get_password(self) -> str:
        return self._password


# ── 共用小元件 ─────────────────────────────────────────────────────────
def _add_logo(layout: QVBoxLayout):
    title = QLabel("🔐  VAULT ME")
    title.setAlignment(Qt.AlignmentFlag.AlignCenter)
    title.setStyleSheet(f"""
        color:{CP['cyan']};
        font-family:'Courier New',monospace;
        font-size:{S(22)}px;font-weight:bold;
        letter-spacing:{S(6)}px;background:transparent;
    """)
    layout.addWidget(title)

    sub = QLabel("SECURE PASSWORD MANAGER")
    sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
    sub.setStyleSheet(f"""
        color:{CP['muted']};
        font-family:'Courier New',monospace;
        font-size:{S(9)}px;letter-spacing:{S(4)}px;background:transparent;
    """)
    layout.addWidget(sub)

    sep = QLabel()
    sep.setFixedHeight(1)
    sep.setStyleSheet(f"background:{CP['border']};border:none;margin:{S(4)}px 0;")
    layout.addWidget(sep)


def _field_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(f"color:{CP['muted']};font-size:{S(11)}px;letter-spacing:1px;")
    return lbl


def _eye_btn(target: QLineEdit) -> QPushButton:
    btn = QPushButton("👁")
    btn.setFixedSize(S(36), S(36))
    btn.setStyleSheet(f"""
        QPushButton {{
            background:rgba(0,245,255,.04);
            border:1px solid {CP['border']};
            border-radius:{S(4)}px;
            color:{CP['muted']};font-size:{S(14)}px;padding:0;
        }}
        QPushButton:hover {{ background:rgba(0,245,255,.10);color:{CP['cyan']}; }}
    """)
    def _toggle():
        vis = target.echoMode() == QLineEdit.EchoMode.Password
        target.setEchoMode(QLineEdit.EchoMode.Normal if vis else QLineEdit.EchoMode.Password)
    btn.clicked.connect(_toggle)
    return btn


def _unlock_btn(slot, text: str = "解鎖  →") -> QPushButton:
    btn = QPushButton(text)
    btn.setFixedHeight(S(42))
    btn.setStyleSheet(f"""
        QPushButton {{
            background:rgba(0,245,255,.08);
            border:1px solid {CP['cyan_dim']};
            border-radius:{S(5)}px;color:{CP['cyan']};
            font-family:'Courier New',monospace;
            font-size:{S(13)}px;letter-spacing:2px;font-weight:bold;
        }}
        QPushButton:hover {{ background:rgba(0,245,255,.18); }}
        QPushButton:pressed {{ background:rgba(0,245,255,.26); }}
    """)
    btn.clicked.connect(slot)
    return btn
