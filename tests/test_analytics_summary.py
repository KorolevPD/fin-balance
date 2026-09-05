# -*- coding: utf-8 -*-

from datetime import datetime

from app.categorization.rules import DEFAULT_CATEGORY
from app.models import Base, Category, Family, FamilyMember, Transaction, User
from app.security import hash_password
from app.services.analytics import get_family_summary


def _prepare(session):
    user1 = User(email="a@test.ru", name="Анна", password_hash=hash_password("secret1"))
    user2 = User(email="b@test.ru", password_hash=hash_password("secret1"))
    session.add_all([user1, user2])
    session.flush()

    family = Family(name="Семья", invite_code="SMOKE1")
    session.add(family)
    session.flush()

    session.add(FamilyMember(user_id=user1.id, family_id=family.id, role="owner"))
    session.add(FamilyMember(user_id=user2.id, family_id=family.id, role="member"))

    category = Category(name=DEFAULT_CATEGORY)
    session.add(category)
    session.flush()

    session.add_all(
        [
            Transaction(
                family_id=family.id,
                user_id=user1.id,
                category_id=category.id,
                date=datetime(2026, 1, 5),
                amount=100.0,
                original_description="Лента",
                source_file="january.csv",
            ),
            Transaction(
                family_id=family.id,
                user_id=user1.id,
                category_id=category.id,
                date=datetime(2026, 1, 25),
                amount=50.0,
                original_description="Такси",
                source_file="january.csv",
            ),
            Transaction(
                family_id=family.id,
                user_id=user2.id,
                category_id=category.id,
                date=datetime(2026, 2, 10),
                amount=200.0,
                original_description="Аптека",
                source_file="february.csv",
            ),
        ]
    )
    session.commit()
    return user1, user2, family


class TestFamilyMembersAggregations:
    def test_члены_семьи_отсортированы_по_тратам(self, db):
        user1, user2, family = _prepare(db)

        summary = get_family_summary(db, family.id, user_id=user1.id)

        members = summary["family_members"]
        assert len(members) == 2
        assert members[0]["name"] == "b@test.ru"  # Пётр второй
        assert members[0]["total_expenses"] == 200.0
        assert members[1]["name"] == "Анна"
        assert members[1]["total_expenses"] == 150.0

    def test_имя_берётся_из_pole_name_или_email(self, db):
        _, _, family = _prepare(db)

        members = get_family_summary(db, family.id)["family_members"]

        names = {m["name"] for m in members}
        assert "Анна" in names  # задано явно
        assert "b@test.ru" in names  # name пустое -> email

    def test_член_без_транзакций_попадает_с_нулевыми_тратами(self, db):
        user1, _, family = _prepare(db)
        user3 = User(email="c@test.ru", name="Мария", password_hash=hash_password("secret1"))
        db.add(user3)
        db.flush()
        db.add(FamilyMember(user_id=user3.id, family_id=family.id, role="member"))
        db.commit()

        summary = get_family_summary(db, family.id, user_id=user1.id)

        by_name = {m["name"]: m["total_expenses"] for m in summary["family_members"]}
        assert by_name["Мария"] == 0.0
        assert len(summary["family_members"]) == 3


class TestIncomeExcluded:
    def test_доходы_не_входят_в_расходы_и_категории(self, db):
        user1, _, family = _prepare(db)
        category = db.query(Category).one()
        db.add(
            Transaction(
                family_id=family.id,
                user_id=user1.id,
                category_id=category.id,
                date=datetime(2026, 1, 10),
                amount=1000.0,
                type="income",
                original_description="Зарплата",
                source_file="january.csv",
            )
        )
        db.commit()

        summary = get_family_summary(db, family.id, user_id=user1.id)

        assert summary["total_amount"] == 350.0
        assert summary["by_category"][0]["amount"] == 350.0
        assert "Зарплата" not in {p["payee"] for p in summary["top_payees"]}
        members = {m["name"]: m["total_expenses"] for m in summary["family_members"]}
        assert members["Анна"] == 150.0
        assert members["b@test.ru"] == 200.0

    def test_период_файла_учитывает_доходы(self, db):
        user1, _, family = _prepare(db)
        category = db.query(Category).one()
        db.add(
            Transaction(
                family_id=family.id,
                user_id=user1.id,
                category_id=category.id,
                date=datetime(2026, 1, 30),
                amount=1000.0,
                type="income",
                original_description="Зарплата",
                source_file="january.csv",
            )
        )
        db.commit()

        file_info = get_family_summary(db, family.id, user_id=user1.id)[
            "uploaded_files"
        ][0]

        assert file_info["period_end"] == "2026-01-30"
        assert file_info["operations_count"] == 3


class TestUploadedFilesAggregations:
    def test_файлы_только_текущего_пользователя(self, db):
        user1, user2, family = _prepare(db)

        summary = get_family_summary(db, family.id, user_id=user1.id)

        assert len(summary["uploaded_files"]) == 1
        assert summary["uploaded_files"][0]["filename"] == "january.csv"

        summary2 = get_family_summary(db, family.id, user_id=user2.id)
        assert len(summary2["uploaded_files"]) == 1
        assert summary2["uploaded_files"][0]["filename"] == "february.csv"

    def test_период_и_количество_операций_файла(self, db):
        user1, _, family = _prepare(db)

        file_info = get_family_summary(db, family.id, user_id=user1.id)[
            "uploaded_files"
        ][0]

        assert file_info["period_start"] == "2026-01-05"
        assert file_info["period_end"] == "2026-01-25"
        assert file_info["operations_count"] == 2

    def test_без_user_id_файлы_пусты(self, db):
        _, _, family = _prepare(db)

        summary = get_family_summary(db, family.id)

        assert summary["uploaded_files"] == []
        assert len(summary["family_members"]) == 2