# -*- coding: utf-8 -*-

import io

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.models import Family, FamilyMember, User
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


def _csv_bytes() -> bytes:
    return (
        "date,amount,description\n"
        "2026-09-01,100,Лента\n"
        "2026-09-02,50.5,Яндекс Такси\n"
    ).encode("utf-8")


def _upload(client, telegram_id: str, content: bytes, filename: str = "statement.csv"):
    files = {"file": (filename, io.BytesIO(content), "text/csv")}
    return client.post(
        "/api/bot/upload",
        files=files,
        data={"telegram_id": telegram_id},
    )


class TestBotUpload:
    def test_привязанный_пользователь_импортирует_выписку(self, client_db):
        client, session = client_db
        user, family = _prepare(session)

        response = _upload(client, user.telegram_id, _csv_bytes())

        assert response.status_code == 201
        body = response.json()
        assert body["family_id"] == str(family.id)
        assert body["parsed"] == 2
        assert body["created"] == 2
        assert body["duplicates_skipped"] == 0

    def test_повторная_загрузка_пропускает_дубли(self, client_db):
        client, session = client_db
        user, family = _prepare(session)

        first = _upload(client, user.telegram_id, _csv_bytes())
        second = _upload(client, user.telegram_id, _csv_bytes())

        assert first.json()["created"] == 2
        assert second.json()["created"] == 0
        assert second.json()["duplicates_skipped"] == 2

    def test_непривязанный_телеграм_получает_401(self, client_db):
        client, session = client_db
        _prepare(session)

        response = _upload(client, "000000000", _csv_bytes())

        assert response.status_code == 401

    def test_пользователь_без_семьи_получает_400(self, client_db):
        client, session = client_db
        user = _user()
        session.add(user)
        session.commit()

        response = _upload(client, user.telegram_id, _csv_bytes())

        assert response.status_code == 400

    def test_файл_не_csv_отклоняется(self, client_db):
        client, session = client_db
        user, family = _prepare(session)

        response = _upload(
            client, user.telegram_id, b"not a csv", filename="notes.txt"
        )

        assert response.status_code == 400
