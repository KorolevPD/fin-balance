"""Шифрование/дешифрование AI-ключей пользователей (AES-GCM).

Ключ шифрования берётся из переменной окружения ``AI_KEY_ENCRYPTION_KEY``.
Каждое значение шифруется свежим nonce, который хранится вместе с
зашифрованным текстом (base64: ``nonce.ciphertext``).
"""

import base64
import hashlib
import os

from cryptography.fernet import Fernet, InvalidToken


def _derive_key() -> bytes:
    raw = os.getenv("AI_KEY_ENCRYPTION_KEY", "")
    if not raw:
        return b""
    return hashlib.sha256(raw.encode("utf-8")).digest()


_fernet: "Fernet | None" = None


def _get_fernet() -> Fernet:
    global _fernet
    key = _derive_key()
    if not key:
        raise ValueError(
            "AI_KEY_ENCRYPTION_KEY не задан: невозможно зашифровать AI-ключ"
        )
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt_key(plaintext: str) -> str:
    """Зашифровать AI-ключ пользователя."""
    if not plaintext:
        return plaintext
    return _get_fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_key(ciphertext: str | None) -> str | None:
    """Расшифровать AI-ключ пользователя. Возвращает ``None`` при ошибке."""
    if not ciphertext:
        return None
    try:
        return _get_fernet().decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError, base64.binascii.Error):
        return None
