# VaultMe — 技術文件 (DEVDOC)

## 目錄
1. [架構概覽](#架構概覽)
2. [檔案結構](#檔案結構)
3. [加密機制](#加密機制)
4. [資料格式](#資料格式)
5. [模組說明](#模組說明)
6. [Supabase 設定](#supabase-設定)
7. [跨裝置同步流程](#跨裝置同步流程)
8. [安全模型](#安全模型)
9. [PWA 手機版](#pwa-手機版)
10. [UI 縮放系統](#ui-縮放系統)
11. [打包（PyInstaller）](#打包pyinstaller)
12. [已知限制](#已知限制)

---

## 架構概覽

```
桌面版 (PyQt6)                    手機版 (PWA)
┌──────────────────┐              ┌──────────────────┐
│  vaultme/app.py  │              │  docs/index.html │
│  UI (PyQt6)      │              │  Web Crypto API  │
│  data_manager.py │              │  WebAuthn (指紋) │
│  crypto.py       │              └────────┬─────────┘
└────────┬─────────┘                       │
         │  AES-256-GCM 密文               │
         └──────────────┬──────────────────┘
                        │
               ┌────────▼────────┐
               │   Supabase      │
               │  (密文儲存)     │
               └─────────────────┘
```

主密碼永遠只存在使用者腦中，**任何裝置上都不儲存、不傳輸**。

---

## 檔案結構

```
VaultMe/
├── main.py                    # 程式進入點
├── requirements.txt
├── VaultMe.spec               # PyInstaller 打包設定
├── icon.ico                   # 多尺寸圖示 (16/24/32/48/64/128/256px)，由 tools/make_icon.py 產生
├── tools/
│   └── make_icon.py           # 產生全部圖示（桌面 ico + PWA png + favicon）；改設計只改這支再重跑
├── README.md
├── DEVDOC.md
├── vaultme/
│   ├── app.py                 # 啟動流程、DPI 縮放、登入/註冊判斷
│   ├── crypto.py              # 加密/解密核心
│   ├── theme.py               # 色盤、樣式表、S() 縮放函數
│   ├── core/
│   │   └── data_manager.py    # 本地讀寫 + Supabase 雲端同步
│   └── ui/
│       ├── main_window.py     # 主視窗（列表、側欄、設定）
│       ├── entry_dialog.py    # 新增/編輯項目對話框
│       └── login_dialog.py    # 登入/首次註冊對話框
└── docs/                      # GitHub Pages (PWA)
    ├── index.html             # PWA 單頁應用（含 JS）
    ├── sw.js                  # Service Worker（離線快取）
    ├── manifest.json          # PWA 安裝設定
    ├── icon-192.png           # 以下圖示皆由 tools/make_icon.py 產生
    ├── icon-512.png           # 滿版不透明底，內容在 maskable 安全區內（any / maskable 共用）
    ├── apple-touch-icon.png   # iOS 主畫面（180px）
    └── favicon.ico            # 瀏覽器分頁
```

### 資料目錄（`%AppData%\VaultMe\`，不進 git）

| 檔案 | 說明 |
|------|------|
| `vault.enc` | 本機加密備份（JSON 密文字串） |
| `vault.hint` | 主密碼提示（明文，僅本機） |
| `vm_cloud.json` | Supabase 連線設定 |
| `vaultme_config.json` | UI 設定（`ui_scale` 等） |

---

## 加密機制

### 金鑰推導
```
主密碼 (str)
    │
    ▼  PBKDF2-HMAC-SHA256
    │  iterations = 260,000
    │  salt = 32 bytes random (首次) / 從 blob 讀取 (後續)
    │  key_length = 32 bytes
    ▼
AES-256 金鑰
```

### 加密流程（`crypto.py`）
```python
encrypt(plaintext, password, salt=None) -> str
# salt=None → 產生新 salt（首次）
# salt=bytes → 重用（更新資料時，確保跨裝置能解密）

# 輸出格式（JSON 字串）：
{"salt": "<base64>", "nonce": "<base64>", "ciphertext": "<base64>"}
```

### 解密流程
```python
decrypt(blob_str, password) -> str
# 密碼錯誤 → AES-GCM InvalidTag → 拋出 ValueError("密碼錯誤或資料已損毀")
# ValueError 即是驗證機制（密碼永不儲存）
```

### Salt 重用策略
- 首次加密：產生隨機 salt，快取至 `_cached_salt`
- 後續加密：重用同一個 salt（確保其他裝置用相同主密碼 + 相同 salt 能解密）
- **更換主密碼**：呼叫 `change_master_password()` 時清除 `_cached_salt`，強制產生新 salt

---

## 資料格式

### vault 資料結構（解密後的 dict）
```python
{
    "entries": [
        {
            "id":           str,   # UUID
            "category":     str,   # 銀行/社群/Email/娛樂/購物/政府/軟體/其他
            "name":         str,   # 項目名稱（必填）
            "account":      str,   # 帳號/Email/使用者名稱
            "owner":        str,   # 持有人（選填，多人共用時使用）
            "password":     str,   # 密碼（必填）
            "url":          str,   # 網址（選填）
            "note":         str,   # 備註（選填）
            "extra_fields": [      # 自訂欄位
                {"label": str, "value": str}
            ],
            "updated_at":   str,   # ISO 8601 UTC 時間戳
        }
    ],
    "_updated": str,               # vault 最後更新時間（用於衝突解決）
}
```

### vaultme_config.json
```json
{
    "ui_scale": 1.25
}
```

### vm_cloud.json（不進 git）
```json
{
    "supabase_url": "https://xxxx.supabase.co",
    "supabase_key": "eyJ...",
    "email": "user@email.com",
    "password": "supabase_auth_password"
}
```

---

## 模組說明

### `crypto.py`
| 函數 | 說明 |
|------|------|
| `encrypt(plaintext, password, salt=None)` | 加密，回傳 JSON blob 字串 |
| `decrypt(blob_str, password)` | 解密，密碼錯誤拋 ValueError |
| `derive_key(password, salt)` | PBKDF2 金鑰推導 |
| `extract_salt(blob_str)` | 從 blob 取出 salt bytes |

### `data_manager.py`
| 函數/變數 | 說明 |
|------|------|
| `DATA_DIR` | `%AppData%\VaultMe\` |
| `DATA_FILE` | vault.enc 路徑 |
| `_master_password` | 模組級全域，登入後設定 |
| `_cloud_push_allowed` | 防呆旗標，False = 禁止推送 |
| `_cached_salt` | 重用 salt，跨裝置一致性 |
| `is_first_time()` | vault.enc 不存在 → True |
| `load_data(master_pwd)` | 讀本地 + 雲端，取較新 |
| `save_data(data)` | 寫本地 + 非同步推雲端 |
| `save_data_with_guard(data, on_blocked)` | 加 50% 筆數防呆保護 |
| `change_master_password(data, new_password)` | 重設主密碼，強制新 salt |
| `load_config() / save_config(cfg)` | 讀寫 vaultme_config.json |
| `SyncWorker` | 背景同步 QObject，發 `sync_done` 訊號 |

### `app.py` 啟動流程
```
QApplication 建立
    │
    ├── 讀 vaultme_config.json → 決定 UI 縮放
    │
    ├── 判斷是否全新安裝
    │     is_first_time() AND NOT cloud_configured
    │     ├── True  → RegisterDialog（設定主密碼 + 提示）
    │     └── False → LoginDialog（輸入主密碼，最多 5 次）
    │               └── 新裝置（有 vm_cloud.json 無 vault.enc）→ 顯示提示
    │
    └── MainWindow(data)
```

### `theme.py`
- `CP` dict：色盤（bg / panel / cyan / pink / green / muted / border...）
- `CATEGORY_COLORS` dict：各分類顏色（8 個）
- `SCALE`：全域縮放係數，由 `set_scale()` 設定
- `S(n)`：整數縮放（px 尺寸用）
- `Sf(n)`：浮點縮放（字體 pt 用）
- `get_stylesheet()`：回傳完整 Qt 樣式表
- `get_dialog_style()`：對話框專用樣式
- `CpPanel`：帶有色條頂邊的 QFrame 元件

### `main_window.py`
- `EntryCard`：單筆密碼卡片（3 行：標題 / 帳號 / 操作）
  - 分類 badge、持有人 badge（👤）
  - 顯示/隱藏密碼、複製（30 秒倒數清除）、編輯
- `MainWindow`：
  - 左側欄：分類篩選（9 個含全部）
  - 右側：搜尋 + 卡片列表（可搜尋 name/account/note/owner）
  - 底部狀態列：同步指示燈
  - Ctrl+Z 復原刪除、Ctrl+N 新增
  - 5 分鐘自動背景同步
  - 設定對話框：UI 縮放 / 更改主密碼 / 資料路徑

### `entry_dialog.py`
- `ExtraFieldRow`：動態 label+value 自訂欄位列
- `EntryDialog(mode='add'|'edit')`：
  - 欄位：名稱* / 分類 / 帳號 / 持有人 / 密碼* / 網址 / 備註 / 自訂欄位
  - 刪除回傳 `done(2)`（與 Accepted 區分）

### `login_dialog.py`
- `LoginDialog`：輸入主密碼解鎖，支援「忘記密碼？」查提示
- `RegisterDialog`：首次使用設定主密碼 + 提示（最短 4 字元，需確認）

---

## Supabase 設定

### Table 建立（SQL Editor）
```sql
CREATE TABLE vaultme (
    id      TEXT PRIMARY KEY,
    payload TEXT,
    updated TEXT
);

ALTER TABLE vaultme ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Own data only" ON vaultme
    FOR ALL USING (auth.uid()::text = id);
```

### 資料欄位說明
| 欄位 | 說明 |
|------|------|
| `id` | Supabase user UUID |
| `payload` | AES-256-GCM 加密的 vault JSON 字串 |
| `updated` | 最後更新時間（UTC ISO） |

---

## 跨裝置同步流程

### 登入時
```
load_data(master_pwd)
    │
    ├── _load_local(master_pwd)     → local_data（或 None）
    ├── _load_local_blob()          → 取出 salt → _cached_salt
    ├── _cloud_pull(...)            → cloud_data, uid, reachable
    │
    ├── _pick_newer(local, cloud)   → 比較 _updated 時間戳
    │
    ├── cloud_reachable=False AND cloud_configured → _cloud_push_allowed=False
    ├── best=None (全新安裝)         → _cloud_push_allowed=False
    └── 正常 → _cloud_push_allowed=True
```

### 儲存時
```
save_data(data)
    │
    ├── _save_local_data()          → 立刻寫 vault.enc
    │
    └── _cloud_push_allowed=True
            └── threading.Thread → _cloud_push()  （非同步）
```

### `_cloud_push_allowed` 防呆邏輯
| 情況 | 狀態 |
|------|------|
| 全新安裝（無 vault.enc 無 vm_cloud.json） | False |
| 有 vm_cloud.json 但本次啟動無網路 | False |
| 正常登入成功 | True |
| 本地筆數 < 雲端 50%（save_data_with_guard）| 彈警告，用戶確認才 True |

---

## 安全模型

| 威脅 | 防護 |
|------|------|
| vault.enc 被竊 | AES-256-GCM，沒有主密碼無法解密 |
| Supabase 資料庫外洩 | payload 是密文，金鑰從未上傳 |
| vm_cloud.json 被竊 | 可下載密文，但無法解密；可刪除雲端資料 |
| vault.hint 被看 | 只是提示，不是密碼 |
| 剪貼簿殘留 | 複製後 30 秒自動清除 |
| 暴力破解密碼 | PBKDF2 260,000 次迭代，大幅增加破解成本 |
| 錯誤密碼驗證 | GCM tag 驗證失敗即拋 ValueError（不儲存密碼） |
| 新裝置空資料覆蓋雲端 | `_cloud_push_allowed=False`，且有 50% 筆數保護 |
| 登入嘗試次數 | 最多 5 次，超過強制結束程式 |

---

## PWA 手機版

### 技術棧
- 純 HTML/CSS/JS 單頁應用（`docs/index.html`）
- Supabase JS SDK v2（CDN）
- Web Crypto API（PBKDF2 + AES-GCM，參數與桌面版完全相同）
- WebAuthn API（指紋解鎖，儲存 master password 至 localStorage）
- Service Worker（離線快取）

### 沉浸式全螢幕
- `manifest.json`：`display: fullscreen` + `display_override: [fullscreen, standalone, minimal-ui]`；`theme_color` / `background_color` 皆為 `#05080f`。
- `viewport-fit=cover` + `env(safe-area-inset-*)`：topbar、底部導覽、modal、toast、登入/鎖定/註冊頁都已補 safe-area padding，避免被瀏覽列瀏海/手勢列蓋住。
- 瀏覽器分頁或 standalone 模式下，每次點擊會嘗試 `requestFullscreen()` 作為備援（`tryFullscreen()`）。
- **manifest 的 `display` 在「安裝當下」就鎖定，改了不會套用到已安裝的 App——必須解除安裝再重新「加入主畫面」。**（做法移植自 WealthMatrix / CyberMind。）

### 加密相容性
Web Crypto API 的 PBKDF2 參數與 Python `cryptography` 庫完全對齊：
- iterations = 260,000
- hash = SHA-256
- salt = 32 bytes（從 Supabase payload blob 讀取）
- key = 256 bits AES-GCM

### 指紋機制
1. 手動登入成功後可選擇啟用指紋
2. 主密碼以 WebAuthn credential 包裝後存入 `localStorage`
3. 下次開啟 → 指紋驗證 → 取出主密碼 → 解密 vault

> **注意**：更改主密碼後，手機端指紋會失效（存的是舊密碼），需重新手動登入並重綁指紋。

### 分類與顏色（桌面 / 手機一致）
| 分類 | 顏色 |
|------|------|
| 銀行 | `#ffd700` 金色 |
| 社群 | `#00f5ff` 青色 |
| Email | `#ff9500` 橘色 |
| 娛樂 | `#c084fc` 紫色 |
| 購物 | `#fb923c` 橙色 |
| 政府 | `#94a3b8` 灰藍 |
| 軟體 | `#00ff88` 綠色 |
| 其他 | `#7aaabb` 灰青 |

---

## UI 縮放系統

### 原理
```python
# app.py 啟動時
dpi_scale = screen.logicalDotsPerInch() / 96.0   # DPI 自動值
cfg = load_config()
scale = cfg.get("ui_scale", dpi_scale)           # 使用者設定優先
theme.set_scale(scale)                            # 設定全域 SCALE

# 使用
S(14)   # → int(14 * SCALE)，用於 px 尺寸
Sf(12)  # → 12 * SCALE，用於字體 pt
```

### 使用者可選縮放
設定視窗 → 介面縮放：`80% / 100% / 125% / 150% / 175%`
儲存至 `vaultme_config.json`，重啟後生效。

### 視窗大小保護
```python
# app.py
w = min(theme.S(920), rect.width())    # 不超過螢幕寬
h = min(theme.S(620), rect.height())   # 不超過螢幕高
window.setMinimumSize(min(S(860), rect.width()), min(S(580), rect.height()))
```

---

## 打包（PyInstaller）

```bash
build_exe.bat   # 內部跑 pyinstaller VaultMe.spec --noconfirm --clean
# 輸出：dist\VaultMe.exe（單一執行檔，無命令列視窗）
```

### VaultMe.spec 重點設定
```python
datas     = [('icon.ico', '.')]          # 圖示打包進 _MEIPASS
icon      = 'icon.ico'                   # EXE 檔案圖示
console   = False                        # 不顯示命令列視窗
upx       = True                         # 壓縮（若未安裝 UPX 改 False）
```

### 凍結環境 SSL 修復
```python
# data_manager.py
if getattr(sys, "frozen", False):
    import certifi
    os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()
    os.environ["SSL_CERT_FILE"]      = certifi.where()
```

---

## 已知限制

| 項目 | 說明 |
|------|------|
| 更改主密碼後手機指紋失效 | 設計限制，需手動重綁 |
| UI 縮放重啟才生效 | Qt 不支援執行中動態重建所有 widget |
| Supabase 離線時禁止推送 | 防呆保護，重新連線後下次儲存自動恢復 |
| vm_cloud.json 需手動建立 | 無 GUI 設定，目前只能手動編輯 |
| PWA 指紋只支援 HTTPS | localhost 或 GitHub Pages 可用，HTTP 不可 |

## 打包環境（build_exe.bat / setup_env.bat）
`build_exe.bat` 開頭會呼叫 `setup_env.bat`：用 `py -3.14` 在專案資料夾建 `.venv`，照 `requirements.txt`（版本全部 `==` 釘死）安裝，再把 `.venv\Scripts` 放到 PATH 最前面，後面的 `python` / `pyinstaller` 都是 `.venv` 裡的那份。
所以**換電腦 git clone 後直接雙擊 `build_exe.bat` 就能打包**，不依賴那台電腦原本裝了什麼版本的 Python 或套件。第一次要連網（約 1-3 分鐘），之後只有 `requirements.txt` 變動才會重新安裝。
- 要換 Python 版本：改 `setup_env.bat` 的 `PYVER`、刪掉 `.venv` 後重跑。
- 新增或升級套件：改 `requirements.txt`（用 `==`），下次執行 bat 會自動重裝；程式 import 了新套件卻沒寫進 `requirements.txt` 的話，別台電腦打包會缺模組。
- `.venv/` 不進版控。
