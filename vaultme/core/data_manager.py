"""
data_manager.py - 本地加密儲存 + Supabase 雲端同步

【Supabase 設定】
  1. 建立 Table：
       Table name: vaultme
       Columns: id(text, PK), payload(text), updated(text)
  2. SQL Editor 執行：
       ALTER TABLE vaultme ENABLE ROW LEVEL SECURITY;
       CREATE POLICY "Own data only" ON vaultme
         FOR ALL USING (auth.uid()::text = id);
  3. 在 VaultMe 資料夾（或 %APPDATA%\\VaultMe\\）建立 vm_cloud.json：
       {
         "supabase_url": "https://xxxx.supabase.co",
         "supabase_key": "eyJ...",
         "email": "your@email.com",
         "password": "yourpassword"
       }

【加密說明】
  本地 .enc 檔案與 Supabase payload 欄位永遠儲存 AES-256-GCM 加密後的亂碼。
  主密碼永遠不離開程式記憶體。

【防呆機制】
  _cloud_push_allowed = False → 禁止推送（全新安裝或斷線啟動）
  推送前比對筆數：本地 < 雲端 50% → 彈警告，禁止推送
"""

import json
import os
import sys
import time
import threading
import requests
from datetime import datetime

if getattr(sys, "frozen", False):
    import certifi
    os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()
    os.environ["SSL_CERT_FILE"]      = certifi.where()

from PyQt6.QtCore import QObject, pyqtSignal

from vaultme.crypto import encrypt, decrypt, extract_salt


# ── 路徑 ──────────────────────────────────────────────────────────────
def _get_data_dir():
    base = os.environ.get("APPDATA", os.path.expanduser("~")) if os.name == "nt" \
           else os.path.expanduser("~")
    d = os.path.join(base, "VaultMe")
    os.makedirs(d, exist_ok=True)
    return d


DATA_DIR    = _get_data_dir()
DATA_FILE   = os.path.join(DATA_DIR, "vault.enc")
HINT_FILE   = os.path.join(DATA_DIR, "vault.hint")
CLOUD_CFG   = os.path.join(DATA_DIR, "vm_cloud.json")

_CLOUD_TIMEOUT  = 6
_SUPABASE_TABLE = "vaultme"

# ── 模組狀態 ──────────────────────────────────────────────────────────
_master_password: str = ""
_auth_cache: dict = {"token": None, "user_id": None, "expires_at": 0.0}
_cloud_push_allowed: bool = False
_cached_salt: bytes | None = None   # 重用 salt，保持跨裝置一致性


# ── 主密碼 ────────────────────────────────────────────────────────────
def is_first_time() -> bool:
    """True = 尚未設定過主密碼（vault.enc 不存在）"""
    return not os.path.exists(DATA_FILE)


def save_hint(hint: str):
    """儲存密碼提示（明文，存在 vault.hint）"""
    try:
        with open(HINT_FILE, "w", encoding="utf-8") as f:
            f.write(hint)
    except Exception:
        pass


def get_hint() -> str:
    """讀取密碼提示，沒設定則回傳空字串"""
    try:
        if os.path.exists(HINT_FILE):
            with open(HINT_FILE, "r", encoding="utf-8") as f:
                return f.read().strip()
    except Exception:
        pass
    return ""


def set_master_password(password: str):
    global _master_password
    _master_password = password


def get_master_password() -> str:
    return _master_password


# ── Supabase 設定 ─────────────────────────────────────────────────────
def _load_cloud_cfg():
    paths = [CLOUD_CFG, os.path.join(os.path.dirname(sys.argv[0]), "vm_cloud.json")]
    for p in paths:
        if not os.path.exists(p):
            continue
        try:
            with open(p, "r", encoding="utf-8-sig") as f:
                cfg = json.load(f)
            url   = cfg.get("supabase_url", "").rstrip("/")
            key   = cfg.get("supabase_key", "")
            email = cfg.get("email", "")
            pwd   = cfg.get("password", "")
            if url and key:
                return url, key, email, pwd
        except Exception:
            pass
    return None, None, None, None


# ── Auth ──────────────────────────────────────────────────────────────
def _sign_in(url, anon_key, email, password):
    r = requests.post(
        f"{url}/auth/v1/token?grant_type=password",
        headers={"apikey": anon_key, "Content-Type": "application/json"},
        json={"email": email, "password": password},
        timeout=_CLOUD_TIMEOUT,
    )
    r.raise_for_status()
    d = r.json()
    return d["access_token"], d["user"]["id"], d.get("expires_in", 3600)


