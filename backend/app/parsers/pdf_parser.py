"""Парсер банковской выписки в формате PDF.

Поддерживает формат выписки Сбербанка по дебетовой карте (как в
``examples/sber.pdf``). Текст извлекается через ``pypdf`` в layout-режиме,
сохраняющем позиции колонок, поэтому строки операций имеют вид:

    11.06.2026        14:11          Перевод СБП            2 000,00      0,00
    11.06.2026        543627         Перевод для И. Иван Иванович. ...
                                     ****1234

Сумма с префиксом ``+`` — поступление (income), без знака — списание
(expense). Описание операции берётся из строк, следующих за строкой
операции: имя контрагента/ATM, код авторизации и номер карты отфильтровываются.
"""

import io
import re
from datetime import date, datetime

from pypdf import PdfReader

from app.parsers.csv_parser import ParsedTransaction

_NBSP = "\u00a0"

_TRANSACTION_RE = re.compile(
    r"^(\d{2}\.\d{2}\.\d{4})\s+(\d{2}:\d{2})\s+(.+?)\s+"
    r"([+\u2212]?[\d\s\u00a0]+,\d{2})\s+([\d\s\u00a0]+,\d{2})\s*$"
)
_DESCRIPTION_RE = re.compile(
    r"^(\d{2}\.\d{2}\.\d{4})\s+(\d{1,6})\s+(.+)$"
)
_CARD_RE = re.compile(r"^\*{2,4}\d{4}$")
_CODE_RE = re.compile(r"^\d{4,6}$")
_CARD_SUFFIX_RE = re.compile(r"\s+\*{2,4}\d{4}\s*$")


def _clean_description(text: str) -> str:
    return _CARD_SUFFIX_RE.sub("", text).strip()


def _parse_amount(raw: str) -> float:
    cleaned = raw.replace(_NBSP, "").replace(" ", "")
    return abs(float(cleaned.replace(",", ".")))


def _parse_date(raw: str) -> date:
    return datetime.strptime(raw, "%d.%m.%Y").date()


def _description_line(line: str) -> str | None:
    """Извлечь описание из строки вида ``ДД.ММ.ГГГГ КОД ОПИСАНИЕ``."""
    match = _DESCRIPTION_RE.match(line)
    if match is None:
        return None
    return match.group(3).strip()


def _is_noise(line: str) -> bool:
    stripped = line.strip()
    if not stripped or stripped in {"****1234"} or _CARD_RE.match(stripped):
        return True
    return bool(_CODE_RE.match(stripped))


def _collect_description(lines: list[str], index: int) -> str:
    parts: list[str] = []
    for candidate in lines[index + 1 :]:
        if not candidate.strip():
            break
        text = _description_line(candidate)
        if text and not _is_noise(text):
            parts.append(text)
        elif _is_noise(candidate) and text is None:
            continue
    return " ".join(parts)


def parse_pdf_bytes(data: bytes) -> list[ParsedTransaction]:
    """Разобрать PDF-выписку (Сбербанк) из байтов в список операций."""
    try:
        reader = PdfReader(io.BytesIO(data))
        pages = [
            page.extract_text(extraction_mode="layout") or "" for page in reader.pages
        ]
    except Exception as exc:  # noqa: BLE001
        raise ValueError(
            "Не удалось прочитать PDF: файл повреждён или не является PDF"
        ) from exc

    lines = "\n".join(pages).splitlines()
    results: list[ParsedTransaction] = []
    seen: set[tuple] = set()

    for i, line in enumerate(lines):
        match = _TRANSACTION_RE.match(line.strip())
        if match is None:
            continue
        date_value = _parse_date(match.group(1))
        amount_raw = match.group(4)
        type_value = "income" if amount_raw.lstrip().startswith("+") else "expense"
        amount_value = round(_parse_amount(amount_raw), 2)
        statement_category = match.group(3).strip()
        description = _collect_description(lines, i)
        if not description:
            description = statement_category
        description = _clean_description(description) or "Без названия"

        key = (date_value, amount_value, description)
        if key in seen:
            continue
        seen.add(key)
        results.append(
            ParsedTransaction(
                date=date_value,
                amount=amount_value,
                description=description,
                type=type_value,
                statement_category=statement_category,
            )
        )
    return results
