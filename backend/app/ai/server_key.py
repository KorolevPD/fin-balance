"""Серверный Gemini-ключ из переменной окружения ``GEMINI_API_KEY``.

Если переменная заполнена, сервер использует общий ключ для всех
пользователей (Gemini), а у клиента пропадает возможность вводить свой
ключ. Если переменная пуста — пользователь вводит свой ключ как раньше.
"""

import os


def server_gemini_key() -> str | None:
    """Вернуть серверный Gemini-ключ или ``None``, если он не задан."""
    value = (os.getenv("GEMINI_API_KEY") or "").strip()
    return value or None


def has_server_gemini_key() -> bool:
    """Признак того, что серверный Gemini-ключ задан."""
    return server_gemini_key() is not None
