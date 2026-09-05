# -*- coding: utf-8 -*-

import io

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app.database import get_db
from app.models import User
from app.routers import auth as auth_routes
from app.security import create_access_token, hash_password
from main import app


def _route_exists(method: str, path: str) -> bool:
    for route in app.routes:
        route_match = (
            isinstance(route, APIRoute)
            and route.path == path
            and method in route.methods
        )
        if route_match:
            return True
    return False


def test_приложение_содержит_роуты_профиля():
    assert _route_exists("PATCH", "/api/auth/me")
    assert _route_exists("POST", "/api/auth/me/avatar")
    assert _route_exists("GET", "/api/auth/me/avatar/{stored_name}")


def test_patch_me_возвращает_userout():
    route = next(
        (
            r
            for r in app.routes
            if isinstance(r, APIRoute)
            and r.path == "/api/auth/me"
            and "PATCH" in r.methods
        )
    )
    assert route.response_model is auth_routes.UserOut


def test_поле_avatar_есть_в_модели():
    assert "avatar" in User.__table__.columns


def test_поле_avatar_есть_в_схеме_userout():
    assert "avatar" in auth_routes.UserOut.model_fields


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
        email="profile@example.com",
        password_hash=hash_password("secret1"),
        name="Старое имя",
    )


def _prepare(session):
    user = _user()
    session.add(user)
    session.commit()
    return user


def _token(user) -> str:
    return create_access_token(subject=str(user.id))


def _png_bytes() -> bytes:
    return b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


class TestUpdateProfile:
    def test_update_me_меняет_имя(self, client_db):
        client, session = client_db
        user = _prepare(session)
        token = _token(user)

        response = client.patch(
            "/api/auth/me",
            json={"name": "Новое имя"},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["name"] == "Новое имя"
        assert body["email"] == "profile@example.com"

    def test_update_me_оставляет_avatar(self, client_db):
        client, session = client_db
        user = _prepare(session)
        user.avatar = "some.png"
        session.commit()
        token = _token(user)

        response = client.patch(
            "/api/auth/me",
            json={"name": "Имя"},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert response.json()["avatar"] == "some.png"

    def test_update_me_требует_авторизации(self, client_db):
        client, _ = client_db

        response = client.patch("/api/auth/me", json={"name": "Имя"})

        assert response.status_code == 401


class TestUploadAvatar:
    def test_upload_avatar_возвращает_новый_avatar(self, client_db):
        client, session = client_db
        user = _prepare(session)
        token = _token(user)

        response = client.post(
            "/api/auth/me/avatar",
            files={"file": ("photo.png", io.BytesIO(_png_bytes()), "image/png")},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["avatar"]
        assert body["avatar"].endswith(".png")

    def test_upload_avatar_меняет_старый_файл(self, client_db):
        client, session = client_db
        user = _prepare(session)
        user.avatar = "old.png"
        session.commit()
        token = _token(user)

        response = client.post(
            "/api/auth/me/avatar",
            files={"file": ("photo.jpg", io.BytesIO(_png_bytes()), "image/jpeg")},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert response.json()["avatar"] != "old.png"

    def test_upload_avatar_отклоняет_не_изображение(self, client_db):
        client, session = client_db
        user = _prepare(session)
        token = _token(user)

        response = client.post(
            "/api/auth/me/avatar",
            files={"file": ("doc.txt", io.BytesIO(b"text"), "text/plain")},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 400

    def test_upload_avatar_требует_авторизации(self, client_db):
        client, _ = client_db

        response = client.post(
            "/api/auth/me/avatar",
            files={"file": ("photo.png", io.BytesIO(_png_bytes()), "image/png")},
        )

        assert response.status_code == 401
