"""Автоматическая категоризация операций.

Категория из выписки (колонка «КАТЕГОРИЯ», например в PDF Сбербанка) имеет
приоритет над правилами ключевых слов. Если её нет или она не распознана —
используются правила по описанию, при отсутствии совпадений —
``DEFAULT_CATEGORY``.
"""

from typing import Sequence

from app.categorization.rules import (
    CATEGORY_RULES,
    DEFAULT_CATEGORY,
    SBERBANK_CATEGORY_MAP,
)
from app.parsers import ParsedTransaction, parse_csv


class CategorizedTransaction(ParsedTransaction):
    """Операция из выписки с присвоенной категорией."""

    category: str = DEFAULT_CATEGORY


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def _map_statement_category(value: str | None) -> str | None:
    """Вернуть категорию приложения по категории из выписки или ``None``."""
    if not value:
        return None
    return SBERBANK_CATEGORY_MAP.get(_normalize(value))


def categorize(description: str, statement_category: str | None = None) -> str:
    """Вернуть имя категории для операции.

    Категория из выписки, распознанная по ``SBERBANK_CATEGORY_MAP``, имеет
    приоритет. Иначе — первое сработавшее ключевое слово описания. Без
    совпадений возвращается ``DEFAULT_CATEGORY``.
    """
    mapped = _map_statement_category(statement_category)
    if mapped is not None:
        return mapped

    normalized = _normalize(description)
    for category, keywords in CATEGORY_RULES.items():
        for keyword in keywords:
            if keyword in normalized:
                return category
    return DEFAULT_CATEGORY


def categorize_transactions(
    transactions: Sequence[ParsedTransaction],
) -> list[CategorizedTransaction]:
    """Присвоить категорию каждой операции из выписки."""
    return [
        CategorizedTransaction(
            date=item.date,
            amount=item.amount,
            description=item.description,
            type=item.type,
            statement_category=item.statement_category,
            category=categorize(item.description, item.statement_category),
        )
        for item in transactions
    ]


def parse_csv_categorized(
    content: str,
    source_format: str | None = None,
) -> list[CategorizedTransaction]:
    """Разобрать CSV-выписку и сразу присвоить категории операциям."""
    return categorize_transactions(
        parse_csv(content, source_format=source_format)
    )
