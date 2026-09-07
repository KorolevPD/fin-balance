# -*- coding: utf-8 -*-

import io

from fastapi.testclient import TestClient
from app.database import get_db
from app.models import AiAdvice, Family, FamilyMember, User
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


def _add_advice(session, family_id, user_id, scope, text):
    session.add(
        AiAdvice(
            family_id=family_id,
            user_id=user_id,
            scope=scope,
            text=text,
        )
    )
    session.commit()


def _add_member(session, user, family_id):
    session.add(FamilyMember(user_id=user.id, family_id=family_id, role="member"))
    session.commit()


def _api_user(email="second@example.com"):
    return User(email=email, password_hash=hash_password("secret1"))


class TestAdviceScope:
    def test_личные_советы_видны_только_владельцу(self, encryption_key, client_db):
        client, session = client_db
        owner, family = _prepare(session)
        other = _api_user()
        session.add(other)
        session.flush()
        _add_member(session, other, family.id)
        owner_token = _token(owner)
        other_token = _token(other)

        _add_advice(session, family.id, owner.id, "family", "Семейный совет владельца")
        _add_advice(session, family.id, owner.id, "personal", "Личный совет владельца")
        _add_advice(session, family.id, other.id, "family", "Семейный совет участника")
        _add_advice(session, family.id, other.id, "personal", "Личный совет участника")

        family_list = client.get(
            f"/api/families/{family.id}/advices",
            params={"scope": "family"},
            headers={"Authorization": f"Bearer {owner_token}"},
        ).json()
        assert {item["text"] for item in family_list} == {
            "Семейный совет владельца",
            "Семейный совет участника",
        }

        owner_personal = client.get(
            f"/api/families/{family.id}/advices",
            params={"scope": "personal"},
            headers={"Authorization": f"Bearer {owner_token}"},
        ).json()
        assert [item["text"] for item in owner_personal] == ["Личный совет владельца"]

        other_personal = client.get(
            f"/api/families/{family.id}/advices",
            params={"scope": "personal"},
            headers={"Authorization": f"Bearer {other_token}"},
        ).json()
        assert [item["text"] for item in other_personal] == ["Личный совет участника"]

    def test_список_без_scope_не_отдаёт_чужие_личные_советы(
        self, encryption_key, client_db
    ):
        client, session = client_db
        owner, family = _prepare(session)
        other = _api_user()
        session.add(other)
        session.flush()
        _add_member(session, other, family.id)
        owner_token = _token(owner)

        _add_advice(session, family.id, other.id, "family", "Семейный совет участника")
        _add_advice(session, family.id, other.id, "personal", "Личный совет участника")

        response = client.get(
            f"/api/families/{family.id}/advices",
            headers={"Authorization": f"Bearer {owner_token}"},
        )

        assert response.status_code == 200
        texts = [item["text"] for item in response.json()]
        assert texts == ["Семейный совет участника"]

    def test_личный_совет_генерируется_по_личной_сводке(
        self, encryption_key, client_db, monkeypatch
    ):
        monkeypatch.setattr(
            "app.routers.transactions.regenerate_advice_in_background",
            lambda **kwargs: None,
        )
        client, session = client_db
        owner, family = _prepare(session, ai_key="fake-key")
        other = _api_user()
        session.add(other)
        session.flush()
        _add_member(session, other, family.id)
        owner_token = _token(owner)

        captured = {}

        def fake_advice(summary, api_key, provider, base_url):
            captured["summary"] = summary
            return "Личный совет."

        monkeypatch.setattr("app.routers.ai.generate_advice", fake_advice)

        def _expense_csv(negative_amount):
            return (
                f"date,amount,description\n2026-09-01,{negative_amount},Продукты\n"
            ).encode("utf-8")

        def _upload(token, amount):
            files = {"file": ("a.csv", io.BytesIO(_expense_csv(amount)), "text/csv")}
            return client.post(
                f"/api/families/{family.id}/transactions/import",
                params={"advice_scope": "personal"},
                files=files,
                headers={"Authorization": f"Bearer {token}"},
            )

        _upload(owner_token, -100)
        _upload(_token(other), -500)
        client.post(
            f"/api/families/{family.id}/advices",
            params={"scope": "personal"},
            headers={"Authorization": f"Bearer {owner_token}"},
        )

        assert captured["summary"]["total_amount"] == 100.0

        client.post(
            f"/api/families/{family.id}/advices",
            params={"scope": "family"},
            headers={"Authorization": f"Bearer {owner_token}"},
        )

        assert captured["summary"]["total_amount"] == 600.0

    def test_создание_совета_сохраняет_scope(
        self, encryption_key, client_db, monkeypatch
    ):
        client, session = client_db
        user, family = _prepare(session, ai_key="fake-key")
        token = _token(user)

        monkeypatch.setattr(
            "app.routers.ai.generate_advice",
            lambda *args, **kwargs: "Совет для личного режима.",
        )

        response = client.post(
            f"/api/families/{family.id}/advices",
            params={"scope": "personal"},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 201
        body = response.json()["advice"]
        assert body["scope"] == "personal"

        rows = (
            session.query(AiAdvice)
            .filter(AiAdvice.family_id == family.id)
            .all()
        )
        assert [row.scope for row in rows] == ["personal"]


class TestAdviceInvalidation:
    def _advice_count(self, session, family_id):
        return (
            session.query(AiAdvice)
            .filter(AiAdvice.family_id == family_id)
            .count()
        )

    def test_импорт_удаляет_советы_и_запускает_перегенерацию(
        self, encryption_key, client_db, monkeypatch
    ):
        client, session = client_db
        user, family = _prepare(session)
        token = _token(user)
        _add_advice(session, family.id, user.id, "family", "Старый семейный совет")
        _add_advice(session, family.id, user.id, "personal", "Старый личный совет")

        calls = []

        def fake_regenerate(**kwargs):
            calls.append(kwargs)

        monkeypatch.setattr(
            "app.routers.transactions.regenerate_advice_in_background",
            fake_regenerate,
        )

        csv_bytes = (
            "date,amount,description\n2026-09-01,-100,Лента\n"
        ).encode("utf-8")
        files = {"file": ("statement.csv", io.BytesIO(csv_bytes), "text/csv")}
        response = client.post(
            f"/api/families/{family.id}/transactions/import",
            params={"advice_scope": "personal"},
            files=files,
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 201
        assert self._advice_count(session, family.id) == 0
        assert calls and calls[0]["scope"] == "personal"
        assert calls[0]["family_id"] == family.id
        assert calls[0]["user_id"] == user.id

    def test_импорт_дублей_не_инвалидирует_советы(
        self, encryption_key, client_db, monkeypatch
    ):
        client, session = client_db
        user, family = _prepare(session)
        token = _token(user)

        csv_bytes = (
            "date,amount,description\n2026-09-01,-100,Лента\n"
        ).encode("utf-8")
        files = {"file": ("statement.csv", io.BytesIO(csv_bytes), "text/csv")}
        client.post(
            f"/api/families/{family.id}/transactions/import",
            files=files,
            headers={"Authorization": f"Bearer {token}"},
        )
        _add_advice(session, family.id, user.id, "family", "Актуальный совет")
        _add_advice(session, family.id, user.id, "personal", "Актуальный личный совет")

        monkeypatch.setattr(
            "app.routers.transactions.regenerate_advice_in_background",
            lambda **kwargs: None,
        )

        duplicate = client.post(
            f"/api/families/{family.id}/transactions/import",
            files=files,
            headers={"Authorization": f"Bearer {token}"},
        )

        assert duplicate.status_code == 201
        assert duplicate.json()["created"] == 0
        assert self._advice_count(session, family.id) == 2

    def test_правка_операции_удаляет_советы_владельца(
        self, encryption_key, client_db, monkeypatch
    ):
        client, session = client_db
        owner, family = _prepare(session)
        owner_token = _token(owner)

        csv_bytes = (
            "date,amount,description\n2026-09-01,-100,Лента\n"
        ).encode("utf-8")
        files = {"file": ("statement.csv", io.BytesIO(csv_bytes), "text/csv")}
        client.post(
            f"/api/families/{family.id}/transactions/import",
            files=files,
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        txn_id = client.get(
            f"/api/families/{family.id}/transactions",
            headers={"Authorization": f"Bearer {owner_token}"},
        ).json()[0]["id"]

        other = _api_user()
        session.add(other)
        session.flush()
        _add_member(session, other, family.id)
        _add_advice(session, family.id, owner.id, "family", "Семейный совет")
        _add_advice(session, family.id, owner.id, "personal", "Личный совет владельца")
        _add_advice(session, family.id, other.id, "personal", "Личный совет участника")

        calls = []
        monkeypatch.setattr(
            "app.routers.transactions.regenerate_advice_in_background",
            lambda **kwargs: calls.append(kwargs),
        )

        response = client.patch(
            f"/api/families/{family.id}/transactions/{txn_id}",
            json={"category": "Рестораны и кафе"},
            headers={"Authorization": f"Bearer {owner_token}"},
        )

        assert response.status_code == 200
        texts = [
            row.text
            for row in session.query(AiAdvice)
            .filter(AiAdvice.family_id == family.id)
            .all()
        ]
        assert texts == ["Личный совет участника"]
        assert calls and calls[0]["scope"] == "personal"

    def test_правка_без_изменений_не_инвалидирует_советы(
        self, encryption_key, client_db, monkeypatch
    ):
        client, session = client_db
        user, family = _prepare(session)
        token = _token(user)

        csv_bytes = (
            "date,amount,description\n2026-09-01,-100,Лента\n"
        ).encode("utf-8")
        files = {"file": ("statement.csv", io.BytesIO(csv_bytes), "text/csv")}
        client.post(
            f"/api/families/{family.id}/transactions/import",
            files=files,
            headers={"Authorization": f"Bearer {token}"},
        )
        txn = client.get(
            f"/api/families/{family.id}/transactions",
            headers={"Authorization": f"Bearer {token}"},
        ).json()[0]
        _add_advice(session, family.id, user.id, "family", "Актуальный совет")
        _add_advice(session, family.id, user.id, "personal", "Актуальный личный совет")

        monkeypatch.setattr(
            "app.routers.transactions.regenerate_advice_in_background",
            lambda **kwargs: None,
        )

        response = client.patch(
            f"/api/families/{family.id}/transactions/{txn['id']}",
            json={
                "cleaned_description": None,
                "category": txn["category"],
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert self._advice_count(session, family.id) == 2

    def test_удаление_выписки_удаляет_советы(
        self, encryption_key, client_db, monkeypatch
    ):
        client, session = client_db
        user, family = _prepare(session)
        token = _token(user)

        csv_bytes = (
            "date,amount,description\n2026-09-01,-100,Лента\n"
        ).encode("utf-8")
        files = {"file": ("statement.csv", io.BytesIO(csv_bytes), "text/csv")}
        client.post(
            f"/api/families/{family.id}/transactions/import",
            files=files,
            headers={"Authorization": f"Bearer {token}"},
        )
        _add_advice(session, family.id, user.id, "family", "Старый семейный совет")
        _add_advice(session, family.id, user.id, "personal", "Старый личный совет")

        calls = []
        monkeypatch.setattr(
            "app.routers.transactions.regenerate_advice_in_background",
            lambda **kwargs: calls.append(kwargs),
        )

        response = client.delete(
            f"/api/families/{family.id}/transactions",
            params={"source_file": "statement.csv", "advice_scope": "family"},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert self._advice_count(session, family.id) == 0
        assert calls and calls[0]["scope"] == "family"

    def test_фоновая_перегенерация_создаёт_совет_после_импорта(
        self, encryption_key, client_db, monkeypatch
    ):
        monkeypatch.setattr(
            "app.services.ai_advices.generate_advice",
            lambda *args, **kwargs: "Новый совет после импорта.",
        )
        client, session = client_db
        user, family = _prepare(session, ai_key="fake-key")
        token = _token(user)

        csv_bytes = (
            "date,amount,description\n2026-09-01,-100,Лента\n"
        ).encode("utf-8")
        files = {"file": ("statement.csv", io.BytesIO(csv_bytes), "text/csv")}
        response = client.post(
            f"/api/families/{family.id}/transactions/import",
            params={"advice_scope": "personal"},
            files=files,
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 201
        advices = client.get(
            f"/api/families/{family.id}/advices",
            params={"scope": "personal"},
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        assert [item["text"] for item in advices] == ["Новый совет после импорта."]
        assert advices[0]["scope"] == "personal"
