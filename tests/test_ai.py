# -*- coding: utf-8 -*-

from datetime import date

import pytest

from fastapi.testclient import TestClient

from app.ai import (
    AIError,
    classify_descriptions,
    decrypt_key,
    encrypt_key,
    generate_advice,
    is_supported,
    normalized_provider,
)
from app.ai import _common
from app.categorization import CategorizedTransaction
from app.services.ai_transactions import enrich_with_ai

DUMMY_KEY = "test-encryption-key-00000000000000000000000000"


@pytest.fixture()
def encryption_key(monkeypatch):
    monkeypatch.setenv("AI_KEY_ENCRYPTION_KEY", DUMMY_KEY)
    yield DUMMY_KEY


def test_encrypt_decrypt_roundtrip(encryption_key):
    plaintext = "AIzaSyVeryLongFakeKey123"
    encrypted = encrypt_key(plaintext)
    assert encrypted != plaintext
    assert decrypt_key(encrypted) == plaintext


def test_decrypt_невалидного_значения_возвращает_none():
    assert decrypt_key("not-a-valid-fernettoken") is None


def test_normalized_provider():
    assert normalized_provider("gemini") == "gemini"
    assert normalized_provider("Gemini") == "gemini"
    assert normalized_provider("google") == "gemini"
    assert normalized_provider("openai_compatible") == "openai_compatible"
    assert normalized_provider("groq") == "openai_compatible"
    assert normalized_provider("unknown") is None
    assert normalized_provider(None) is None


def test_is_supported():
    assert is_supported("gemini") is True
    assert is_supported("openai_compatible") is True
    assert is_supported("unknown") is False


def test_parse_classify_response_корректный_json():
    data = (
        '[{"category": "Продукты", '
        '"cleaned_description": "Продукты в супермаркете"}]'
    )
    results = _common.parse_classify_response(data, expected=1)
    assert len(results) == 1
    assert results[0].category == "Продукты"
    assert results[0].cleaned_description == "Продукты в супермаркете"


def test_parse_classify_response_скобки_в_json():
    raw = (
        "```json\n"
        '[{"category": "Транспорт", '
        '"cleaned_description": "Поездка на метро"}]\n'
        "```"
    )
    results = _common.parse_classify_response(raw, expected=1)
    assert results[0].category == "Транспорт"


def test_parse_classify_response_невалидный_json_бросает():
    with pytest.raises(AIError):
        _common.parse_classify_response("это не json", expected=1)


def test_parse_advice_response_json():
    text = _common.parse_advice_response('{"advice": "Сократите траты на кафе."}')
    assert text == "Сократите траты на кафе."


def test_parse_advice_response_plain_text():
    text = _common.parse_advice_response("Попробуйте откладывать 10% каждый месяц.")
    assert "откладывать" in text


def test_classify_descriptions_gemini_сетевая_ошибка(monkeypatch):
    def fake_post(*args, **kwargs):
        raise RuntimeError("network down")

    monkeypatch.setattr("app.ai.gemini.httpx.post", fake_post)
    with pytest.raises(AIError):
        classify_descriptions(
            ["Покупка продуктов"], api_key="fake", provider="gemini"
        )


def test_classify_descriptions_gemini_успех(monkeypatch):
    class FakeResponse:
        status_code = 200

        @staticmethod
        def json():
            return {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "text": '[{"category": "Продукты", '
                                    '"cleaned_description": "Покупка в магазине"}]'
                                }
                            ]
                        }
                    }
                ]
            }

    def fake_post(*args, **kwargs):
        return FakeResponse()

    monkeypatch.setattr("app.ai.gemini.httpx.post", fake_post)
    results = classify_descriptions(
        ["Покупка продуктов"], api_key="fake", provider="gemini"
    )
    assert len(results) == 1
    assert results[0].category == "Продукты"
    assert results[0].cleaned_description == "Покупка в магазине"


def test_enrich_with_ai_без_ключа_возвращает_как_есть():
    txns = [
        CategorizedTransaction(
            date=date(2026, 1, 1), amount=100.0, description="MAGNIT", type="expense"
        )
    ]
    result = enrich_with_ai(txns, provider="gemini", api_key_encrypted=None)
    assert result == txns


def test_enrich_with_ai_fallback_при_ошибке(encryption_key, monkeypatch):
    key = encrypt_key("fake-key")
    txns = [
        CategorizedTransaction(
            date=date(2026, 1, 1),
            amount=100.0,
            description="Пятёрочка",
            type="expense",
        )
    ]

    def raise_error(*args, **kwargs):
        raise AIError("boom")

    monkeypatch.setattr(
        "app.services.ai_transactions.classify_descriptions", raise_error
    )
    result = enrich_with_ai(txns, provider="gemini", api_key_encrypted=key)
    assert result == txns


