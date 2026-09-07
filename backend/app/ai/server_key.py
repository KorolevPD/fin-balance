"""Серверный GigaChat-ключ из переменной окружения ``GIGACHAT_API_KEY``.

Если переменная заполнена, сервер использует общий ключ для всех
пользователей (GigaChat), а раздел «AI-ассистент» в профиле скрывается.
Если переменная пуста — пользователь вводит свой ключ как раньше.
"""

import os


def server_gigachat_key() -> str | None:
    """Вернуть серверный GigaChat-ключ или ``None``, если он не задан."""
    value = (os.getenv("GIGACHAT_API_KEY") or "").strip()
    return value or None


def has_server_gigachat_key() -> bool:
    """Признак того, что серверный GigaChat-ключ задан."""
    return server_gigachat_key() is not None
