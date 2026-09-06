"""Обогащение операций результатами AI-классификации.

AI запускается только если у пользователя сохранён ключ и провайдер
поддерживается. При любой ошибке AI или некорректных ответах операции
остаются с категорией из правил (фолбэк не ломает импорт).
"""

from typing import Sequence

from app.ai import AIError, classify_descriptions, decrypt_key, is_supported
from app.ai.client import ClassifyResult
from app.categorization import CategorizedTransaction
from app.categorization.rules import CATEGORY_RULES, DEFAULT_CATEGORY

MAX_CLEANED_LENGTH = 255

_ALLOWED_CATEGORIES = {*CATEGORY_RULES.keys(), DEFAULT_CATEGORY}


def _normalize_category(value: str | None) -> str | None:
    if not value:
        return None
    category = " ".join(str(value).strip().split())
    if category in _ALLOWED_CATEGORIES:
        return category
    return None


def _normalize_cleaned(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = " ".join(str(value).strip().split())
    if not cleaned:
        return None
    return cleaned[:MAX_CLEANED_LENGTH]


def _apply_results(
    transactions: list[CategorizedTransaction],
    results: Sequence[ClassifyResult],
) -> list[CategorizedTransaction]:
    """Применить результаты AI к операциям, сохраняя порядок."""
    enriched: list[CategorizedTransaction] = []
    for item, result in zip(transactions, results):
        category = _normalize_category(result.category)
        cleaned = _normalize_cleaned(result.cleaned_description)
        enriched.append(
            CategorizedTransaction(
                date=item.date,
                amount=item.amount,
                description=item.description,
                type=item.type,
                statement_category=item.statement_category,
                category=category or item.category,
                cleaned_description=cleaned or item.cleaned_description,
            )
        )
    return enriched


def enrich_with_ai(
    transactions: list[CategorizedTransaction],
    *,
    provider: str | None,
    api_key_encrypted: str | None,
    base_url: str | None = None,
) -> list[CategorizedTransaction]:
    """Если возможно — применить AI-классификацию; иначе вернуть как есть."""
    if not api_key_encrypted or not is_supported(provider):
        return transactions

    api_key = decrypt_key(api_key_encrypted)
    if not api_key:
        return transactions

    if not transactions:
        return transactions

    try:
        results = classify_descriptions(
            [item.description for item in transactions],
            api_key=api_key,
            provider=provider,
            base_url=base_url,
        )
    except AIError:
        return transactions
    if len(results) != len(transactions):
        return transactions
    return _apply_results(transactions, results)
