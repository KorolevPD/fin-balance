"""Реестр AI-провайдеров и точка входа для классификации и советов.

Единственный поддерживаемый провайдер — GigaChat. Модуль с функциями:
- ``classify_transactions(descriptions, api_key, base_url) -> list[ClassifyResult]``
- ``generate_advice(summary, api_key, base_url) -> str``

``classify_transactions`` возвращает результат строго той же длины, что и вход,
либо бросает исключение. Вызывающий код всегда может откатиться на правила.
"""

from dataclasses import dataclass

PROVIDER_GIGACHAT = "gigachat"

DEFAULT_PROVIDER = PROVIDER_GIGACHAT


@dataclass
class ClassifyResult:
    """Результат AI-классификации одной операции."""

    category: str | None
    cleaned_description: str | None


class AIError(Exception):
    """Ошибка обращения к AI-провайдеру."""


def normalized_provider(provider: str | None) -> str | None:
    """Привести имя провайдера к каноническому виду."""
    if not provider:
        return None
    p = provider.strip().lower()
    if p in ("gigachat", "giga_chat", "giga-chat"):
        return PROVIDER_GIGACHAT
    return None


def is_supported(provider: str | None) -> bool:
    return normalized_provider(provider) == PROVIDER_GIGACHAT


def _load(provider: str):
    from app.ai import gigachat as module

    return module


def classify_descriptions(
    descriptions: list[str],
    *,
    api_key: str,
    provider: str | None = DEFAULT_PROVIDER,
    base_url: str | None = None,
) -> list[ClassifyResult]:
    """Классифицировать описания операций через AI-провайдера.

    При любой ошибке (сеть, неверный ключ, разбор) бросает ``AIError``.
    """
    module = _load(provider)
    try:
        return module.classify_transactions(
            descriptions, api_key=api_key, base_url=base_url
        )
    except Exception as exc:  # noqa: BLE001 — пробрасываем как AIError
        raise AIError(f"Ошибка AI-классификации: {exc}") from exc


def generate_advice(
    summary: dict,
    *,
    api_key: str,
    provider: str | None = DEFAULT_PROVIDER,
    base_url: str | None = None,
) -> str:
    """Сгенерировать текстовый совет на основе сводки расходов."""
    module = _load(provider)
    try:
        return module.generate_advice(summary, api_key=api_key, base_url=base_url)
    except Exception as exc:  # noqa: BLE001 — пробрасываем как AIError
        raise AIError(f"Ошибка генерации совета: {exc}") from exc
