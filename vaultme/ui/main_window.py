"""
main_window.py - VaultMe 主視窗
左側：分類側欄
右側：搜尋列 + 項目卡片列表
底部：同步狀態列
"""
import pyperclip
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QScrollArea,
    QFrame, QSizePolicy, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QColor

from vaultme.theme import CP, S, Sf, CATEGORY_COLORS, get_stylesheet, CpPanel, section_label
from vaultme.core import data_manager
from vaultme.ui.entry_dialog import EntryDialog

CATEGORIES     = ["全部", "銀行", "社群", "Email", "娛樂", "購物", "政府", "軟體", "其他"]
CAT_ICONS      = {"全部": "☰", "銀行": "🏦", "社群": "💬", "Email": "✉",
                  "娛樂": "🎮", "購物": "🛒", "政府": "🏛", "軟體": "💻", "其他": "⋯"}
SYNC_INTERVAL  = 5 * 60 * 1000   # 5 分鐘（ms）
CLIPBOARD_TTL  = 30               # 秒


# ────────────────────────────────────────────────────────────────────────
class EntryCard(QFrame):
    """單筆密碼項目卡片"""
    edit_clicked   = pyqtSignal(dict)
    copy_clicked   = pyqtSignal(str, object)   # password, card

    def __init__(self, entry: dict, parent=None):
        super().__init__(parent)
        self.entry   = entry
        self._copied = False

        cat   = entry.get("category", "其他")
        color = CATEGORY_COLORS.get(cat, CP["muted"])

        self.setStyleSheet(f"""
            QFrame {{
                background-color: {CP['panel']};
                border: 1px solid {CP['border']};
                border-radius: {S(6)}px;
            }}
            QFrame:hover {{
                border-color: rgba(0,168,176,0.5);
                background-color: #0b1525;
            }}
        """)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(S(14), S(10), S(14), S(10))
        outer.setSpacing(S(6))

        # ── 上排：名稱 + 分類徽章 ──────────────────────────────────────
        top_row = QHBoxLayout()
        top_row.setSpacing(S(8))

        name_lbl = QLabel(entry.get("name", "—"))
        name_lbl.setStyleSheet(f"""
            color: {CP['text']};
            font-family: 'Courier New', monospace;
            font-size: {S(13)}px;
            font-weight: bold;
        """)
        top_row.addWidget(name_lbl)

        cat_badge = QLabel(f" {cat} ")
        cat_badge.setStyleSheet(f"""
            color: {color};
            background: transparent;
            border: 1px solid {color}44;
            border-radius: {S(3)}px;
            font-size: {S(9)}px;
            padding: {S(1)}px {S(5)}px;
            letter-spacing: 1px;
        """)
        top_row.addWidget(cat_badge)

        owner = entry.get("owner", "").strip()
        if owner:
            owner_badge = QLabel(f" 👤 {owner} ")
            owner_badge.setStyleSheet(f"""
                color: {CP['muted']};
                background: transparent;
                border: 1px solid rgba(122,170,187,0.3);
                border-radius: {S(3)}px;
                font-size: {S(9)}px;
                padding: {S(1)}px {S(5)}px;
            """)
            top_row.addWidget(owner_badge)

        top_row.addStretch()
        outer.addLayout(top_row)

        # ── 下排：帳號 + 密碼操作 ──────────────────────────────────────
        bot_row = QHBoxLayout()
        bot_row.setSpacing(S(8))

        account_lbl = QLabel(entry.get("account", "") or "—")
        account_lbl.setStyleSheet(f"""
            color: {CP['muted']};
            font-family: 'Courier New', monospace;
            font-size: {S(11)}px;
        """)
        bot_row.addWidget(account_lbl)
        bot_row.addStretch()

        # 密碼顯示（預設隱藏）
        self.pwd_lbl = QLabel("●●●●●●●●")
        self.pwd_lbl.setStyleSheet(f"""
            color: {CP['muted']};
            font-family: 'Courier New', monospace;
            font-size: {S(11)}px;
        """)
        self._pwd_visible = False
        bot_row.addWidget(self.pwd_lbl)

        # 眼睛按鈕
        eye_btn = QPushButton("👁")
        eye_btn.setFixedSize(S(26), S(26))
        eye_btn.setStyleSheet(self._icon_btn_style())
        eye_btn.clicked.connect(self._toggle_pwd)
        bot_row.addWidget(eye_btn)

        # 複製按鈕
        self.copy_btn = QPushButton("複製")
        self.copy_btn.setFixedHeight(S(26))
        self.copy_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: 1px solid rgba(0,255,136,0.3);
                border-radius: {S(3)}px;
                color: {CP['green_dim']};
                font-family: 'Courier New', monospace;
                font-size: {S(10)}px;
                padding: 0 {S(8)}px;
            }}
            QPushButton:hover {{ background: rgba(0,255,136,0.1); color: {CP['green']}; }}
        """)
        self.copy_btn.clicked.connect(self._on_copy)
        bot_row.addWidget(self.copy_btn)

        # 編輯按鈕
        edit_btn = QPushButton("編輯")
        edit_btn.setFixedHeight(S(26))
        edit_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: 1px solid rgba(0,168,176,0.3);
                border-radius: {S(3)}px;
                color: {CP['cyan_dim']};
                font-family: 'Courier New', monospace;
                font-size: {S(10)}px;
                padding: 0 {S(8)}px;
            }}
            QPushButton:hover {{ background: rgba(0,245,255,0.08); color: {CP['cyan']}; }}
        """)
        edit_btn.clicked.connect(lambda: self.edit_clicked.emit(self.entry))
        bot_row.addWidget(edit_btn)

        outer.addLayout(bot_row)

    def _icon_btn_style(self):
        return f"""
            QPushButton {{
                background: transparent;
                border: 1px solid {CP['border']};
                border-radius: {S(3)}px;
                color: {CP['muted']};
                font-size: {S(12)}px;
                padding: 0;
            }}
            QPushButton:hover {{ background: rgba(0,245,255,0.08); color: {CP['cyan']}; }}
        """

    def _toggle_pwd(self):
        self._pwd_visible = not self._pwd_visible
        if self._pwd_visible:
            self.pwd_lbl.setText(self.entry.get("password", ""))
            self.pwd_lbl.setStyleSheet(f"""
                color: {CP['green']};
                font-family: 'Courier New', monospace;
                font-size: {S(11)}px;
            """)
        else:
            self.pwd_lbl.setText("●●●●●●●●")
            self.pwd_lbl.setStyleSheet(f"""
                color: {CP['muted']};
                font-family: 'Courier New', monospace;
                font-size: {S(11)}px;
            """)

    def _on_copy(self):
        self.copy_clicked.emit(self.entry.get("password", ""), self)

    def set_copied_state(self, countdown: int):
        """顯示倒數計時"""
        if countdown > 0:
            self.copy_btn.setText(f"{countdown}s")
            self.copy_btn.setStyleSheet(f"""
                QPushButton {{
                    background: rgba(0,255,136,0.1);
                    border: 1px solid rgba(0,255,136,0.5);
                    border-radius: {S(3)}px;
                    color: {CP['green']};
                    font-family: 'Courier New', monospace;
                    font-size: {S(10)}px;
                    padding: 0 {S(8)}px;
                }}
            """)
        else:
            self.copy_btn.setText("複製")
            self.copy_btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    border: 1px solid rgba(0,255,136,0.3);
                    border-radius: {S(3)}px;
                    color: {CP['green_dim']};
                    font-family: 'Courier New', monospace;
                    font-size: {S(10)}px;
                    padding: 0 {S(8)}px;
                }}
                QPushButton:hover {{ background: rgba(0,255,136,0.1); color: {CP['green']}; }}
            """)


# ────────────────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self, data: dict):
        super().__init__()
        self._data           = data
        self._undo_stack: list[dict] = []
        self._current_cat    = "全部"
        self._search_text    = ""
        self._clipboard_card = None
        self._clipboard_countdown = 0

        self.setWindowTitle("VaultMe")
        self.setMinimumSize(S(860), S(580))
        self.setStyleSheet(get_stylesheet())

        self._build_ui()
        self._refresh_list()
        self._setup_timers()

    # ── UI 建構 ────────────────────────────────────────────────────────
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_sidebar())
        root.addWidget(self._build_main_area(), 1)

    def _build_sidebar(self):
        sidebar = QFrame()
        sidebar.setFixedWidth(S(170))
        sidebar.setStyleSheet(f"""
            QFrame {{
                background-color: {CP['panel']};
                border: none;
                border-right: 1px solid {CP['border']};
            }}
        """)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, S(20), 0, S(16))
        layout.setSpacing(0)

        logo = QLabel("🔐 VAULT ME")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setStyleSheet(f"""
            color: {CP['cyan']};
            font-family: 'Courier New', monospace;
            font-size: {S(13)}px;
            font-weight: bold;
            letter-spacing: {S(3)}px;
            padding: 0 {S(8)}px {S(16)}px;
        """)
        layout.addWidget(logo)

        sep = QLabel()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {CP['border']}; margin: 0 {S(12)}px;")
        layout.addWidget(sep)
        layout.addSpacing(S(8))

        self._cat_buttons: dict[str, QPushButton] = {}
        for cat in CATEGORIES:
            icon = CAT_ICONS.get(cat, "")
            color = CATEGORY_COLORS.get(cat, CP["cyan"])
            btn = QPushButton(f"  {icon}  {cat}")
            btn.setObjectName("category_btn")
            btn.setFixedHeight(S(38))
            btn.setCheckable(False)
            btn.setProperty("active", cat == self._current_cat)
            btn.clicked.connect(lambda _, c=cat: self._select_category(c))
            layout.addWidget(btn)
            self._cat_buttons[cat] = btn

        layout.addStretch()

        # 設定按鈕
        settings_btn = QPushButton("  ⚙  設定")
        settings_btn.setObjectName("category_btn")
        settings_btn.setFixedHeight(S(38))
        settings_btn.clicked.connect(self._show_settings)
        layout.addWidget(settings_btn)

        return sidebar

    def _build_main_area(self):
        area = QWidget()
        area.setStyleSheet(f"background-color: {CP['bg']};")
        layout = QVBoxLayout(area)
        layout.setContentsMargins(S(20), S(16), S(20), 0)
        layout.setSpacing(S(12))

        # ── 頂部列 ─────────────────────────────────────────────────────
        top_row = QHBoxLayout()
        top_row.setSpacing(S(10))

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("🔍  搜尋名稱、帳號…")
        self.search_edit.setFixedHeight(S(36))
        self.search_edit.textChanged.connect(self._on_search)
        top_row.addWidget(self.search_edit, 1)

        add_btn = QPushButton("＋  新增")
        add_btn.setFixedHeight(S(36))
        add_btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(0,255,136,0.08);
                border: 1px solid rgba(0,255,136,0.35);
                border-radius: {S(4)}px;
                color: {CP['green']};
                font-family: 'Courier New', monospace;
                font-size: {S(12)}px;
                padding: 0 {S(16)}px;
                letter-spacing: 1px;
            }}
            QPushButton:hover {{ background: rgba(0,255,136,0.16); }}
        """)
        add_btn.clicked.connect(self._on_add)
        top_row.addWidget(add_btn)

        self.sync_btn = QPushButton("⟳")
        self.sync_btn.setFixedSize(S(36), S(36))
        self.sync_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: 1px solid {CP['border']};
                border-radius: {S(4)}px;
                color: {CP['muted']};
                font-size: {S(16)}px;
                padding: 0;
            }}
            QPushButton:hover {{ border-color: {CP['cyan_dim']}; color: {CP['cyan']}; }}
        """)
        self.sync_btn.setToolTip("手動同步雲端")
        self.sync_btn.clicked.connect(self._manual_sync)
        top_row.addWidget(self.sync_btn)

        layout.addLayout(top_row)

        # ── 計數列 ─────────────────────────────────────────────────────
        count_row = QHBoxLayout()
        self.count_lbl = QLabel()
        self.count_lbl.setStyleSheet(f"color: {CP['muted']}; font-size: {S(11)}px; letter-spacing: 1px;")
        count_row.addWidget(self.count_lbl)
        count_row.addStretch()

        self.undo_btn = QPushButton("↩  復原刪除")
        self.undo_btn.setFixedHeight(S(26))
        self.undo_btn.setVisible(False)
        self.undo_btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(255,149,0,0.08);
                border: 1px solid rgba(255,149,0,0.3);
                border-radius: {S(3)}px;
                color: {CP['orange']};
                font-family: 'Courier New', monospace;
                font-size: {S(10)}px;
                padding: 0 {S(10)}px;
            }}
            QPushButton:hover {{ background: rgba(255,149,0,0.15); }}
        """)
        self.undo_btn.clicked.connect(self._on_undo)
        count_row.addWidget(self.undo_btn)

        layout.addLayout(count_row)

        # ── 項目列表（可捲動）─────────────────────────────────────────
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.list_widget = QWidget()
        self.list_widget.setStyleSheet("background: transparent;")
        self.list_layout = QVBoxLayout(self.list_widget)
        # 右邊距預留滾輪條空間，避免卡片被覆蓋（S(14) 略大於最大縮放下的 S(10) 滾輪寬）
        self.list_layout.setContentsMargins(0, 0, S(14), S(12))
        self.list_layout.setSpacing(S(6))
        self.list_layout.addStretch()

        self.scroll_area.setWidget(self.list_widget)
        layout.addWidget(self.scroll_area, 1)

        # ── 狀態列 ─────────────────────────────────────────────────────
        status_frame = QFrame()
        status_frame.setFixedHeight(S(28))
        status_frame.setStyleSheet(f"""
            QFrame {{
                background: {CP['panel']};
                border-top: 1px solid {CP['border']};
                border-left: none; border-right: none; border-bottom: none;
            }}
        """)
        status_row = QHBoxLayout(status_frame)
        status_row.setContentsMargins(S(12), 0, S(12), 0)
        status_row.setSpacing(S(10))

        self.sync_dot = QLabel("●")
        self.sync_dot.setStyleSheet(f"color: {CP['muted']}; font-size: {S(9)}px;")
        status_row.addWidget(self.sync_dot)

        self.status_lbl = QLabel("就緒")
        self.status_lbl.setStyleSheet(f"color: {CP['muted']}; font-size: {S(10)}px; letter-spacing: 1px;")
        status_row.addWidget(self.status_lbl)
        status_row.addStretch()

        push_allowed = data_manager.is_cloud_push_allowed()
        guard_lbl = QLabel("雲端推送：已啟用" if push_allowed else "雲端推送：已停用（防呆保護）")
        guard_lbl.setStyleSheet(f"color: {'#00aa55' if push_allowed else CP['orange']}; font-size: {S(10)}px;")
        status_row.addWidget(guard_lbl)

        layout.addWidget(status_frame)
        layout.setContentsMargins(S(20), S(16), S(20), 0)

        return area

    # ── 分類 & 搜尋 ────────────────────────────────────────────────────
    def _select_category(self, cat: str):
        self._current_cat = cat
        for c, btn in self._cat_buttons.items():
            btn.setProperty("active", c == cat)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self._refresh_list()

    def _on_search(self, text: str):
        self._search_text = text.lower()
        self._refresh_list()

    def _filtered_entries(self):
        entries = self._data.get("entries", [])
        if self._current_cat != "全部":
            entries = [e for e in entries if e.get("category") == self._current_cat]
        if self._search_text:
            entries = [e for e in entries
                       if self._search_text in e.get("name", "").lower()
                       or self._search_text in e.get("account", "").lower()
                       or self._search_text in e.get("note", "").lower()
                       or self._search_text in e.get("owner", "").lower()]
        return entries

    def _refresh_list(self):
        # 清除舊卡片（保留末尾的 stretch）
        while self.list_layout.count() > 1:
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        entries = self._filtered_entries()
        self.count_lbl.setText(f"{len(entries)} 筆")

        if not entries:
            empty = QLabel("— 沒有項目 —")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet(f"color: {CP['border']}; font-size: {S(13)}px; padding: {S(40)}px;")
            self.list_layout.insertWidget(0, empty)
            return

        for entry in reversed(sorted(entries, key=lambda e: e.get("name", ""))):
            card = EntryCard(entry)
            card.edit_clicked.connect(self._on_edit)
            card.copy_clicked.connect(self._on_copy_password)
            self.list_layout.insertWidget(0, card)

    # ── CRUD ───────────────────────────────────────────────────────────
    def _on_add(self):
        dlg = EntryDialog(self, mode="add")
        if dlg.exec() == EntryDialog.DialogCode.Accepted:
            entry = dlg.get_result()
            if entry:
                self._data.setdefault("entries", []).append(entry)
                self._save()
                self._refresh_list()
                self._set_status("已新增", CP["green"])

    def _on_edit(self, entry: dict):
        dlg = EntryDialog(self, entry=entry, mode="edit")
        result = dlg.exec()

        if result == EntryDialog.DialogCode.Accepted:
            updated = dlg.get_result()
            if updated:
                entries = self._data.get("entries", [])
                for i, e in enumerate(entries):
                    if e["id"] == updated["id"]:
                        entries[i] = updated
                        break
                self._save()
                self._refresh_list()
                self._set_status("已更新", CP["cyan"])

        elif result == 2:   # 刪除
            self._undo_stack.append(dict(entry))
            self._data["entries"] = [e for e in self._data.get("entries", [])
                                     if e["id"] != entry["id"]]
            self._save()
            self._refresh_list()
            self.undo_btn.setVisible(True)
            self._set_status(f"已刪除「{entry.get('name')}」", CP["orange"])

    def _on_undo(self):
        if not self._undo_stack:
            return
        entry = self._undo_stack.pop()
        self._data.setdefault("entries", []).append(entry)
        self._save()
        self._refresh_list()
        if not self._undo_stack:
            self.undo_btn.setVisible(False)
        self._set_status(f"已復原「{entry.get('name')}」", CP["green"])

    # ── 複製密碼（30 秒清除）─────────────────────────────────────────
    def _on_copy_password(self, password: str, card: EntryCard):
        try:
            pyperclip.copy(password)
        except Exception:
            pass

        # 重置上一張卡的計時
        if self._clipboard_card and self._clipboard_card is not card:
            self._clipboard_card.set_copied_state(0)

        self._clipboard_card      = card
        self._clipboard_countdown = CLIPBOARD_TTL
        card.set_copied_state(self._clipboard_countdown)

    def _tick_clipboard(self):
        if self._clipboard_countdown <= 0:
            return
        self._clipboard_countdown -= 1
        if self._clipboard_card:
            self._clipboard_card.set_copied_state(self._clipboard_countdown)
        if self._clipboard_countdown == 0:
            try:
                pyperclip.copy("")
            except Exception:
                pass
            self._clipboard_card = None

    # ── 同步 ───────────────────────────────────────────────────────────
    def _save(self):
        def _on_blocked(local_count, cloud_count):
            reply = QMessageBox.warning(
                self,
                "⚠ 防呆警告",
                f"本地資料筆數（{local_count}）\n遠少於雲端資料筆數（{cloud_count}）。\n\n"
                f"這可能代表資料遺失。確定要覆蓋雲端嗎？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            return reply == QMessageBox.StandardButton.Yes

        data_manager.save_data_with_guard(self._data, on_blocked=_on_blocked)

    def _manual_sync(self):
        self._set_status("同步中…", CP["gold"])
        self.sync_btn.setEnabled(False)

        from vaultme.core.data_manager import SyncWorker
        self._sync_worker = SyncWorker()
        self._sync_worker.sync_done.connect(self._on_sync_done)
        self._sync_worker.run_sync(self._data)

    def _auto_sync(self):
        from vaultme.core.data_manager import SyncWorker
        worker = SyncWorker()
        worker.sync_done.connect(lambda ok, msg: None)
        worker.run_sync(self._data)

    def _on_sync_done(self, ok: bool, msg: str):
        self.sync_btn.setEnabled(True)
        color = CP["green"] if ok else CP["orange"]
        self._set_status(msg, color)
        # 更新同步指示燈
        self.sync_dot.setStyleSheet(f"color: {'#00ff88' if ok else CP['orange']}; font-size: {S(9)}px;")

    def _set_status(self, msg: str, color: str = None):
        self.status_lbl.setText(msg)
        if color:
            self.status_lbl.setStyleSheet(f"color: {color}; font-size: {S(10)}px; letter-spacing: 1px;")

    # ── 計時器 ─────────────────────────────────────────────────────────
    def _setup_timers(self):
        # 剪貼簿倒數（每秒）
        self._clip_timer = QTimer(self)
        self._clip_timer.timeout.connect(self._tick_clipboard)
        self._clip_timer.start(1000)

        # 背景雲端同步（5 分鐘）
        self._sync_timer = QTimer(self)
        self._sync_timer.timeout.connect(self._auto_sync)
        self._sync_timer.start(SYNC_INTERVAL)

    # ── 設定 ───────────────────────────────────────────────────────────
    def _show_settings(self):
        from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout,
                                     QLabel, QPushButton, QFrame)
        from vaultme import theme as _theme

        dlg = QDialog(self)
        dlg.setWindowTitle("設定")
        dlg.setMinimumWidth(S(460))
        dlg.setStyleSheet(f"""
            QDialog {{ background: #07101e; border: 1px solid {CP['cyan_dim']};
                       border-radius: {S(8)}px; }}
            QLabel  {{ color: {CP['text']}; font-size: {S(12)}px; background: transparent; }}
            QLabel#section {{ color: {CP['cyan_dim']}; font-size: {S(10)}px;
                              letter-spacing: 2px; font-weight: bold; }}
            QLabel#dim {{ color: {CP['muted']}; font-size: {S(11)}px; }}
        """)
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(S(28), S(24), S(28), S(20))
        lay.setSpacing(S(14))

        # ── 標題 ───────────────────────────────────────────────────
        title_lbl = QLabel("⚙  設定")
        title_lbl.setStyleSheet(f"""
            color: {CP['cyan']}; font-family: 'Courier New', monospace;
            font-size: {S(15)}px; font-weight: bold; letter-spacing: 2px;
        """)
        lay.addWidget(title_lbl)

        def _sep():
            s = QFrame(); s.setFixedHeight(1)
            s.setStyleSheet(f"background: {CP['border']}; border: none;")
            lay.addWidget(s)

        _sep()

        # ── 字體縮放 ───────────────────────────────────────────────
        lbl_scale = QLabel("介面縮放")
        lbl_scale.setObjectName("section")
        lay.addWidget(lbl_scale)

        cfg          = data_manager.load_config()
        current_ui   = float(cfg.get("ui_scale", _theme.SCALE))
        PRESETS      = [(0.8, "80%"), (1.0, "100%"), (1.25, "125%"),
                        (1.5, "150%"), (1.75, "175%")]

        scale_row = QHBoxLayout()
        scale_row.setSpacing(S(6))

        notice_lbl = QLabel()
        notice_lbl.setObjectName("dim")

        def _make_scale_btns(selected_val):
            # 清除舊按鈕
            while scale_row.count():
                item = scale_row.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            for val, label in PRESETS:
                is_sel = abs(val - selected_val) < 0.01
                btn = QPushButton(label)
                btn.setFixedHeight(S(32))
                if is_sel:
                    btn.setStyleSheet(f"""
                        QPushButton {{
                            background: rgba(0,245,255,0.18);
                            border: 1px solid {CP['cyan']};
                            border-radius: {S(4)}px;
                            color: {CP['cyan']};
                            font-family: 'Courier New', monospace;
                            font-size: {S(11)}px; font-weight: bold;
                            padding: 0 {S(10)}px;
                        }}
                    """)
                else:
                    btn.setStyleSheet(f"""
                        QPushButton {{
                            background: transparent;
                            border: 1px solid {CP['border']};
                            border-radius: {S(4)}px;
                            color: {CP['muted']};
                            font-family: 'Courier New', monospace;
                            font-size: {S(11)}px;
                            padding: 0 {S(10)}px;
                        }}
                        QPushButton:hover {{
                            border-color: {CP['cyan_dim']}; color: {CP['text']};
                        }}
                    """)

                def _make_handler(sv):
                    def handler():
                        c = data_manager.load_config()
                        c["ui_scale"] = sv
                        data_manager.save_config(c)
                        notice_lbl.setText(
                            f"✓ 已儲存（{sv*100:.0f}%），重新啟動後生效")
                        notice_lbl.setStyleSheet(
                            f"color: {CP['green']}; font-size: {S(11)}px;")
                        _make_scale_btns(sv)
                    return handler

                btn.clicked.connect(_make_handler(val))
                scale_row.addWidget(btn)
            scale_row.addStretch()

        _make_scale_btns(current_ui)
        lay.addLayout(scale_row)
        lay.addWidget(notice_lbl)

        _sep()

        # ── 資料資訊 ───────────────────────────────────────────────
        lbl_data = QLabel("資料與雲端")
        lbl_data.setObjectName("section")
        lay.addWidget(lbl_data)

        for text in [
            f"本地資料：{data_manager.DATA_FILE}",
            f"雲端設定：{data_manager.CLOUD_CFG}",
            "雲端推送：" + ("已啟用 ✓" if data_manager.is_cloud_push_allowed()
                           else "已停用（防呆保護）"),
        ]:
            lbl = QLabel(text)
            lbl.setObjectName("dim")
            lbl.setWordWrap(True)
            lay.addWidget(lbl)

        _sep()

        # ── 關閉 ───────────────────────────────────────────────────
        close_btn = QPushButton("關閉")
        close_btn.setFixedHeight(S(36))
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; border: 1px solid {CP['border']};
                border-radius: {S(4)}px; color: {CP['muted']};
                font-family: 'Courier New', monospace; font-size: {S(12)}px;
            }}
            QPushButton:hover {{ background: rgba(255,255,255,0.04); color: {CP['text']}; }}
        """)
        close_btn.clicked.connect(dlg.accept)
        lay.addWidget(close_btn)

        dlg.exec()

    # ── 快捷鍵 ─────────────────────────────────────────────────────────
    def keyPressEvent(self, event):
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            if event.key() == Qt.Key.Key_Z:
                self._on_undo()
                return
            if event.key() == Qt.Key.Key_N:
                self._on_add()
                return
        super().keyPressEvent(event)
