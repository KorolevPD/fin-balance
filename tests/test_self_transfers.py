# -*- coding: utf-8 -*-

import io
from datetime import date, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.categorization import CategorizedTransaction
from app.database import get_db
from app.models import Family, FamilyMember, Transaction, User
from app.parsers import extract_account_owner, parse_pdf_bytes
from app.security import create_access_token, hash_password
from app.services.analytics import get_family_summary
from app.services.names import (
    is_transfer_to_self,
    mark_self_transfers,
    parse_person_name,
    parse_transfer_recipient,
)
from app.services.transactions import save_transactions
from main import app

SBER_PDF = Path(__file__).resolve().parents[1] / "pdf_examples" / "sber.pdf"


@pytest.fixture()
def client_db(session_factory):
    session = session_factory()
    app.dependency_overrides[get_db] = lambda: session
    try:
        yield TestClient(app), session
    finally:
        app.dependency_overrides.pop(get_db, None)
        session.close()


class TestExtractAccountOwner:
    def test_извлекает_фио_владельца_из_шапки_pdf(self):
        assert extract_account_owner(SBER_PDF.read_bytes()) == "Иванов Иван Иванович"

    def test_битый_файл_возвращает_none(self):
        assert extract_account_owner(b"this is not a pdf") is None

    def test_пустой_документ_возвращает_none(self):
        from pypdf import PdfWriter

        writer = PdfWriter()
        writer.add_blank_page(width=200, height=200)
        empty_bytes = io.BytesIO()
        writer.write(empty_bytes)

        assert extract_account_owner(empty_bytes.getvalue()) is None

    def test_владелец_из_pdf_попадает_в_парсер_переводов(self):
        transactions = parse_pdf_bytes(SBER_PDF.read_bytes())

        self_transfers = [
            item
            for item in transactions
            if is_transfer_to_self("Иванов Иван Иванович", item.description)
            and item.type == "expense"
        ]
        assert self_transfers
        assert all(
            item.description.startswith("Перевод для И. Иван Иванович")
            for item in self_transfers
        )


class TestParsePersonName:
    def test_разбирает_фамилию_имя_отчество(self):
        signature = parse_person_name("Иванов Иван Иванович")

        assert signature.given_name == "иван"
        assert signature.patronymic == "иванович"
        assert signature.surname_initial == "и"

    def test_разбирает_имя_и_отчество_без_фамилии(self):
        signature = parse_person_name("Иван Иванович")

        assert signature.given_name == "иван"
        assert signature.patronymic == "иванович"
        assert signature.surname_initial is None

    def test_разбирает_имя_и_фамилию(self):
        signature = parse_person_name("Анна Иванова")

        assert signature.given_name == "анна"
        assert signature.surname_initial == "и"

    def test_разбирает_только_имя(self):
        signature = parse_person_name("Иван")

        assert signature.given_name == "иван"
        assert signature.patronymic is None
        assert signature.surname_initial is None

    def test_пустое_имя_не_разбирается(self):
        assert parse_person_name("").given_name is None

    def test_разбирает_латинское_фио(self):
        signature = parse_person_name("Ivanov Ivan Ivanovich")

        assert signature.given_name == "ivan"
        assert signature.patronymic == "ivanovich"
        assert signature.surname_initial == "i"


class TestParseTransferRecipient:
    def test_сбербанк_инициал_фамилии_имя_отчество(self):
        signature = parse_transfer_recipient(
            "Перевод для И. Иван Иванович. Операция по карте"
        )

        assert signature.given_name == "иван"
        assert signature.patronymic == "иванович"
        assert signature.surname_initial == "и"

    def test_перевод_без_инициала(self):
        signature = parse_transfer_recipient("Перевод для Иван Иванович")

        assert signature.given_name == "иван"
        assert signature.patronymic == "иванович"
        assert signature.surname_initial is None

    def test_перевод_имя_фамилия(self):
        signature = parse_transfer_recipient("Перевод для Анна Иванова")

        assert signature.given_name == "анна"
        assert signature.surname_initial == "и"

    def test_латинский_получатель(self):
        signature = parse_transfer_recipient("P2P Ivanov Ivan I.")

        assert signature.given_name == "ivan"
        assert signature.surname_initial == "i"

    def test_не_перевод_возвращает_none(self):
        assert parse_transfer_recipient("Лента") is None
        assert parse_transfer_recipient("SPOTIFY") is None


class TestIsTransferToSelf:
    def test_перевод_самому_себе_по_сбербанку(self):
        assert is_transfer_to_self(
            "Иванов Иван Иванович",
            "Перевод для И. Иван Иванович. Операция по карте",
        )

    def test_перевод_без_инициала_самому_себе(self):
        assert is_transfer_to_self("Иванов Иван Иванович", "Перевод для Иван Иванович")

    def test_инициал_совпадает_с_фамилией_владельца(self):
        assert is_transfer_to_self(
            "Иванов Иван Иванович",
            "Перевод для И. Иван Иванович",
        )

    def test_перевод_другому_человеку_не_распознаётся(self):
        assert not is_transfer_to_self(
            "Иванов Иван Иванович",
            "Перевод для П. Петр Петрович. Операция по карте",
        )

    def test_покупка_не_является_переводом(self):
        assert not is_transfer_to_self("Иванов Иван Иванович", "Лента")

    def test_только_имя_владельца_не_достаточно_для_совпадения(self):
        assert not is_transfer_to_self(
            "Иван",
            "Перевод для И. Иван Иванович. Операция по карте",
        )

    def test_разное_отчество_не_совпадение(self):
        assert not is_transfer_to_self(
            "Иванов Иван Петрович",
            "Перевод для И. Иван Иванович. Операция по карте",
        )

    def test_латинский_перевод_самому_себе(self):
        assert is_transfer_to_self("Ivanov Ivan Ivanovich", "P2P Ivanov Ivan I.")

    def test_пустое_имя_владельца_не_даёт_совпадения(self):
        assert not is_transfer_to_self(
            None, "Перевод для И. Иван Иванович. Операция по карте"
        )


