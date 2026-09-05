# -*- coding: utf-8 -*-

import io

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.models import Family, FamilyMember, User
from app.security import create_access_token, hash_password
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
        password_hash=hash_password("secret1"),
    )


def _family():
    return Family(name="Моя семья", invite_code="TESTCODE1")


def _prepare(session):
    user = _user()
    session.add(user)
    session.flush()
    family = _family()
    session.add(family)
    session.flush()
    session.add(FamilyMember(user_id=user.id, family_id=family.id, role="owner"))
    session.commit()
    return user, family


def _token(user) -> str:
    return create_access_token(subject=str(user.id))


def _csv_bytes() -> bytes:
    return (
        "date,amount,description\n"
        "2026-09-01,100,Лента\n"
        "2026-09-02,50.5,Яндекс Такси\n"
    ).encode("utf-8")


def _upload(client, family_id: str, token: str, content: bytes):
    files = {"file": ("statement.csv", io.BytesIO(content), "text/csv")}
    return client.post(
        f"/api/families/{family_id}/transactions/import",
        files=files,
        headers={"Authorization": f"Bearer {token}"},
    )


class TestImportTransactions:
    def test_импорт_создаёт_транзакции_в_семье(self, client_db):
        client, session = client_db
        user, family = _prepare(session)
        token = _token(user)

        response = _upload(client, family.id, token, _csv_bytes())

        assert response.status_code == 201
        body = response.json()
        assert body["parsed"] == 2
        assert body["created"] == 2
        assert body["duplicates_skipped"] == 0

    def test_повторный_импорт_пропускает_дубли(self, client_db):
        client, session = client_db
        user, family = _prepare(session)
        token = _token(user)

        first = _upload(client, family.id, token, _csv_bytes())
        second = _upload(client, family.id, token, _csv_bytes())

        assert first.json()["created"] == 2
        assert second.json()["created"] == 0
        assert second.json()["duplicates_skipped"] == 2

    def test_не_участник_семьи_получает_403(self, client_db):
        client, session = client_db
        user = _user()
        session.add(user)
        session.flush()
        family = _family()
        session.add(family)
        session.commit()
        token = _token(user)

        response = _upload(client, family.id, token, _csv_bytes())

        assert response.status_code == 403

    def test_импорт_требует_авторизации(self, client_db):
        client, session = client_db
        _, family = _prepare(session)

        response = _upload(client, family.id, "", _csv_bytes())

        assert response.status_code == 401


class TestListTransactions:
    def test_список_возвращает_сохранённые_транзакции_с_категорией(self, client_db):
        client, session = client_db
        user, family = _prepare(session)
        token = _token(user)
        _upload(client, family.id, token, _csv_bytes())

        response = client.get(
            f"/api/families/{family.id}/transactions",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 2
        assert {item["category"] for item in body} == {"Продукты", "Транспорт"}
        assert {item["original_description"] for item in body} == {
            "Лента",
            "Яндекс Такси",
        }
