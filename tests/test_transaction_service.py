# -*- coding: utf-8 -*-

from datetime import date
from uuid import UUID

from app.categorization import CategorizedTransaction
from app.models import Category, Transaction
from app.services import save_transactions

FAMILY_A = UUID("11111111-1111-1111-1111-111111111111")
FAMILY_B = UUID("33333333-3333-3333-3333-333333333333")
USER = UUID("22222222-2222-2222-2222-222222222222")
USER_OTHER = UUID("44444444-4444-4444-4444-444444444444")


def tx(date_value, amount, description, category="Прочее"):
    return CategorizedTransaction(
        date=date_value,
        amount=amount,
        description=description,
        type="expense",
        category=category,
    )


class TestSaveTransactions:
    def test_создаётся_запись_с_привязкой_к_семье_и_пользователю(self, db):
        result = save_transactions(
            db,
            family_id=FAMILY_A,
            user_id=USER,
            transactions=[tx(date(2026, 9, 1), 100.0, "Лента")],
        )

        saved = db.query(Transaction).all()
        assert result.created == 1
        assert len(saved) == 1
        assert saved[0].family_id == FAMILY_A
        assert saved[0].user_id == USER
        assert saved[0].amount == 100.0
        assert saved[0].original_description == "Лента"

    def test_сохраняются_дата_и_категория(self, db):
        save_transactions(
            db,
            family_id=FAMILY_A,
            user_id=USER,
            transactions=[tx(date(2026, 9, 1), 100.0, "Лента", "Продукты")],
        )

        saved = db.query(Transaction).one()
        assert saved.date.date() == date(2026, 9, 1)
        assert saved.category.name == "Продукты"

    def test_неизвестная_категория_создаётся_автоматически(self, db):
        save_transactions(
            db,
            family_id=FAMILY_A,
            user_id=USER,
            transactions=[tx(date(2026, 9, 1), 100.0, "Лента", "Продукты")],
        )

        assert db.query(Category).filter(Category.name == "Продукты").count() == 1

    def test_существующая_категория_не_дублируется(self, db):
        save_transactions(
            db,
            family_id=FAMILY_A,
            user_id=USER,
            transactions=[tx(date(2026, 9, 1), 100.0, "Лента", "Продукты")],
        )
        save_transactions(
            db,
            family_id=FAMILY_A,
            user_id=USER,
            transactions=[tx(date(2026, 9, 2), 200.0, "Аптека", "Продукты")],
        )

        assert db.query(Category).filter(Category.name == "Продукты").count() == 1

    def test_сохраняется_тип_операции(self, db):
        income = CategorizedTransaction(
            date=date(2026, 9, 1),
            amount=1000.0,
            description="Зарплата",
            type="income",
            category="Прочее",
        )
        expense = tx(date(2026, 9, 2), 250.0, "Лента", "Продукты")
        save_transactions(
            db,
            family_id=FAMILY_A,
            user_id=USER,
            transactions=[income, expense],
        )

        saved = {t.original_description: t.type for t in db.query(Transaction).all()}
        assert saved["Зарплата"] == "income"
        assert saved["Лента"] == "expense"

    def test_неизвестный_тип_подменяется_на_расход(self, db):
        unknown = CategorizedTransaction(
            date=date(2026, 9, 1),
            amount=100.0,
            description="Лента",
            type="unknown",
            category="Прочее",
        )
        save_transactions(
            db,
            family_id=FAMILY_A,
            user_id=USER,
            transactions=[unknown],
        )

        assert db.query(Transaction).one().type == "expense"

    def test_дубли_в_одном_импорте_сохраняются_один_раз(self, db):
        duplicated_operations = [
            tx(date(2026, 9, 1), 100.0, "Лента"),
            tx(date(2026, 9, 1), 100.0, "Лента"),
            tx(date(2026, 9, 1), 100.0, "Лента"),
        ]
        result = save_transactions(
            db,
            family_id=FAMILY_A,
            user_id=USER,
            transactions=duplicated_operations,
        )

        assert result.created == 1
        assert result.duplicates_skipped == 2
        assert db.query(Transaction).count() == 1

    def test_повторный_импорт_той_же_выписки_не_дублирует_записи(self, db):
        operations = [
            tx(date(2026, 9, 1), 100.0, "Лента"),
            tx(date(2026, 9, 2), 50.5, "Яндекс Такси"),
        ]
        save_transactions(
            db,
            family_id=FAMILY_A,
            user_id=USER,
            transactions=operations,
        )
        result = save_transactions(
            db,
            family_id=FAMILY_A,
            user_id=USER,
            transactions=operations,
        )

        assert result.created == 0
        assert result.duplicates_skipped == 2
        assert db.query(Transaction).count() == 2

    def test_одна_операция_в_разных_семьях_не_считается_дублем(self, db):
        operation = tx(date(2026, 9, 1), 100.0, "Лента")
        save_transactions(
            db,
            family_id=FAMILY_A,
            user_id=USER,
            transactions=[operation],
        )
        result = save_transactions(
            db,
            family_id=FAMILY_B,
            user_id=USER,
            transactions=[operation],
        )

        assert result.created == 1
        assert result.duplicates_skipped == 0
        assert db.query(Transaction).count() == 2

    def test_разные_суммы_не_считаются_дублями(self, db):
        business = tx(date(2026, 9, 1), 100.0, "Лента")
        second = tx(date(2026, 9, 1), 150.0, "Лента")
        result = save_transactions(
            db,
            family_id=FAMILY_A,
            user_id=USER,
            transactions=[business, second],
        )

        assert result.created == 2
        assert db.query(Transaction).count() == 2

    def test_одинаковые_операции_двух_пользователей_не_дублируются(self, db):
        operation = tx(date(2026, 9, 1), 100.0, "Лента")
        first = save_transactions(
            db,
            family_id=FAMILY_A,
            user_id=USER,
            transactions=[operation],
        )
        second = save_transactions(
            db,
            family_id=FAMILY_A,
            user_id=USER_OTHER,
            transactions=[operation],
        )

        assert first.created == 1
        assert second.created == 1
        assert second.duplicates_skipped == 0
        saved = db.query(Transaction).all()
        assert len(saved) == 2
        assert {t.user_id for t in saved} == {USER, USER_OTHER}

    def test_повторный_импорт_только_своего_пользователя_пропускается(self, db):
        operations = [
            tx(date(2026, 9, 1), 100.0, "Лента"),
            tx(date(2026, 9, 2), 50.5, "Яндекс Такси"),
        ]
        save_transactions(
            db,
            family_id=FAMILY_A,
            user_id=USER,
            transactions=operations,
        )
        result = save_transactions(
            db,
            family_id=FAMILY_A,
            user_id=USER,
            transactions=operations,
        )

        assert result.created == 0
        assert result.duplicates_skipped == 2
        assert db.query(Transaction).count() == 2
