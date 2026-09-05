# -*- coding: utf-8 -*-

from fastapi.routing import APIRoute

from main import app
from app.models.models import BotLink


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


def test_приложение_содержит_роуты_бота():
    assert _route_exists("POST", "/api/bot/link-code")
    assert _route_exists("POST", "/api/bot/confirm")
    assert _route_exists("GET", "/api/bot/me")


def test_поле_botlink_соответствует_модели():
    assert BotLink.__tablename__ == "bot_links"
    assert "code" in BotLink.__table__.columns
    assert "user_id" in BotLink.__table__.columns
    assert "telegram_id" in BotLink.__table__.columns
    assert "expires_at" in BotLink.__table__.columns
