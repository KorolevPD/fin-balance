# -*- coding: utf-8 -*-

from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.models import Family, FamilyMember, User
from app.services import save_transactions
from app.categorization import CategorizedTransaction
from main import app


@pytest.fixture()
def client_db(session_factory):
    session = session_factory()
    app.dependency_overrides[get_db] = lambda: session
    try:
        yield TestClient(app), session
    finally:
        app.dependency_overrides.pop(get_db, None)
        session.close()


def _user():
    return User(
        email="user@example.com",
        telegram_id="123456789",
        password_hash="not-needed-in-test",
    )


def _family():
    return Family(invite_code="TESTCODE1")


def _prepare(session, with_transactions: bool = True):
    user = _user()
    session.add(user)
    session.flush()
    family = _family()
    session.add(family)
    session.flush()
    session.add(FamilyMember(user_id=user.id, family_id=family.id, role="owner"))
    session.commit()

    if with_transactions:
        save_transactions(
            session,
            family_id=family.id,
            user_id=user.id,
            transactions=[
                CategorizedTransaction(
                    date=date(2026, 9, 1),
                    amount=100.0,
                    description="Лента",
                    type="expense",
                    category="Продукты",
                ),
                CategorizedTransaction(
                    date=date(2026, 9, 2),
                    amount=50.0,
                    description="Яндекс Такси",
                    type="expense",
                    category="Транспорт",
                ),
            ],
        )
    return user, family


def _summary(client, telegram_id: str):
    return client.get("/api/bot/summary", params={"telegram_id": telegram_id})


class TestBotSummary:
    def test_привязанный_пользователь_получает_сводку(self, client_db):
        client, session = client_db
        user, family = _prepare(session)

        response = _summary(client, user.telegram_id)

        assert response.status_code == 200
        body = response.json()
        assert body["family_id"] == str(family.id)
        assert body["total_amount"] == 150.0
        categories = {item["category"]: item for item in body["by_category"]}
        assert categories["Продукты"]["amount"] == 100.0
        assert categories["Продукты"]["count"] == 1
        assert categories["Транспорт"]["amount"] == 50.0

    def test_непривязанный_телеграм_получает_401(self, client_db):
        client, session = client_db
        _prepare(session)

        response = _summary(client, "000000000")

        assert response.status_code == 401

    def test_пользователь_без_семьи_получает_400(self, client_db):
        client, session = client_db
        user = _user()
        session.add(user)
        session.commit()

        response = _summary(client, user.telegram_id)

        assert response.status_code == 400

    def test_пустая_сводка_без_транзакций(self, client_db):
        client, session = client_db
        user, family = _prepare(session, with_transactions=False)

        response = _summary(client, user.telegram_id)

        assert response.status_code == 200
        body = response.json()
        assert body["family_id"] == str(family.id)
        assert body["total_amount"] == 0.0
        assert body["by_category"] == []
        assert body["top_payees"] == []
