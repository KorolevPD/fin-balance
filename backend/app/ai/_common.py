"""Общие промпты и разбор ответов для AI-провайдеров."""

import json
import re

from app.ai.client import ClassifyResult, AIError

_CATEGORIES = (
    "Продукты",
    "Рестораны и кафе",
    "Транспорт",
    "Топливо",
    "Связь и интернет",
    "ЖКХ",
    "Маркетплейсы и покупки",
    "Одежда и обувь",
    "Здоровье",
    "Развлечения",
    "Подписки и сервисы",
    "Дом и ремонт",
    "Электроника",
    "Дети",
    "Животные",
    "Красота и уход",
    "Путешествия",
    "Образование",
    "Кредиты и долги",
    "Налоги и штрафы",
    "Наличные",
    "Переводы",
    "Зарплата",
    "Возвраты и кэшбэк",
)

CATEGORY_LIST = ", ".join(f'"{c}"' for c in _CATEGORIES)


def _extract_json(text: str) -> str:
    """Вытащить JSON-массив или объект из ответа модели."""
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return text


def parse_classify_response(
    text: str, expected: int
) -> list[ClassifyResult]:
    """Разобрать JSON-ответ классификации в список результатов."""
    raw = _extract_json(text)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AIError(f"Не удалось разобрать JSON от AI: {exc}") from exc

    results = []
    for item in data:
        if not isinstance(item, dict):
            results.append(ClassifyResult(None, None))
            continue
        category = item.get("category") or item.get("категория")
        cleaned = item.get("cleaned_description") or item.get("описание")
        results.append(
            ClassifyResult(
                category=(str(category).strip() if category else None),
                cleaned_description=(str(cleaned).strip() if cleaned else None),
            )
        )

    if not results:
        raise AIError("AI вернул пустой список классификации")
    return results


def parse_advice_response(text: str) -> str:
    """Извлечь текст совета из ответа модели."""
    text = text.strip()
    raw = _extract_json(text)
    try:
        data = json.loads(raw)
        if isinstance(data, dict) and ("advice" in data or "совет" in data):
            value = data.get("advice") or data.get("совет")
            if isinstance(value, str) and value.strip():
                return value.strip()
    except json.JSONDecodeError:
        pass
    return text.strip() or "Совет"


def build_classify_prompt(descriptions: list[str]) -> str:
    """Промпт для классификации описаний операций."""
    items = "\n".join(f'{i + 1}. "{d}"' for i, d in enumerate(descriptions))
    return (
        "Ты — помощник по финансовой аналитике. Для каждой банковской операции "
        "определи категорию из строго заданного списка и придумай короткое "
        "понятное человеку описание (до 60 символов) на русском языке.\n\n"
        f"Допустимые категории: {CATEGORY_LIST}.\n\n"
        "Описание должно максимально точно отражать исходное техническое название: "
        "сохраняй суть операции (магазин, услугу, контрагента, назначение платежа), "
        "не додумывай несуществующие детали и не меняй смысл. Текст должен быть "
        "грамотным: начинай с заглавной буквы, соблюдай правильную пунктуацию "
        "(точки, запятые) и расставляй пробелы по правилам русского языка.\n\n"
        "Верни строго JSON-массив в том же порядке без пояснений в формате:\n"
        '[{"category": "Категория", "cleaned_description": "Описание"}, ...]\n\n'
        f"Операции:\n{items}\n\n"
        "Всегда выбирай конкретную категорию из списка, не оставляй "
        "операцию без категории."
    )


def build_advice_prompt(summary: dict) -> str:
    """Промпт для генерации совета на основе сводки расходов."""
    payload = json.dumps(summary, ensure_ascii=False, default=str)
    return (
        "Ты — персональный финансовый консультант на русском языке. На основе "
        "сводки расходов семьи дай один конкретный полезный совет по экономии "
        "или улучшению финансовой картины. Учитывай топ категорий, динамику "
        "по месяцам и крупные траты. Не упоминай имена. Совет размером 2-4 "
        "предложения (до 1000 символов), без нумерации и вводных фраз вида "
        "'Рекомендация:'. Верни строго JSON: "
        '{"advice": "текст совета"}\n\n'
        f"Сводка расходов (JSON):\n{payload}"
    )
