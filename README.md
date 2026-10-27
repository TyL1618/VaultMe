# 🔐 VaultMe

個人密碼管理器，支援 AES-256-GCM 加密、Supabase 雲端跨裝置同步、PyQt6 桌面版與 PWA 手機版。

## 功能

- **強加密**：AES-256-GCM + PBKDF2（260,000 次），主密碼永不離開裝置
- **跨裝置同步**：Supabase 雲端，密文同步（明文永不上雲）
- **桌面版**：PyQt6 Cyberpunk 風格 GUI，支援 DPI 縮放
- **手機版**：PWA（可安裝至主畫面），支援指紋解鎖
- **分類管理**：銀行 / 社群 / Email / 娛樂 / 購物 / 政府 / 軟體 / 其他
- **持有人欄位**：多人帳號管理（家人共用）
- **自訂欄位**：每筆記錄可新增任意 label + value
- **防呆保護**：本地筆數 < 雲端 50% 時阻止推送
- **剪貼簿自動清除**：複製密碼 30 秒後自動清除

## 安裝（桌面版）

```bash
pip install -r requirements.txt
python main.py
```

## 打包成 EXE

```bash
build_exe.bat   # 內部跑 pyinstaller VaultMe.spec --noconfirm --clean
# 輸出：dist\VaultMe.exe
```

## 雲端設定

在 `%AppData%\VaultMe\` 建立 `vm_cloud.json`：

```json
{
  "supabase_url": "https://xxxx.supabase.co",
  "supabase_key": "eyJ...",
  "email": "your@email.com",
  "password": "yourpassword"
}
```

## 手機版

GitHub Pages：https://TyL1618.github.io/VaultMe/

## 資料位置

| 檔案 | 路徑 | 說明 |
|------|------|------|
| `vault.enc` | `%AppData%\VaultMe\` | 加密密碼庫（本機備份） |
| `vault.hint` | `%AppData%\VaultMe\` | 主密碼提示（明文，僅本機） |
| `vm_cloud.json` | `%AppData%\VaultMe\` | Supabase 連線設定（勿外洩） |
| `vaultme_config.json` | `%AppData%\VaultMe\` | UI 設定（縮放比例等） |