class TestMarkAndSave:
    def test_перевод_самому_себе_помечается(self):
        items = [
            CategorizedTransaction(
                date=date(2026, 9, 1),
                amount=1000.0,
                description="Перевод для И. Иван Иванович. Операция по карте",
                type="expense",
                category="Прочее",
            ),
            CategorizedTransaction(
                date=date(2026, 9, 1),
                amount=200.0,
                description="Лента",
                type="expense",
                category="Прочее",
            ),
        ]
        mark_self_transfers(items, "Иванов Иван Иванович")

        assert items[0].is_self_transfer is True
        assert items[1].is_self_transfer is False

    def test_сохраняется_с_флагом_self_transfer(self, db):
        family = Family(invite_code="SELF001")
        db.add(family)
        user = User(
            email="self@test.ru",
            name="Иванов Иван Иванович",
            password_hash="x",
        )
        db.add(user)
        db.flush()
        db.add(FamilyMember(user_id=user.id, family_id=family.id, role="owner"))
        db.commit()

        result = save_transactions(
            db,
            family_id=family.id,
            user_id=user.id,
            transactions=[
                CategorizedTransaction(
                    date=date(2026, 9, 1),
                    amount=1000.0,
                    description="Перевод для И. Иван Иванович. Операция по карте",
                    type="expense",
                    category="Прочее",
                    is_self_transfer=True,
                )
            ],
        )

        assert result.created == 1
        saved = db.query(Transaction).one()
        assert saved.is_self_transfer is True

    def test_исключается_из_агрегатов_расходов(self, db):
        family = Family(invite_code="SELF002")
        db.add(family)
        user = User(
            email="self2@test.ru",
            name="Иванов Иван Иванович",
            password_hash="x",
        )
        db.add(user)
        db.flush()
        db.add(FamilyMember(user_id=user.id, family_id=family.id, role="owner"))
        db.flush()
        db.add_all(
            [
                Transaction(
                    family_id=family.id,
                    user_id=user.id,
                    date=datetime(2026, 9, 1),
                    amount=1000.0,
                    original_description="Перевод для И. Иван Иванович",
                    is_self_transfer=True,
                ),
                Transaction(
                    family_id=family.id,
                    user_id=user.id,
                    date=datetime(2026, 9, 2),
                    amount=200.0,
                    original_description="Лента",
                    is_self_transfer=False,
                ),
            ]
        )
        db.commit()

        summary = get_family_summary(db, family.id, user_id=user.id)

        assert summary["total_amount"] == 200.0
        assert len(summary["by_category"]) == 1
        assert summary["by_category"][0]["amount"] == 200.0
        assert [item["payee"] for item in summary["top_payees"]] == ["Лента"]
        assert summary["uploaded_files"] == []
        assert summary["family_members"][0]["total_expenses"] == 200.0


class TestImportSelfTransfer:
    def test_импорт_не_загружает_перевод_самому_себе_по_владельцу_из_выписки(
        self, client_db
    ):
        client, session = client_db
        user = User(email="owner@example.com", password_hash=hash_password("secret1"))
        session.add(user)
        session.flush()
        family = Family(invite_code="SELF003")
        session.add(family)
        session.flush()
        session.add(FamilyMember(user_id=user.id, family_id=family.id, role="owner"))
        session.commit()
        token = create_access_token(subject=str(user.id))

        response = client.post(
            f"/api/families/{family.id}/transactions/import",
            files={
                "file": (
                    "statement.pdf",
                    io.BytesIO(SBER_PDF.read_bytes()),
                    "application/pdf",
                )
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 201
        transactions = client.get(
            f"/api/families/{family.id}/transactions",
            headers={"Authorization": f"Bearer {token}"},
        ).json()

        descriptions = {item["original_description"] for item in transactions}
        assert "Перевод для И. Иван Иванович. Операция по карте" not in descriptions
        assert "Перевод от И. Иван Иванович. Операция по карте" not in descriptions

        other_transfer = next(
            item
            for item in transactions
            if item["original_description"]
            == "Перевод от С. Алексей Анатольевич. Операция по карте"
        )
        assert other_transfer["is_self_transfer"] is False

    def test_сводка_не_учитывает_перевод_самому_себе(self, client_db):
        client, session = client_db
        user = User(email="owner2@example.com", password_hash=hash_password("secret1"))
        session.add(user)
        session.flush()
        family = Family(invite_code="SELF004")
        session.add(family)
        session.flush()
        session.add(FamilyMember(user_id=user.id, family_id=family.id, role="owner"))
        session.commit()
        token = create_access_token(subject=str(user.id))

        import_response = client.post(
            f"/api/families/{family.id}/transactions/import",
            files={
                "file": (
                    "statement.pdf",
                    io.BytesIO(SBER_PDF.read_bytes()),
                    "application/pdf",
                )
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert import_response.status_code == 201

        transactions = client.get(
            f"/api/families/{family.id}/transactions",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        expenses = [
            item["amount"]
            for item in transactions
            if item["type"] == "expense" and not item["is_self_transfer"]
        ]
        assert expenses

        summary = client.get(
            f"/api/families/{family.id}/summary",
            headers={"Authorization": f"Bearer {token}"},
        ).json()

        assert summary["total_amount"] == pytest.approx(sum(expenses))