def test_gemini_запрос_идет_на_актуальную_модель(monkeypatch):
    class FakeAdviceResponse:
        status_code = 200

        @staticmethod
        def json():
            return {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "text": '{"advice": "Сократите траты на кафе."}'
                                }
                            ]
                        }
                    }
                ]
            }

    captured = {}

    def fake_post(url, *args, **kwargs):
        captured["url"] = url
        return FakeAdviceResponse()

    monkeypatch.setattr("app.ai.gemini.httpx.post", fake_post)
    text = generate_advice(
        {"by_category": {"Продукты": 500.0}},
        api_key="fake",
        provider="gemini",
    )
    assert text == "Сократите траты на кафе."
    assert "gemini-3.6-flash" in captured["url"]
    assert "gemini-2.0-flash" not in captured["url"]


def test_gemini_404_отозванной_модели_бросает_aierror(monkeypatch):
    class NotFoundResponse:
        status_code = 404
        text = (
            '{"error": {"code": 404, "message": "This model '
            'models/gemini-2.0-flash is no longer available", '
            '"status": "NOT_FOUND"}}'
        )

        @staticmethod
        def json():
            return {
                "error": {
                    "code": 404,
                    "message": "This model models/gemini-2.0-flash "
                    "is no longer available. Please update your code "
                    "to use models/gemini-3.6-flash",
                    "status": "NOT_FOUND",
                }
            }

    def fake_post(url, *args, **kwargs):
        return NotFoundResponse()

    monkeypatch.setattr("app.ai.gemini.httpx.post", fake_post)
    with pytest.raises(AIError) as exc_info:
        generate_advice(
            {"by_category": {"Продукты": 500.0}},
            api_key="fake",
            provider="gemini",
        )
    assert "HTTP 404" in str(exc_info.value)


class FakeGeminiResponse:
    """Ответ Gemini API, всегда возвращающий категорию «Продукты»."""

    status_code = 200

    @staticmethod
    def json():
        return {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": '[{"category": "Продукты", '
                                '"cleaned_description": "Покупка в магазине"}, '
                                '{"category": "Продукты", '
                                '"cleaned_description": "Ещё покупка"}]'
                            }
                        ]
                    }
                }
            ]
        }


def _import_via_api(session, monkeypatch):
    """Вспомогательный тест-клиент: создаёт пользователя с AI-ключом."""
    import io

    from app.database import get_db
    from app.models import Family, FamilyMember, User
    from app.security import create_access_token, hash_password
    from main import app

    monkeypatch.setenv("AI_KEY_ENCRYPTION_KEY", DUMMY_KEY)

    user = User(
        email="ai-import@example.com",
        password_hash=hash_password("secret1"),
        ai_provider="gemini",
        ai_api_key_encrypted=encrypt_key("fake-key"),
    )
    session.add(user)
    session.flush()
    family = Family(invite_code="AIIMPORT1")
    session.add(family)
    session.flush()
    session.add(FamilyMember(user_id=user.id, family_id=family.id, role="owner"))
    session.commit()

    app.dependency_overrides[get_db] = lambda: session
    client = TestClient(app)
    token = create_access_token(subject=str(user.id))
    csv_bytes = (
        "date,amount,description\n"
        "2026-09-01,120,Лента\n"
        "2026-09-02,60,Яндекс Такси\n"
    ).encode("utf-8")
    files = {"file": ("statement.csv", io.BytesIO(csv_bytes), "text/csv")}
    resp = client.post(
        f"/api/families/{family.id}/transactions/import",
        files=files,
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp, client, token, str(family.id)


def test_импорт_с_ai_сохраняет_clean_описание(monkeypatch, session_factory):
    from app.database import get_db
    from main import app

    monkeypatch.setattr(
        "app.ai.gemini.httpx.post", lambda *a, **k: FakeGeminiResponse()
    )
    session = session_factory()
    try:
        resp, client, token, family_id = _import_via_api(session, monkeypatch)
        assert resp.status_code == 201
        assert resp.json()["created"] == 2

        got = client.get(
            f"/api/families/{family_id}/transactions",
            headers={"Authorization": f"Bearer {token}"},
        )
        body = got.json()
        assert len(body) == 2
        descriptions = {item["cleaned_description"] for item in body}
        assert descriptions == {"Покупка в магазине", "Ещё покупка"}
        assert {item["category"] for item in body} == {"Продукты"}
    finally:
        app.dependency_overrides.pop(get_db, None)
        session.close()
