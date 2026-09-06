"""AI-провайдер Google Gemini (REST generateContent).

Бесплатный ключ выдаётся в Google AI Studio (aistudio.google.com).
Модель по умолчанию — ``gemini-3.6-flash`` (бесплатный тариф).
"""

import httpx

from app.ai import _common
from app.ai.client import AIError, ClassifyResult

DEFAULT_MODEL = "gemini-3.6-flash"

_GENERATE_URL = "https://generativelanguage.googleapis.com/v1beta/models/{}:generateContent"


def _headers(api_key: str) -> dict:
    return {"Content-Type": "application/json", "x-goog-api-key": api_key}


def _generate(api_key: str, model: str, prompt: str) -> str:
    url = _GENERATE_URL.format(model)
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2},
    }
    try:
        resp = httpx.post(url, headers=_headers(api_key), json=payload, timeout=60)
    except httpx.HTTPError as exc:
        raise AIError(f"Gemini: сеть/таймаут: {exc}") from exc
    if resp.status_code != 200:
        raise AIError(
            f"Gemini: HTTP {resp.status_code}: {resp.text[:300]}"
        )
    try:
        data = resp.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, ValueError) as exc:
        raise AIError(f"Gemini: не удалось прочитать ответ: {resp.text[:300]}") from exc
    return text


def classify_transactions(
    descriptions: list[str],
    *,
    api_key: str,
    base_url: str | None = None,
) -> list[ClassifyResult]:
    if not descriptions:
        return []
    model = (base_url or DEFAULT_MODEL)
    prompt = _common.build_classify_prompt(descriptions)
    text = _generate(api_key, model, prompt)
    results = _common.parse_classify_response(text, len(descriptions))
    # Дополняем недостающие элементы до длины входа
    while len(results) < len(descriptions):
        results.append(ClassifyResult(None, None))
    return results[: len(descriptions)]


def generate_advice(
    summary: dict,
    *,
    api_key: str,
    base_url: str | None = None,
) -> str:
    model = base_url or DEFAULT_MODEL
    prompt = _common.build_advice_prompt(summary)
    text = _generate(api_key, model, prompt)
    return _common.parse_advice_response(text)
