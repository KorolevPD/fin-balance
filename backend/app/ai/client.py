"""Реестр AI-провайдеров и точка входа для классификации и советов.

Каждый провайдер — модуль с функциями:
- ``classify_transactions(descriptions, api_key, base_url) -> list[ClassifyResult]``
- ``generate_advice(summary, api_key, base_url) -> str``

``classify_transactions`` возвращает результат строго той же длины, что и вход,
либо бросает исключение. Вызывающий код всегда может откатиться на правила.
"""

from dataclasses import dataclass

PROVIDER_GEMINI = "gemini"
PROVIDER_OPENAI_COMPAT = "openai_compatible"

DEFAULT_PROVIDER = PROVIDER_GEMINI


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
    if p in ("gemini", "google", "ai_studio"):
        return PROVIDER_GEMINI
    if p in ("openai", "openai_compatible", "groq", "openrouter"):
        return PROVIDER_OPENAI_COMPAT
    return None


def is_supported(provider: str | None) -> bool:
    return normalized_provider(provider) in (PROVIDER_GEMINI, PROVIDER_OPENAI_COMPAT)


def _load(provider: str):
    norm = normalized_provider(provider)
    if norm == PROVIDER_OPENAI_COMPAT:
        from app.ai import openai_compat as module
    else:
        from app.ai import gemini as module
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
