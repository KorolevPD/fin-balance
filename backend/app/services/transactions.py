"""Сохранение операций из выписки в БД с обработкой дублей.

Дубликатом считается пара записей с одинаковыми датой, суммой и исходным
описанием в пределах одной семьи. Обрабатываются два случая:
- повтор строк внутри одного импорта;
- повторный импорт уже сохранённых операций (та же выписка, тот же файл).
"""

from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Iterable
from uuid import UUID

from sqlalchemy.orm import Session

from app.categorization import CategorizedTransaction
from app.models import Category, Transaction


@dataclass
class SaveResult:
    """Итог сохранения партии операций."""

    total: int
    created: int
    duplicates_skipped: int


def _as_dt(day: date) -> datetime:
    return datetime.combine(day, time.min)


def _dedup_key(day: date, amount: float, description: str) -> tuple:
    return (_as_dt(day), round(amount, 2), description)


def _resolve_or_create_category(db: Session, name: str) -> Category:
    category = db.query(Category).filter(Category.name == name).first()
    if category is None:
        category = Category(name=name)
        db.add(category)
        db.flush()
    return category


def _existing_keys(
    db: Session,
    family_id: UUID,
    keys: Iterable[tuple],
) -> set[tuple]:
    dates = [key[0] for key in keys]
    if not dates:
        return set()
    rows = (
        db.query(Transaction.date, Transaction.amount, Transaction.original_description)
        .filter(Transaction.family_id == family_id, Transaction.date.in_(dates))
        .all()
    )
    return {
        (_as_dt(row.date.date()), round(row.amount, 2), row.original_description)
        for row in rows
    }


def save_transactions(
    db: Session,
    *,
    family_id: UUID,
    user_id: UUID,
    transactions: Iterable[CategorizedTransaction],
    source_file: str | None = None,
) -> SaveResult:
    """Сохранить операции выписки в БД с привязкой к семье и пользователю.

    Возвращает количество созданных записей и пропущенных дубликатов.
    """
    items = list(transactions)

    unique: dict[tuple, CategorizedTransaction] = {}
    internal_duplicates = 0
    for item in items:
        key = _dedup_key(item.date, item.amount, item.description)
        if key in unique:
            internal_duplicates += 1
        else:
            unique[key] = item

    existing = _existing_keys(db, family_id, unique.keys())

    created = 0
    db_matches = 0
    for key, item in unique.items():
        if key in existing:
            db_matches += 1
            continue
        category = _resolve_or_create_category(db, item.category)
        db.add(
            Transaction(
                family_id=family_id,
                user_id=user_id,
                category_id=category.id,
                date=_as_dt(item.date),
                amount=round(item.amount, 2),
                type=item.type if item.type in ("income", "expense") else "expense",
                original_description=item.description,
                cleaned_description=None,
                source_file=source_file,
            )
        )
        created += 1

    db.commit()
    return SaveResult(
        total=len(unique),
        created=created,
        duplicates_skipped=internal_duplicates + db_matches,
    )
