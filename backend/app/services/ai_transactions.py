"""Обогащение операций результатами AI-классификации.

AI запускается только если у пользователя сохранён ключ и провайдер
поддерживается. При любой ошибке AI или некорректных ответах операции
остаются с категорией из правил (фолбэк не ломает импорт).
"""

from typing import Sequence
from uuid import UUID

from sqlalchemy.orm import Session

from app import database
from app.ai import AIError, classify_descriptions, decrypt_key, is_supported
from app.ai.client import ClassifyResult
from app.categorization import CategorizedTransaction
from app.categorization.rules import CATEGORY_RULES, DEFAULT_CATEGORY
from app.models import Transaction, User
from app.services.transactions import _resolve_or_create_category

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


def enrich_saved_transactions(
    db: Session,
    *,
    family_id: UUID,
    user_id: UUID,
    source_file: str,
) -> int:
    """Обогатить уже сохранённые операции AI-результатами (фоновая задача).

    Читает созданные выпиской транзакции, вызывает AI-классификацию и
    обновляет category/cleaned_description. Возвращает число обновлённых.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.ai_api_key_encrypted or not is_supported(user.ai_provider):
        return 0

    api_key = decrypt_key(user.ai_api_key_encrypted)
    if not api_key:
        return 0

    transactions = (
        db.query(Transaction)
        .filter(
            Transaction.family_id == family_id,
            Transaction.user_id == user_id,
            Transaction.source_file == source_file,
        )
        .all()
    )
    if not transactions:
        return 0

    try:
        results = classify_descriptions(
            [t.original_description for t in transactions],
            api_key=api_key,
            provider=user.ai_provider,
            base_url=user.ai_base_url,
        )
    except AIError:
        return 0
    if len(results) != len(transactions):
        return 0

    updated = 0
    for txn, result in zip(transactions, results):
        category = _normalize_category(result.category)
        cleaned = _normalize_cleaned(result.cleaned_description)
        changed = False
        if category and category != (txn.category.name if txn.category else None):
            category_obj = _resolve_or_create_category(db, category)
            txn.category_id = category_obj.id
            changed = True
        if cleaned and cleaned != txn.cleaned_description:
            txn.cleaned_description = cleaned
            changed = True
        if changed:
            updated += 1
    db.commit()
    return updated


def run_enrich_in_background(
    *,
    family_id: UUID,
    user_id: UUID,
    source_file: str,
) -> None:
    """Обернуть фоновое обогащение: открыть свою сессию и выполнить.

    Используется как фоновая задача FastAPI (BackgroundTasks). Любые
    ошибки не должны ронять ответ импорта.
    """
    db = database.SessionLocal()
    try:
        enrich_saved_transactions(
            db,
            family_id=family_id,
            user_id=user_id,
            source_file=source_file,
        )
    except Exception:  # noqa: BLE001 — фон не должен ломать импорт
        return
    finally:
        db.close()
