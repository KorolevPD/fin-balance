# -*- coding: utf-8 -*-

from datetime import date

import httpx
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
from app.services.ai_transactions import (
    _ALLOWED_CATEGORIES,
    _normalize_category,
    enrich_with_ai,
)

DUMMY_KEY = "test-encryption-key-00000000000000000000000000"


class _OAuthResponse:
    status_code = 200

    @staticmethod
    def json():
        return {"access_token": "token-123", "expires_at": 1234567890}


class _ChatResponse:
    def __init__(self, content, status_code=200):
        self.status_code = status_code
        self._content = content
        self.text = content

    def json(self):
        return {
            "choices": [{"message": {"content": self._content}}],
        }


class _ErrorResponse:
    def __init__(self, status_code, text=""):
        self.status_code = status_code
        self.text = text

    def json(self):
        return {"error": {"message": self.text}}


def _fake_gigachat_post(chat_text, chat_status=200):
    def fake_post(url, *args, **kwargs):
        if "oauth" in url:
            return _OAuthResponse()
        return _ChatResponse(chat_text, chat_status)

    return fake_post


@pytest.fixture()
def encryption_key(monkeypatch):
    monkeypatch.setenv("AI_KEY_ENCRYPTION_KEY", DUMMY_KEY)
    yield DUMMY_KEY


def test_encrypt_decrypt_roundtrip(encryption_key):
    plaintext = "Авторизационный-ключ-GigaChat"
    encrypted = encrypt_key(plaintext)
    assert encrypted != plaintext
    assert decrypt_key(encrypted) == plaintext


def test_decrypt_невалидного_значения_возвращает_none():
    assert decrypt_key("not-a-valid-fernettoken") is None


def test_normalized_provider():
    assert normalized_provider("gigachat") == "gigachat"
    assert normalized_provider("GigaChat") == "gigachat"
    assert normalized_provider("giga_chat") == "gigachat"
    assert normalized_provider("gemini") is None
    assert normalized_provider("openai_compatible") is None
    assert normalized_provider("unknown") is None
    assert normalized_provider(None) is None


def test_is_supported():
    assert is_supported("gigachat") is True
    assert is_supported("gemini") is False
    assert is_supported("openai_compatible") is False
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


def test_classify_descriptions_gigachat_сетевая_ошибка(monkeypatch):
    def fake_post(*args, **kwargs):
        raise RuntimeError("network down")

    monkeypatch.setattr("app.ai.gigachat.httpx.post", fake_post)
    with pytest.raises(AIError):
        classify_descriptions(
            ["Покупка продуктов"], api_key="fake", provider="gigachat"
        )


