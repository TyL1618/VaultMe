# -*- mode: python ; coding: utf-8 -*-
# VaultMe PyInstaller spec
# 打包指令：pyinstaller VaultMe.spec
# 輸出位置：dist\VaultMe.exe（單一執行檔，無主控台）

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        # 圖示打包進去，讓視窗 / 工具列圖示在 EXE 中也能顯示
        ('icon.ico', '.'),
    ],
    hiddenimports=[
        # 主套件
        'vaultme',
        'vaultme.ui',
        'vaultme.ui.main_window',
        'vaultme.ui.login_dialog',
        'vaultme.ui.entry_dialog',
        'vaultme.core',
        'vaultme.core.data_manager',
        'vaultme.crypto',
        'vaultme.theme',
        'vaultme.app',
        # cryptography (Rust 後端需要明確列出)
        'cryptography.hazmat.backends.openssl',
        'cryptography.hazmat.bindings._rust',
        'cryptography.hazmat.bindings._rust.openssl',
        # requests / certifi（凍結環境 SSL 憑證）
        'requests',
        'certifi',
        # 剪貼簿
        'pyperclip',
        # PyQt6 外掛（部分版本需要）
        'PyQt6.sip',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'PyQt5', 'PySide2', 'PySide6',   # qtpy 會誤把 PyQt5 拉進來，跟 PyQt6 衝突導致打包中止
        # 不需要的大型套件
        'tkinter',
        'matplotlib',
        'numpy',
        'pandas',
        'PIL',
        'scipy',
        'IPython',
        'jupyter',
        'notebook',
        'pytest',
        'setuptools',
        'pkg_resources',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher,
)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='VaultMe',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,         # 未簽章 exe 被 UPX 壓過容易被防毒誤判
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,     # 不顯示黑色命令列視窗
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico',   # EXE 檔案圖示
)
