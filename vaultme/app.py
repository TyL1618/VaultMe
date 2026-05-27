"""
app.py - VaultMe 應用程式進入點

啟動流程：
  第一次使用 → RegisterDialog（設定密碼 + 提示）
  之後每次   → LoginDialog（輸入密碼，可查提示）
"""
import sys

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtGui import QScreen, QIcon

from vaultme import theme
from vaultme.ui.login_dialog import LoginDialog, RegisterDialog
from vaultme.ui.main_window import MainWindow
from vaultme.core import data_manager

MAX_ATTEMPTS = 5


def run():
    app = QApplication(sys.argv)
    app.setApplicationName("VaultMe")

    # ── 應用程式圖示（工具列 + 視窗左上角）────────────────────────────
    import os
    _icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "icon.ico")
    if os.path.exists(_icon_path):
        app.setWindowIcon(QIcon(_icon_path))

    # ── DPI 縮放 ─────────────────────────────────────────────────────
    screen = app.primaryScreen()
    scale  = max(0.8, min(2.5, screen.logicalDotsPerInch() / 96.0))
    theme.set_scale(scale)
    app.setStyleSheet(theme.get_stylesheet())

    # ── 判斷是否為全新安裝 ───────────────────────────────────────────
    # 有 vm_cloud.json 或有 vault.enc → 是回訪用戶，直接顯示解鎖畫面
    # 兩者都沒有 → 才是真正第一次，顯示設定畫面
    cloud_configured = bool(data_manager._load_cloud_cfg()[0])
    truly_new = data_manager.is_first_time() and not cloud_configured

    if truly_new:
        # ── 全新安裝：設定主密碼 ──────────────────────────────────────
        dlg = RegisterDialog()
        _center(dlg, screen)
        if dlg.exec() != RegisterDialog.DialogCode.Accepted:
            sys.exit(0)
        password = dlg.get_password()
        data = data_manager.load_data(password)
        data_manager.save_data(data)   # 立刻建立 vault.enc，確保下次進入解鎖畫面

    else:
        # ── 回訪 / 新裝置：輸入既有主密碼解鎖 ───────────────────────
        data  = None
        error = ""
        # 新裝置提示（有 vm_cloud.json 但沒有 vault.enc）
        if data_manager.is_first_time() and cloud_configured:
            error = "新裝置：請輸入你的主密碼，將從雲端恢復資料"

        for _ in range(MAX_ATTEMPTS):
            dlg = LoginDialog(error_msg=error)
            _center(dlg, screen)
            if dlg.exec() != LoginDialog.DialogCode.Accepted:
                sys.exit(0)
            try:
                data = data_manager.load_data(dlg.get_password())
                # 新裝置第一次登入成功 → 立刻寫入 vault.enc
                if not data_manager._load_local_blob():
                    data_manager.save_data(data)
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
