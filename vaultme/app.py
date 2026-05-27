"""
app.py - VaultMe 應用程式進入點

啟動流程：
  第一次使用 → RegisterDialog（設定密碼 + 提示）
  之後每次   → LoginDialog（輸入密碼，可查提示）
"""
import sys

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtGui import QScreen

from vaultme import theme
from vaultme.ui.login_dialog import LoginDialog, RegisterDialog
from vaultme.ui.main_window import MainWindow
from vaultme.core import data_manager

MAX_ATTEMPTS = 5


def run():
    app = QApplication(sys.argv)
    app.setApplicationName("VaultMe")

    # ── DPI 縮放 ─────────────────────────────────────────────────────
    screen = app.primaryScreen()
    scale  = max(0.8, min(2.5, screen.logicalDotsPerInch() / 96.0))
    theme.set_scale(scale)
    app.setStyleSheet(theme.get_stylesheet())

    # ── 第一次使用：設定主密碼 ────────────────────────────────────────
    if data_manager.is_first_time():
        dlg = RegisterDialog()
        _center(dlg, screen)
        if dlg.exec() != RegisterDialog.DialogCode.Accepted:
            sys.exit(0)
        password = dlg.get_password()
        data = data_manager.load_data(password)
        data_manager.save_data(data)   # 立刻建立 vault.enc，確保下次進入解鎖畫面

    # ── 回訪：輸入主密碼解鎖 ─────────────────────────────────────────
    else:
        data     = None
        error    = ""
        for _ in range(MAX_ATTEMPTS):
            dlg = LoginDialog(error_msg=error)
            _center(dlg, screen)
            if dlg.exec() != LoginDialog.DialogCode.Accepted:
                sys.exit(0)
            try:
                data = data_manager.load_data(dlg.get_password())
                break
            except ValueError as e:
                error = str(e)

        if data is None:
            QMessageBox.critical(None, "VaultMe", "密碼錯誤次數過多，程式結束。")
            sys.exit(1)

    # ── 開啟主視窗 ───────────────────────────────────────────────────
    window = MainWindow(data)
    w, h   = theme.S(920), theme.S(620)
    rect   = screen.availableGeometry()
    window.resize(w, h)
    window.move(rect.x() + (rect.width() - w) // 2,
                rect.y() + (rect.height() - h) // 2)
    window.show()
    sys.exit(app.exec())


def _center(widget, screen: QScreen):
    rect = screen.availableGeometry()
    hint = widget.sizeHint()
    widget.move(
        rect.x() + (rect.width()  - hint.width())  // 2,
        rect.y() + (rect.height() - hint.height()) // 2,
    )
