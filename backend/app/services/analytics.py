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
    filter_user_id: UUID | None = None,
) -> dict[str, Any]:
    """Сводка расходов семьи для дашборда фронтенда (T-014).

    Возвращает словарь с ключами ``total_amount``, ``by_category``,
    ``top_payees``, ``yearly``, ``monthly``, ``daily``, ``family_members``
    (члены семьи с суммарными тратами, отсортированы по убыванию),
    ``uploaded_files`` (файлы текущего пользователя с периодом
    первой/последней операции) и ``other_members_have_statements`` (есть ли у
    членов семьи, кроме запрашивающего, загруженные выписки).
    Финансовые агрегаты учитывают только расходы (``type == "expense"``);
    ``uploaded_files`` — все операции независимо от типа.
    Суммы округляются до двух знаков.
    ``user_id`` — запрашивающий пользователь: используется всегда для блока
    ``uploaded_files``. Если задан ``filter_user_id``, финансовые агрегаты
    считаются только по операциям этого пользователя (режим «Личные» на
    дашборде); иначе — по всей семье.
    """
    query = db.query(Transaction).filter(
        Transaction.family_id == family_id,
        Transaction.is_self_transfer.is_not(True),
    )
    if filter_user_id is not None:
        query = query.filter(Transaction.user_id == filter_user_id)
    rows = query.all()

    total_amount = 0.0
    by_category: dict[str, dict[str, Any]] = {}
    by_payee: dict[str, dict[str, Any]] = {}
    by_year: dict[str, float] = {}
    by_month: dict[str, float] = {}
    by_day: dict[str, float] = {}
    by_member_total: dict[UUID, float] = defaultdict(float)

    for row in rows:
        amount = float(row.amount or 0.0)
        is_expense = (row.type or "expense") == "expense"

        if is_expense:
            total_amount += amount

            category_name = (
                row.category.name if row.category is not None else DEFAULT_CATEGORY
            )
            cat = by_category.setdefault(category_name, {"amount": 0.0, "count": 0})
            cat["amount"] += amount
            cat["count"] += 1

            payee = (
                row.cleaned_description or row.original_description or "Без названия"
            )
            payee_item = by_payee.setdefault(payee, {"amount": 0.0, "count": 0})
            payee_item["amount"] += amount
            payee_item["count"] += 1

            if row.date is not None:
                year = row.date.strftime("%Y")
                by_year[year] = by_year.get(year, 0.0) + amount

                month = row.date.strftime("%Y-%m")
                by_month[month] = by_month.get(month, 0.0) + amount

                day = row.date.strftime("%Y-%m-%d")
                by_day[day] = by_day.get(day, 0.0) + amount

            by_member_total[row.user_id] += amount

    other_members_have_statements = False
    if user_id is not None:
        other_stmt = (
            db.query(Transaction.id)
            .filter(
                Transaction.family_id == family_id,
                Transaction.user_id != user_id,
                Transaction.source_file.is_not(None),
            )
            .limit(1)
            .first()
        )
        other_members_have_statements = other_stmt is not None

    files: dict[str, dict[str, Any]] = {}
    if user_id is not None:
        file_rows = (
            db.query(Transaction)
            .filter(
                Transaction.family_id == family_id,
                Transaction.user_id == user_id,
                Transaction.source_file.is_not(None),
            )
            .all()
        )
        for row in file_rows:
            file_item = files.setdefault(
                row.source_file,
                {"period_start": row.date, "period_end": row.date, "count": 0},
            )
            file_item["period_start"] = min(row.date, file_item["period_start"])
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
    yearly_list = [
        {"year": year, "amount": round(amount, 2)}
        for year, amount in sorted(by_year.items())
    ]
    daily_list = [
        {"day": day, "amount": round(amount, 2)}
        for day, amount in sorted(by_day.items())
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
        "yearly": yearly_list,
        "monthly": monthly_list,
        "daily": daily_list,
        "family_members": family_members_list,
        "uploaded_files": uploaded_files_list,
        "other_members_have_statements": other_members_have_statements,
    }
