"""Автоматическая категоризация операций по правилам ключевых слов."""

from typing import Sequence

from app.categorization.rules import CATEGORY_RULES, DEFAULT_CATEGORY
from app.parsers import ParsedTransaction, parse_csv


class CategorizedTransaction(ParsedTransaction):
    """Операция из выписки с присвоенной категорией."""

    category: str = DEFAULT_CATEGORY


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def categorize(description: str) -> str:
    """Вернуть имя категории для описания операции.

    Первое сработавшее ключевое слово определяет категорию.
    Если совпадений нет — возвращает ``DEFAULT_CATEGORY``.
    """
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
            category=categorize(item.description),
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