def _get_auth(url, anon_key, email, password):
    global _auth_cache
    now = time.time()
    if _auth_cache["token"] and _auth_cache["expires_at"] > now + 60:
        headers = _make_headers(anon_key, _auth_cache["token"])
        return headers, _auth_cache["user_id"]
    try:
        token, uid, expires = _sign_in(url, anon_key, email, password)
        _auth_cache = {"token": token, "user_id": uid, "expires_at": now + expires}
        return _make_headers(anon_key, token), uid
    except Exception as e:
        return None, None


def _make_headers(anon_key, token=None):
    bearer = token or anon_key
    return {
        "apikey":        anon_key,
        "Authorization": f"Bearer {bearer}",
        "Content-Type":  "application/json",
        "Prefer":        "return=minimal",
    }


# ── 雲端讀取 ──────────────────────────────────────────────────────────
def _cloud_pull(url, anon_key, email, password, master_pwd):
    """
    回傳 (data, uid, reachable)
      data      : 解密後的 dict，或 None（無資料 / 解密失敗）
      uid       : user UUID，或 None（auth 失敗）
      reachable : True = 成功連上雲端（即使無資料），False = 網路/auth 錯誤
    """
    headers, uid = _get_auth(url, anon_key, email, password)
    if headers is None:
        return None, None, False
    try:
        ep = f"{url}/rest/v1/{_SUPABASE_TABLE}?id=eq.{uid}&select=payload,updated"
        r  = requests.get(ep, headers=headers, timeout=_CLOUD_TIMEOUT)
        r.raise_for_status()
        rows = r.json()
        if not rows:
            # 雲端可連，但還沒有資料（全新帳號第一次同步）
            return None, uid, True
        payload_str = rows[0].get("payload", "")
        if not payload_str:
            return None, uid, True
        plaintext = decrypt(payload_str, master_pwd)
        data = json.loads(plaintext)
        return data, uid, True
    except Exception:
        return None, None, False


# ── 雲端寫入 ──────────────────────────────────────────────────────────
def _cloud_push(url, anon_key, email, password, payload_str, uid) -> bool:
    headers, _ = _get_auth(url, anon_key, email, password)
    if headers is None:
        return False
    h = dict(headers)
    h["Prefer"] = "resolution=merge-duplicates,return=minimal"
    body = {
        "id":      uid,
        "payload": payload_str,
        "updated": datetime.utcnow().isoformat(),
    }
    try:
        r = requests.post(
            f"{url}/rest/v1/{_SUPABASE_TABLE}",
            headers=h, json=body, timeout=_CLOUD_TIMEOUT,
        )
        r.raise_for_status()
        return True
    except Exception:
        return False


# ── 時間戳比較 ────────────────────────────────────────────────────────
def _pick_newer(local_data, cloud_data):
    if cloud_data is None:
        return local_data
    if local_data is None:
        return cloud_data
    lt = local_data.get("_updated", "")
    ct = cloud_data.get("_updated", "")
    if not lt and not ct:
        return local_data
    if not lt:
        return cloud_data
    if not ct:
        return local_data
    return cloud_data if ct >= lt else local_data


# ── 本地讀取 ──────────────────────────────────────────────────────────
def _load_local(master_pwd: str):
    """
    回傳解密後的 dict，或 None（檔案不存在）。
    檔案存在但密碼錯誤 → 拋出 ValueError（讓登入畫面顯示錯誤）。
    """
    if not os.path.exists(DATA_FILE):
        return None   # 全新安裝，正常
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            blob_str = f.read().strip()
    except Exception:
        return None   # 讀檔失敗（檔案損毀），當作無檔案

    # decrypt 若密碼錯誤會拋 ValueError，不要在這裡吞掉
    plaintext = decrypt(blob_str, master_pwd)
    return json.loads(plaintext)


def _load_local_blob() -> str | None:
    if not os.path.exists(DATA_FILE):
        return None
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return None


# ── 預設資料 ──────────────────────────────────────────────────────────
def _default_data():
    return {"entries": [], "_updated": ""}