def test_classify_descriptions_gigachat_успех(monkeypatch):
    chat_text = (
        '[{"category": "Продукты", '
        '"cleaned_description": "Покупка в магазине"}]'
    )
    monkeypatch.setattr(
        "app.ai.gigachat.httpx.post", _fake_gigachat_post(chat_text)
    )
    results = classify_descriptions(
        ["Покупка продуктов"], api_key="fake", provider="gigachat"
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
    result = enrich_with_ai(txns, provider="gigachat", api_key_encrypted=None)
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
    result = enrich_with_ai(txns, provider="gigachat", api_key_encrypted=key)
    assert result == txns


def test_gigachat_запрос_идет_на_chat_completions(monkeypatch):
    captured = {}

    def fake_post(url, *args, **kwargs):
        captured["url"] = url
        if "oauth" not in url:
            captured["payload"] = kwargs.get("json")
        if "oauth" in url:
            return _OAuthResponse()
        return _ChatResponse('{"advice": "Сократите траты на кафе."}')

    monkeypatch.setattr("app.ai.gigachat.httpx.post", fake_post)
    text = generate_advice(
        {"by_category": {"Продукты": 500.0}},
        api_key="fake-key",
        provider="gigachat",
    )
    assert text == "Сократите траты на кафе."
    assert "api.giga.chat/v1/chat/completions" in captured["url"]
    assert captured["payload"]["model"] == "GigaChat-2-Max"
    assert captured["payload"]["stream"] is False


def test_gigachat_404_от_oauth_бросает_aierror(monkeypatch):
    def fake_post(url, *args, **kwargs):
        if "oauth" in url:
            return _ErrorResponse(401, "Unauthorized")
        raise AssertionError("oauth должен вернуть ошибку")

    monkeypatch.setattr("app.ai.gigachat.httpx.post", fake_post)
    with pytest.raises(AIError) as exc_info:
        generate_advice(
            {"by_category": {"Продукты": 500.0}},
            api_key="bad-key",
            provider="gigachat",
        )
    assert "HTTP 401" in str(exc_info.value)


def test_gigachat_ошибка_chat_completions_бросает_aierror(monkeypatch):
    monkeypatch.setattr(
        "app.ai.gigachat.httpx.post", _fake_gigachat_post("", chat_status=500)
    )
    with pytest.raises(AIError) as exc_info:
        generate_advice(
            {"by_category": {"Продукты": 500.0}},
            api_key="fake-key",
            provider="gigachat",
        )
    assert "HTTP 500" in str(exc_info.value)


def test_gigachat_ssl_ошибка_содержит_подсказку_ca(monkeypatch):
    def fake_post(url, *args, **kwargs):
        raise httpx.ConnectError(
            "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: "
            "self-signed certificate in certificate chain"
        )

    monkeypatch.setattr("app.ai.gigachat.httpx.post", fake_post)
    with pytest.raises(AIError) as exc_info:
        generate_advice(
            {"by_category": {"Продукты": 500.0}},
            api_key="fake-key",
            provider="gigachat",
        )
    message = str(exc_info.value)
    assert "GIGACHAT_CA_BUNDLE" in message
    assert "НУЦ Минцифры" in message


def test_gigachat_verify_путь_бандла_из_env(monkeypatch):
    monkeypatch.setenv("GIGACHAT_CA_BUNDLE", "/etc/ssl/certs/gigachat-ca.pem")
    captured = {}

    def fake_post(url, *args, **kwargs):
        captured["verify"] = kwargs.get("verify")
        if "oauth" in url:
            return _OAuthResponse()
        return _ChatResponse('{"advice": "Сократите траты на кафе."}')

    monkeypatch.setattr("app.ai.gigachat.httpx.post", fake_post)
    generate_advice(
        {"by_category": {"Продукты": 500.0}},
        api_key="fake-key",
        provider="gigachat",
    )
    assert captured["verify"] == "/etc/ssl/certs/gigachat-ca.pem"


def test_gigachat_verify_по_умолчанию_включен(monkeypatch):
    monkeypatch.delenv("GIGACHAT_CA_BUNDLE", raising=False)
    captured = {}

    def fake_post(url, *args, **kwargs):
        captured["verify"] = kwargs.get("verify")
        if "oauth" in url:
            return _OAuthResponse()
        return _ChatResponse('{"advice": "Сократите траты на кафе."}')

    monkeypatch.setattr("app.ai.gigachat.httpx.post", fake_post)
    generate_advice(
        {"by_category": {"Продукты": 500.0}},
        api_key="fake-key",
        provider="gigachat",
    )
    assert captured["verify"] is True


class FakeGigaChatHttp:
    """Фейковый httpx.post для GigaChat: /oauth → токен, /chat/completions → ответ."""

    status_code = 200

    def __call__(self, url, *args, **kwargs):
        if "oauth" in url:
            return _OAuthResponse()
        return _ChatResponse(
            '[{"category": "Продукты", "cleaned_description": "Покупка в магазине"}, '
            '{"category": "Продукты", "cleaned_description": "Ещё покупка"}]'
        )


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
        ai_provider="gigachat",
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
        "2026-09-01,120,Неопознанная покупка\n"
        "2026-09-02,60,Ещё один неизвестный платёж\n"
    ).encode("utf-8")
    files = {"file": ("statement.csv", io.BytesIO(csv_bytes), "text/csv")}
    resp = client.post(
        f"/api/families/{family.id}/transactions/import",
        files=files,
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp, client, token, str(family.id)


def test_импорт_с_ai_перераспределяет_прочее(monkeypatch, session_factory):
    from app.database import get_db
    from main import app

    monkeypatch.setattr("app.ai.gigachat.httpx.post", FakeGigaChatHttp())
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


def test_категория_прочее_не_входит_в_допустимые_для_ai():
    assert "Прочее" not in _ALLOWED_CATEGORIES


def test_normalize_category_отклоняет_прочее():
    assert _normalize_category("Прочее") is None
    assert _normalize_category("Продукты") == "Продукты"


def test_промпт_классификации_не_содержит_прочее():
    prompt = _common.build_classify_prompt(["Неопознанная покупка"])
    assert "Прочее" not in prompt
    assert "если не уверен" not in prompt.lower()
