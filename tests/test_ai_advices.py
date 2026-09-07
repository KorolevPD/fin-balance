# -*- coding: utf-8 -*-

from fastapi.testclient import TestClient
from app.database import get_db
from app.models import Family, FamilyMember, User
from app.security import create_access_token, hash_password
from main import app
import pytest

from app.ai import encrypt_key

DUMMY_KEY = "test-encryption-key-00000000000000000000000000"


@pytest.fixture()
def encryption_key(monkeypatch):
    monkeypatch.setenv("AI_KEY_ENCRYPTION_KEY", DUMMY_KEY)


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
        email="ai@example.com",
        password_hash=hash_password("secret1"),
    )


def _family():
    return Family(invite_code="AIDEMO01")


def _prepare(session, user=None, family=None, ai_key=None, provider="gigachat"):
    user = user or _user()
    if ai_key:
        user.ai_provider = provider
        user.ai_api_key_encrypted = encrypt_key(ai_key)
    session.add(user)
    session.flush()
    family = family or _family()
    session.add(family)
    session.flush()
    session.add(FamilyMember(user_id=user.id, family_id=family.id, role="owner"))
    session.commit()
    return user, family


def _token(user) -> str:
    return create_access_token(subject=str(user.id))


class TestListAdvices:
    def test_список_советов_пуст_вначале(self, encryption_key, client_db):
        client, session = client_db
        user, family = _prepare(session)
        token = _token(user)

        response = client.get(
            f"/api/families/{family.id}/advices",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert response.json() == []

    def test_список_требует_авторизации(self, encryption_key, client_db):
        client, session = client_db
        _, family = _prepare(session)

        response = client.get(f"/api/families/{family.id}/advices")

        assert response.status_code == 401

    def test_не_участник_получает_403(self, encryption_key, client_db):
        client, session = client_db
        user = _user()
        session.add(user)
        session.flush()
        family = _family()
        session.add(family)
        session.commit()
        token = _token(user)

        response = client.get(
            f"/api/families/{family.id}/advices",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 403


class TestCreateAdvice:
    def test_генерация_без_ключа_возвращает_400(self, encryption_key, client_db):
        client, session = client_db
        user, family = _prepare(session)
        token = _token(user)

        response = client.post(
            f"/api/families/{family.id}/advices",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 400

    def test_новый_совет_сохраняется(  # pylint: disable=unused-argument
        self, encryption_key, client_db, monkeypatch
    ):
        client, session = client_db
        user, family = _prepare(session, ai_key="fake-key")
        token = _token(user)

        monkeypatch.setattr(
            "app.routers.ai.generate_advice",
            lambda *args, **kwargs: "Сократите траты на кафе.",
        )

        response = client.post(
            f"/api/families/{family.id}/advices",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 201
        body = response.json()["advice"]
        assert body["text"] == "Сократите траты на кафе."
        assert body["provider"] == "gigachat"

    def test_советы_накапливаются(
        self,
        encryption_key,
        client_db,
        monkeypatch,
    ):
        client, session = client_db
        user, family = _prepare(session, ai_key="fake-key")
        token = _token(user)

        monster_advice = iter(["Совет первый", "Совет второй"])

        def fake_advice(*args, **kwargs):
            return next(monster_advice)

        monkeypatch.setattr("app.routers.ai.generate_advice", fake_advice)

        client.post(
            f"/api/families/{family.id}/advices",
            headers={"Authorization": f"Bearer {token}"},
        )
        client.post(
            f"/api/families/{family.id}/advices",
            headers={"Authorization": f"Bearer {token}"},
        )

        response = client.get(
            f"/api/families/{family.id}/advices",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        texts = [item["text"] for item in response.json()]
        assert texts == ["Совет второй", "Совет первый"]

    def test_советы_заменяются_при_replace(
        self,
        encryption_key,
        client_db,
        monkeypatch,
    ):
        client, session = client_db
        user, family = _prepare(session, ai_key="fake-key")
        token = _token(user)

        monster_advice = iter(["Совет первый", "Совет второй"])

        def fake_advice(*args, **kwargs):
            return next(monster_advice)

        monkeypatch.setattr("app.routers.ai.generate_advice", fake_advice)

        client.post(
            f"/api/families/{family.id}/advices",
            params={"replace": True},
            headers={"Authorization": f"Bearer {token}"},
        )
        client.post(
            f"/api/families/{family.id}/advices",
            params={"replace": True},
            headers={"Authorization": f"Bearer {token}"},
        )

        response = client.get(
            f"/api/families/{family.id}/advices",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        texts = [item["text"] for item in response.json()]
        assert texts == ["Совет второй"]

    def test_генерация_требует_авторизации(self, encryption_key, client_db):
        client, session = client_db
        _, family = _prepare(session, ai_key="fake-key")

        response = client.post(f"/api/families/{family.id}/advices")

        assert response.status_code == 401


class TestServerKeyAdvice:
    def test_совет_генерируется_серверным_ключом_без_ключа_пользователя(
        self, encryption_key, client_db, monkeypatch
    ):
        monkeypatch.setenv("GIGACHAT_API_KEY", "Server-GigaChat-Key-123")
        client, session = client_db
        user, family = _prepare(session)
        token = _token(user)

        captured = {}

        def fake_advice(summary, api_key, provider, base_url):
            captured["api_key"] = api_key
            captured["provider"] = provider
            return "Совет от серверного ключа."

        monkeypatch.setattr("app.routers.ai.generate_advice", fake_advice)

        response = client.post(
            f"/api/families/{family.id}/advices",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 201
        body = response.json()["advice"]
        assert body["text"] == "Совет от серверного ключа."
        assert captured["api_key"] == "Server-GigaChat-Key-123"
        assert captured["provider"] == "gigachat"