# ── 公開 API：load_data ───────────────────────────────────────────────
def load_data(master_pwd: str) -> dict:
    """
    載入資料。
    1. 讀本地加密檔
    2. 嘗試從雲端拉取
    3. 取 _updated 較新的那份
    4. 根據結果設定 _cloud_push_allowed
    """
    global _cloud_push_allowed, _cached_salt

    set_master_password(master_pwd)

    local_data = _load_local(master_pwd)

    # 取得本地 blob 的 salt，未來重新加密時重用
    local_blob = _load_local_blob()
    if local_blob:
        _cached_salt = extract_salt(local_blob)

    sb_url, sb_key, sb_email, sb_pwd = _load_cloud_cfg()
    cloud_configured = bool(sb_url and sb_key)
    cloud_data       = None
    cloud_reachable  = False
    cloud_uid        = None

    if cloud_configured:
        cloud_data, cloud_uid, cloud_reachable = _cloud_pull(sb_url, sb_key, sb_email, sb_pwd, master_pwd)

    best = _pick_newer(local_data, cloud_data)

    if best:
        # 雲端設定了但本次斷線 → 禁止推送
        if cloud_configured and not cloud_reachable:
            _cloud_push_allowed = False
        else:
            _cloud_push_allowed = True
    else:
        best = _default_data()
        _cloud_push_allowed = False   # 全新安裝，禁止推送保護雲端

    # 雲端比本地新 → 同步更新本地備份
    if cloud_data and local_data:
        ct = cloud_data.get("_updated", "")
        lt = local_data.get("_updated", "")
        if ct > lt:
            _save_local_data(best, master_pwd)

    return best


def is_cloud_push_allowed() -> bool:
    return _cloud_push_allowed


# ── 公開 API：save_data ───────────────────────────────────────────────
def save_data(data: dict):
    """
    1. 立刻寫本地加密檔
    2. 非同步推送雲端（若允許且筆數安全）
    """
    global _cloud_push_allowed

    data["_updated"] = datetime.utcnow().isoformat()

    master_pwd = get_master_password()
    if not master_pwd:
        return

    _save_local_data(data, master_pwd)

    if not _cloud_push_allowed:
        return

    sb_url, sb_key, sb_email, sb_pwd = _load_cloud_cfg()
    if not (sb_url and sb_key):
        return

    _, uid = _get_auth(sb_url, sb_key, sb_email, sb_pwd)
    if not uid:
        return

    payload_str = _encrypt_data(data, master_pwd)

    def _push():
        _cloud_push(sb_url, sb_key, sb_email, sb_pwd, payload_str, uid)

    threading.Thread(target=_push, daemon=True).start()


def save_data_with_guard(data: dict, on_blocked=None):
    """
    推送前比對筆數：本地筆數 < 雲端筆數 50% → 呼叫 on_blocked callback 並阻止推送。
    on_blocked(local_count, cloud_count) → 若回傳 True 代表用戶強制確認，繼續推送。
    """
    global _cloud_push_allowed

    sb_url, sb_key, sb_email, sb_pwd = _load_cloud_cfg()
    cloud_configured = bool(sb_url and sb_key)

    if cloud_configured and _cloud_push_allowed:
        master_pwd = get_master_password()
        cloud_data, _, _reachable = _cloud_pull(sb_url, sb_key, sb_email, sb_pwd, master_pwd)
        if cloud_data:
            local_count = len(data.get("entries", []))
            cloud_count = len(cloud_data.get("entries", []))
            if cloud_count > 0 and local_count < cloud_count * 0.5:
                if on_blocked:
                    confirmed = on_blocked(local_count, cloud_count)
                    if not confirmed:
                        _save_local_data(data, master_pwd)
                        return
                else:
                    return

    save_data(data)


def _save_local_data(data: dict, master_pwd: str):
    global _cached_salt
    blob_str = _encrypt_data(data, master_pwd)
    # 第一次加密後快取 salt
    if _cached_salt is None:
        _cached_salt = extract_salt(blob_str)
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            f.write(blob_str)
    except Exception as e:
        print(f"[VaultMe] 本地儲存失敗：{e}")


def _encrypt_data(data: dict, master_pwd: str) -> str:
    global _cached_salt
    plaintext = json.dumps(data, ensure_ascii=False)
    return encrypt(plaintext, master_pwd, salt=_cached_salt)


# ── 背景同步 Worker ────────────────────────────────────────────────────
class SyncWorker(QObject):
    sync_done  = pyqtSignal(bool, str)   # success, message

    def run_sync(self, data: dict):
        def _work():
            sb_url, sb_key, sb_email, sb_pwd = _load_cloud_cfg()
            if not (sb_url and sb_key):
                self.sync_done.emit(False, "未設定 Supabase")
                return
            if not _cloud_push_allowed:
                self.sync_done.emit(False, "推送已停用（防呆保護）")
                return
            master_pwd = get_master_password()
            _, uid = _get_auth(sb_url, sb_key, sb_email, sb_pwd)
            if not uid:
                self.sync_done.emit(False, "Supabase 登入失敗")
                return
            payload_str = _encrypt_data(data, master_pwd)
            ok = _cloud_push(sb_url, sb_key, sb_email, sb_pwd, payload_str, uid)
            msg = "已同步至雲端" if ok else "雲端推送失敗"
            self.sync_done.emit(ok, msg)
        threading.Thread(target=_work, daemon=True).start()
