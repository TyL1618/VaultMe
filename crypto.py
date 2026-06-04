"""
crypto.py - PBKDF2-HMAC-SHA256 key derivation + AES-256-GCM encryption

跨裝置解密原理：
  加密時產生隨機 salt (32 bytes)，salt 隨密文一起儲存。
  任何裝置只要有相同主密碼 + salt，就能透過 PBKDF2 推導出相同金鑰。
  不需要傳輸或同步 key 檔案。

儲存格式（JSON string）：
  {"salt": "<base64>", "nonce": "<base64>", "ciphertext": "<base64>"}
"""

import os
import json
import base64

from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag

_ITERATIONS = 260_000
_SALT_SIZE  = 32
_KEY_SIZE   = 32
_NONCE_SIZE = 12


def _b64e(b: bytes) -> str:
    return base64.b64encode(b).decode()


def _b64d(s: str) -> bytes:
    return base64.b64decode(s)


def derive_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=_KEY_SIZE,
        salt=salt,
        iterations=_ITERATIONS,
    )
    return kdf.derive(password.encode("utf-8"))


def encrypt(plaintext: str, password: str, salt: bytes = None) -> str:
    """
    加密 plaintext，回傳 JSON string（可直接存檔或上傳 Supabase）。
    salt 為 None 時自動產生新 salt（第一次加密）。
    有傳入 salt 時重用（更新資料時保持相同 salt，確保其他裝置能解密）。
    """
    if salt is None:
        salt = os.urandom(_SALT_SIZE)
    key   = derive_key(password, salt)
    nonce = os.urandom(_NONCE_SIZE)
    aesgcm    = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return json.dumps({
        "salt":       _b64e(salt),
        "nonce":      _b64e(nonce),
        "ciphertext": _b64e(ciphertext),
    }, separators=(",", ":"))


def decrypt(blob_str: str, password: str) -> str:
    """
    解密，回傳 plaintext string。
    密碼錯誤或資料損毀時拋出 ValueError。
    """
    try:
        blob       = json.loads(blob_str)
        salt       = _b64d(blob["salt"])
        nonce      = _b64d(blob["nonce"])
        ciphertext = _b64d(blob["ciphertext"])
    except Exception as e:
        raise ValueError(f"解密失敗：資料格式錯誤 ({e})")

    key    = derive_key(password, salt)
    aesgcm = AESGCM(key)
    try:
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    except InvalidTag:
        raise ValueError("密碼錯誤或資料已損毀")

    return plaintext.decode("utf-8")


def extract_salt(blob_str: str) -> bytes | None:
    """從已加密的 blob 取出 salt，用於保持相同 salt 重新加密。"""
    try:
        blob = json.loads(blob_str)
        return _b64d(blob["salt"])
    except Exception:
        return None
