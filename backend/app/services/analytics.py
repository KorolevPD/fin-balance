"""Агрегации расходов семьи для дашборда."""

from collections import defaultdict
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.categorization.rules import DEFAULT_CATEGORY
from app.models import FamilyMember, Transaction


def get_family_summary(
    db: Session,
    family_id: UUID,
    user_id: UUID | None = None,
) -> dict[str, Any]:
    """Сводка расходов семьи для дашборда фронтенда (T-014).

    Возвращает словарь с ключами ``total_amount``, ``by_category``,
    ``top_payees``, ``monthly``, ``family_members`` (члены семьи с
    суммарными тратами, отсортированы по убыванию) и ``uploaded_files``
    (файлы текущего пользователя с периодом первой/последней операции).
    Суммы округляются до двух знаков.
    """
    rows = db.query(Transaction).filter(Transaction.family_id == family_id).all()

    total_amount = 0.0
    by_category: dict[str, dict[str, Any]] = {}
    by_payee: dict[str, dict[str, Any]] = {}
    by_month: dict[str, float] = {}
    by_member_total: dict[UUID, float] = defaultdict(float)
    files: dict[str, dict[str, Any]] = {}

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

        by_member_total[row.user_id] += amount

        if row.user_id == user_id and row.source_file:
            file_item = files.setdefault(
                row.source_file,
                {"period_start": row.date, "period_end": row.date, "count": 0},
            )
            file_item["period_start"] = min(
                row.date, file_item["period_start"]
            )
            file_item["period_end"] = max(row.date, file_item["period_end"])
            file_item["count"] += 1

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

    members = (
        db.query(FamilyMember)
        .filter(FamilyMember.family_id == family_id)
        .all()
    )
    family_members_list = [
        {
            "user_id": str(member.user_id),
            "name": member.user.name or member.user.email,
            "email": member.user.email,
            "total_expenses": round(by_member_total.get(member.user_id, 0.0), 2),
        }
        for member in members
    ]
    family_members_list.sort(key=lambda item: item["total_expenses"], reverse=True)

    uploaded_files_list = [
        {
            "filename": filename,
            "period_start": data["period_start"].strftime("%Y-%m-%d"),
            "period_end": data["period_end"].strftime("%Y-%m-%d"),
            "operations_count": data["count"],
        }
        for filename, data in sorted(files.items())
    ]

    return {
        "total_amount": round(total_amount, 2),
        "by_category": by_category_list,
        "top_payees": by_payee_list,
        "monthly": monthly_list,
        "family_members": family_members_list,
        "uploaded_files": uploaded_files_list,
    }
