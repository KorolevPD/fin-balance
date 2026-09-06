"""AI-провайдер OpenAI-совместимого API (Groq, OpenRouter, OpenAI).

Используется, когда ``ai_provider = openai_compatible``. Адрес API задаётся
в ``ai_base_url`` (например ``https://api.groq.com/openai/v1`` для Groq).
"""

import httpx

from app.ai import _common
from app.ai.client import AIError, ClassifyResult

DEFAULT_MODEL = "llama-3.3-70b-versatile"
DEFAULT_BASE_URL = "https://api.openai.com/v1"


def _base(base_url: str | None) -> str:
    return (base_url or DEFAULT_BASE_URL).rstrip("/")


def _chat(api_key: str, base_url: str, model: str, prompt: str) -> str:
    url = f"{_base(base_url)}/chat/completions"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    try:
        resp = httpx.post(url, headers=headers, json=payload, timeout=60)
    except httpx.HTTPError as exc:
        raise AIError(f"OpenAI-совместимый: сеть/таймаут: {exc}") from exc
    if resp.status_code != 200:
        raise AIError(
            f"OpenAI-совместимый: HTTP {resp.status_code}: {resp.text[:300]}"
        )
    try:
        return resp.json()["choices"][0]["message"]["content"]
    except (KeyError, IndexError, ValueError) as exc:
        raise AIError(
            f"OpenAI-совместимый: не удалось прочитать ответ: {resp.text[:300]}"
        ) from exc


def classify_transactions(
    descriptions: list[str],
    *,
    api_key: str,
    base_url: str | None = None,
) -> list[ClassifyResult]:
    if not descriptions:
        return []
    # Модель принимается в base_url через "?model=..." или по умолчанию.
    model = DEFAULT_MODEL
    url = base_url or DEFAULT_BASE_URL
    if "?model=" in url:
        url, _, model = url.partition("?model=")
    prompt = _common.build_classify_prompt(descriptions)
    text = _chat(api_key, url, model, prompt)
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
    model = DEFAULT_MODEL
    url = base_url or DEFAULT_BASE_URL
    if "?model=" in url:
        url, _, model = url.partition("?model=")
    prompt = _common.build_advice_prompt(summary)
    text = _chat(api_key, url, model, prompt)
    return _common.parse_advice_response(text)
