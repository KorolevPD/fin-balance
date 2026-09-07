"""AI-провайдер GigaChat (REST, OpenAI-совместимый chat/completions).

GigaChat требует получения access-токена (действует 30 минут) по ключу
авторизации (Authorization Key) из личного кабинета Сбера, после чего запросы
генерации выполняются по адресу ``https://api.giga.chat/v1``.

Поток: ключ авторизации → POST /oauth (access-токен) → POST /chat/completions.
"""

import os
import uuid

import httpx

from app.ai import _common
from app.ai.client import AIError, ClassifyResult

DEFAULT_MODEL = "GigaChat"
DEFAULT_BASE_URL = "https://api.giga.chat/v1"
_OAUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
_OAUTH_SCOPE = "GIGACHAT_API_PERS"
_CA_ENV = "GIGACHAT_CA_BUNDLE"

_SSL_HINT = (
    " Установите корневой сертификат НУЦ Минцифры и укажите его через переменную "
    f"окружения {_CA_ENV} (путь к PEM-файлу), см. deploy/DEPLOY.md."
)


def _cacert() -> str | bool:
    """Путь к PEM-бандлу с корневым сертификатом НУЦ Минцифры или ``True``.

    Глобальный trust-store не трогается: параметр применяется только к запросам
    GigaChat. Без переменной поведение прежнее — проверка TLS включена.
    """
    path = (os.getenv(_CA_ENV) or "").strip()
    return path or True


def _access_token(auth_key: str) -> str:
    """Получить access-токен по ключу авторизации (OAuth)."""
    last_error: AIError | None = None
    for scheme in ("Basic", "Bearer"):
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "RqUID": str(uuid.uuid4()),
            "Authorization": f"{scheme} {auth_key}",
        }
        try:
            resp = httpx.post(
                _OAUTH_URL,
                headers=headers,
                data={"scope": _OAUTH_SCOPE},
                timeout=60,
                verify=_cacert(),
            )
        except httpx.HTTPError as exc:
            last_error = AIError(
                f"GigaChat: сеть/таймаут при получении токена: {exc}{_SSL_HINT}"
            )
            continue
        if resp.status_code == 200:
            try:
                token = resp.json()["access_token"]
            except (KeyError, ValueError) as exc:
                raise AIError(
                    f"GigaChat: не удалось прочитать токен: {resp.text[:300]}"
                ) from exc
            return token
        last_error = AIError(
            f"GigaChat: HTTP {resp.status_code} при получении токена: "
            f"{resp.text[:300]}"
        )
        if resp.status_code not in (400, 401, 403):
            raise last_error
    raise last_error


def _chat(auth_key: str, base_url: str, model: str, prompt: str) -> str:
    token = _access_token(auth_key)
    url = f"{base_url.rstrip('/')}/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "Ты — помощник по финансовой аналитике на русском языке.",
            },
            {"role": "user", "content": prompt},
        ],
        "stream": False,
    }
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    try:
        resp = httpx.post(
            url, headers=headers, json=payload, timeout=60, verify=_cacert()
        )
    except httpx.HTTPError as exc:
        raise AIError(f"GigaChat: сеть/таймаут: {exc}{_SSL_HINT}") from exc
    if resp.status_code != 200:
        raise AIError(
            f"GigaChat: HTTP {resp.status_code}: {resp.text[:300]}"
        )
    try:
        return resp.json()["choices"][0]["message"]["content"]
    except (KeyError, IndexError, ValueError) as exc:
        raise AIError(
            f"GigaChat: не удалось прочитать ответ: {resp.text[:300]}"
        ) from exc


def classify_transactions(
    descriptions: list[str],
    *,
    api_key: str,
    base_url: str | None = None,
) -> list[ClassifyResult]:
    if not descriptions:
        return []
    base = base_url or DEFAULT_BASE_URL
    prompt = _common.build_classify_prompt(descriptions)
    text = _chat(api_key, base, DEFAULT_MODEL, prompt)
    results = _common.parse_classify_response(text, len(descriptions))
    while len(results) < len(descriptions):
        results.append(ClassifyResult(None, None))
    return results[: len(descriptions)]


def generate_advice(
    summary: dict,
    *,
    api_key: str,
    base_url: str | None = None,
) -> str:
    base = base_url or DEFAULT_BASE_URL
    prompt = _common.build_advice_prompt(summary)
    text = _chat(api_key, base, DEFAULT_MODEL, prompt)
    return _common.parse_advice_response(text)
