"""
entry_dialog.py - 新增 / 編輯密碼項目的對話框
支援自訂欄位（label + value 動態增減）
"""
import uuid
from datetime import datetime

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QPushButton, QComboBox,
    QTextEdit, QScrollArea, QWidget, QFrame, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from vaultme.theme import CP, S, get_dialog_style, CATEGORY_COLORS

CATEGORIES = ["銀行", "社群", "Email", "娛樂", "購物", "政府", "軟體", "其他"]


class ExtraFieldRow(QWidget):
    """一列自訂欄位（label + value + 刪除按鈕）"""
    remove_requested = pyqtSignal(object)

    def __init__(self, label="", value="", parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(S(6))

        self.label_edit = QLineEdit(label)
        self.label_edit.setPlaceholderText("欄位名稱")
        self.label_edit.setFixedWidth(S(120))
        self.label_edit.setStyleSheet(f"""
            background: rgba(0,245,255,0.04);
            border: 1px solid {CP['border']};
            border-radius: {S(4)}px;
            color: {CP['muted']};
            font-family: 'Courier New', monospace;
            font-size: {S(12)}px;
            padding: {S(5)}px {S(8)}px;
            min-height: {S(26)}px;
        """)

        self.value_edit = QLineEdit(value)
        self.value_edit.setPlaceholderText("值")
        self.value_edit.setStyleSheet(f"""
            background: rgba(0,245,255,0.04);
            border: 1px solid {CP['border']};
            border-radius: {S(4)}px;
            color: {CP['text']};
            font-family: 'Courier New', monospace;
            font-size: {S(12)}px;
            padding: {S(5)}px {S(8)}px;
            min-height: {S(26)}px;
        """)

        remove_btn = QPushButton("✕")
        remove_btn.setFixedSize(S(28), S(28))
        remove_btn.setObjectName("btn_pink")
        remove_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: 1px solid rgba(255,45,120,0.3);
                border-radius: {S(4)}px;
                color: {CP['pink']};
                font-size: {S(11)}px;
                padding: 0;
            }}
            QPushButton:hover {{ background: rgba(255,45,120,0.12); }}
        """)
        remove_btn.clicked.connect(lambda: self.remove_requested.emit(self))

        row.addWidget(self.label_edit)
        row.addWidget(self.value_edit, 1)
        row.addWidget(remove_btn)

    def get_data(self):
        return {"label": self.label_edit.text().strip(),
                "value": self.value_edit.text().strip()}


class EntryDialog(QDialog):
    def __init__(self, parent=None, entry: dict = None, mode: str = "add"):
        """
        mode: 'add' | 'edit'
        entry: 現有記錄 dict（edit 時傳入）
        """
        super().__init__(parent)
        self._mode  = mode
        self._entry = entry or {}
        self._extra_rows: list[ExtraFieldRow] = []
        self._result_entry: dict | None = None

        self.setWindowTitle("新增項目" if mode == "add" else "編輯項目")
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setModal(True)
        self.setMinimumWidth(S(460))
        self.setStyleSheet(get_dialog_style() + f"""
            QDialog {{
                background-color: #07101e;
                border: 1px solid {CP['cyan_dim']};
                border-radius: {S(8)}px;
            }}
        """)
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(S(28), S(24), S(28), S(24))
        outer.setSpacing(S(14))

        # ── 標題列 ─────────────────────────────────────────────────────
        title_row = QHBoxLayout()
        icon = "✚" if self._mode == "add" else "✎"
        lbl_title = QLabel(f"{icon}  {'新增項目' if self._mode == 'add' else '編輯項目'}")
        lbl_title.setStyleSheet(f"""
            color: {CP['cyan']};
            font-family: 'Courier New', monospace;
            font-size: {S(15)}px;
            font-weight: bold;
            letter-spacing: 2px;
        """)
        title_row.addWidget(lbl_title)
        title_row.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(S(28), S(28))
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; border: none;
                color: {CP['muted']}; font-size: {S(14)}px; padding: 0;
            }}
            QPushButton:hover {{ color: {CP['pink']}; }}
        """)
        close_btn.clicked.connect(self.reject)
        title_row.addWidget(close_btn)
        outer.addLayout(title_row)

        sep = QLabel()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {CP['border']}; border: none;")
        outer.addWidget(sep)

        # ── 表單（可捲動） ─────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        form_widget = QWidget()
        form_widget.setStyleSheet("background: transparent;")
        form = QVBoxLayout(form_widget)
        form.setContentsMargins(0, 0, S(8), 0)
        form.setSpacing(S(10))

        def _field(label_text, widget):
            lbl = QLabel(label_text)
            lbl.setStyleSheet(f"color: {CP['muted']}; font-size: {S(11)}px; letter-spacing: 1px;")
            form.addWidget(lbl)
            form.addWidget(widget)

        # 名稱
        self.name_edit = QLineEdit(self._entry.get("name", ""))
        self.name_edit.setPlaceholderText("例：台新銀行網銀")
        _field("名稱 *", self.name_edit)

        # 分類
        self.cat_combo = QComboBox()
        self.cat_combo.addItems(CATEGORIES)
        current_cat = self._entry.get("category", "其他")
        idx = CATEGORIES.index(current_cat) if current_cat in CATEGORIES else len(CATEGORIES) - 1
        self.cat_combo.setCurrentIndex(idx)
        _field("分類", self.cat_combo)

        # 帳號
        self.account_edit = QLineEdit(self._entry.get("account", ""))
        self.account_edit.setPlaceholderText("帳號 / Email / 使用者名稱")
        _field("帳號 / 使用者名稱", self.account_edit)

        # 持有人
        self.owner_edit = QLineEdit(self._entry.get("owner", ""))
        self.owner_edit.setPlaceholderText("例：蔡昀龍（選填，多人共用時區分帳號所有人）")
        _field("持有人（選填）", self.owner_edit)

        # 密碼
        pwd_lbl = QLabel("密碼 *")
        pwd_lbl.setStyleSheet(f"color: {CP['muted']}; font-size: {S(11)}px; letter-spacing: 1px;")
        form.addWidget(pwd_lbl)

        pwd_row = QHBoxLayout()
        pwd_row.setSpacing(S(6))
        self.pwd_edit = QLineEdit(self._entry.get("password", ""))
        self.pwd_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.pwd_edit.setPlaceholderText("密碼")
        pwd_row.addWidget(self.pwd_edit)

        self._show_pwd = False
        eye_btn = QPushButton("👁")
        eye_btn.setFixedSize(S(36), S(34))
        eye_btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(0,245,255,0.04);
                border: 1px solid {CP['border']};
                border-radius: {S(4)}px;
                color: {CP['muted']}; font-size: {S(13)}px; padding: 0;
            }}
            QPushButton:hover {{ background: rgba(0,245,255,0.10); color: {CP['cyan']}; }}
        """)
        eye_btn.clicked.connect(self._toggle_pwd)
        pwd_row.addWidget(eye_btn)
        form.addLayout(pwd_row)

        # 網址
        self.url_edit = QLineEdit(self._entry.get("url", ""))
        self.url_edit.setPlaceholderText("https://（選填）")
        _field("網址", self.url_edit)

        # 備註
        self.note_edit = QTextEdit(self._entry.get("note", ""))
        self.note_edit.setPlaceholderText("備註（選填）")
        self.note_edit.setFixedHeight(S(72))
        _field("備註", self.note_edit)

        # ── 自訂欄位 ────────────────────────────────────────────────────
        extra_title_row = QHBoxLayout()
        extra_lbl = QLabel("自訂欄位")
        extra_lbl.setStyleSheet(f"color: {CP['cyan_dim']}; font-size: {S(11)}px; letter-spacing: 2px;")
        extra_title_row.addWidget(extra_lbl)
        extra_title_row.addStretch()
        add_field_btn = QPushButton("＋ 新增欄位")
        add_field_btn.setFixedHeight(S(26))
        add_field_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: 1px solid rgba(0,168,176,0.4);
                border-radius: {S(3)}px;
                color: {CP['cyan_dim']};
                font-family: 'Courier New', monospace;
                font-size: {S(10)}px;
                padding: 0 {S(8)}px;
            }}
            QPushButton:hover {{ background: rgba(0,245,255,0.08); }}
        """)
        add_field_btn.clicked.connect(self._add_extra_field)
        extra_title_row.addWidget(add_field_btn)
        form.addLayout(extra_title_row)

        self.extra_container = QVBoxLayout()
        self.extra_container.setSpacing(S(6))
        form.addLayout(self.extra_container)

        # 填入已有的自訂欄位
        for ef in self._entry.get("extra_fields", []):
            self._add_extra_field(ef.get("label", ""), ef.get("value", ""))

        form.addStretch()
        scroll.setWidget(form_widget)
        scroll.setMinimumHeight(S(340))
        scroll.setMaximumHeight(S(480))
        outer.addWidget(scroll)

        # ── 底部按鈕 ────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(S(10))

        if self._mode == "edit":
            del_btn = QPushButton("刪除")
            del_btn.setObjectName("btn_pink")
            del_btn.setFixedHeight(S(38))
            del_btn.clicked.connect(self._on_delete)
            btn_row.addWidget(del_btn)

        btn_row.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("btn_cancel")
        cancel_btn.setFixedSize(S(90), S(38))
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        save_btn = QPushButton("儲存")
        save_btn.setFixedSize(S(110), S(38))
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(0,245,255,0.08);
                border: 1px solid {CP['cyan_dim']};
                border-radius: {S(4)}px;
                color: {CP['cyan']};
                font-family: 'Courier New', monospace;
                font-size: {S(12)}px;
                letter-spacing: 1px;
            }}
            QPushButton:hover {{ background: rgba(0,245,255,0.18); }}
        """)
        save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(save_btn)

        outer.addLayout(btn_row)

    def _toggle_pwd(self):
        self._show_pwd = not self._show_pwd
        mode = QLineEdit.EchoMode.Normal if self._show_pwd else QLineEdit.EchoMode.Password
        self.pwd_edit.setEchoMode(mode)

    def _add_extra_field(self, label="", value=""):
        row = ExtraFieldRow(label, value, self)
        row.remove_requested.connect(self._remove_extra_field)
        self._extra_rows.append(row)
        self.extra_container.addWidget(row)

    def _remove_extra_field(self, row: ExtraFieldRow):
        self._extra_rows.remove(row)
        self.extra_container.removeWidget(row)
        row.deleteLater()

    def _on_save(self):
        name = self.name_edit.text().strip()
        pwd  = self.pwd_edit.text()
        if not name:
            QMessageBox.warning(self, "提示", "名稱不能為空")
            return
        if not pwd:
            QMessageBox.warning(self, "提示", "密碼不能為空")
            return

        extra_fields = [d for d in (r.get_data() for r in self._extra_rows)
                        if d["label"] or d["value"]]

        self._result_entry = {
            "id":           self._entry.get("id") or str(uuid.uuid4()),
            "category":     self.cat_combo.currentText(),
            "name":         name,
            "account":      self.account_edit.text().strip(),
            "owner":        self.owner_edit.text().strip(),
            "password":     pwd,
            "url":          self.url_edit.text().strip(),
            "note":         self.note_edit.toPlainText().strip(),
            "extra_fields": extra_fields,
            "updated_at":   datetime.utcnow().isoformat(),
        }
        self.accept()

    def _on_delete(self):
        reply = QMessageBox.question(
            self, "確認刪除",
            f"確定要刪除「{self._entry.get('name', '')}」嗎？\n此動作可透過 Ctrl+Z 復原。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._result_entry = None
            self.done(2)   # 回傳值 2 = 刪除

    def get_result(self) -> dict | None:
        return self._result_entry
