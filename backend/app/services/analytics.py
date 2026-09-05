"""Агрегации расходов семьи для дашборда."""

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.categorization.rules import DEFAULT_CATEGORY
from app.models import Transaction


def get_family_summary(db: Session, family_id: UUID) -> dict[str, Any]:
    """Сводка расходов семьи для дашборда фронтенда (T-014).

    Возвращает словарь с ключами ``total_amount``, ``by_category``,
    ``top_payees`` и ``monthly``. Суммы округляются до двух знаков.
    """
    rows = db.query(Transaction).filter(Transaction.family_id == family_id).all()

    total_amount = 0.0
    by_category: dict[str, dict[str, Any]] = {}
    by_payee: dict[str, dict[str, Any]] = {}
    by_month: dict[str, float] = {}

    for row in rows:
        amount = float(row.amount or 0.0)
        total_amount += amount

        category_name = (
            row.category.name if row.category is not None else DEFAULT_CATEGORY
        )
        cat = by_category.setdefault(category_name, {"amount": 0.0, "count": 0})
        cat["amount"] += amount
        cat["count"] += 1

        payee = row.cleaned_description or row.original_description or "Без названия"
        payee_item = by_payee.setdefault(payee, {"amount": 0.0, "count": 0})
        payee_item["amount"] += amount
        payee_item["count"] += 1

        if row.date is not None:
            month = row.date.strftime("%Y-%m")
            by_month[month] = by_month.get(month, 0.0) + amount

    by_category_list = [
        {"category": name, "amount": round(data["amount"], 2), "count": data["count"]}
        for name, data in sorted(
            by_category.items(), key=lambda kv: kv[1]["amount"], reverse=True
        )
    ]
    by_payee_list = [
        {"payee": name, "amount": round(data["amount"], 2), "count": data["count"]}
        for name, data in sorted(
            by_payee.items(),
            key=lambda kv: abs(kv[1]["amount"]),
            reverse=True,
        )
    ]
    monthly_list = [
        {"month": month, "amount": round(amount, 2)}
        for month, amount in sorted(by_month.items())
    ]

    return {
        "total_amount": round(total_amount, 2),
        "by_category": by_category_list,
        "top_payees": by_payee_list,
        "monthly": monthly_list,
    }
