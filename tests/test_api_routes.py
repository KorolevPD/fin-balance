# -*- coding: utf-8 -*-

from fastapi.routing import APIRoute

from main import app
from app.routers import auth as auth_routes


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


def test_приложение_импортируется_и_содержит_роуты_авторизации():
    assert _route_exists("POST", "/api/auth/register")
    assert _route_exists("POST", "/api/auth/login")
    assert _route_exists("GET", "/api/auth/me")


def test_register_возвращает_токен_как_ожидает_фронтенд():
    route = next(
        (
            r
            for r in app.routes
            if isinstance(r, APIRoute) and r.path == "/api/auth/register"
        )
    )
    assert route.response_model is auth_routes.TokenOut


def test_приложение_содержит_роуты_семей():
    assert _route_exists("POST", "/api/families")
    assert _route_exists("POST", "/api/families/join")
    assert _route_exists("GET", "/api/families/my")
    assert _route_exists("GET", "/api/families/{family_id}/members")


def test_приложение_содержит_роут_загрузки_csv():
    assert _route_exists("POST", "/api/upload")
