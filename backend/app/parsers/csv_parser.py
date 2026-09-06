"""Парсер банковских выписок CSV.

Поддерживает три формата:
- universal — универсальный: колонки определяются по заголовкам или по типам значений;
- tinkoff — выписка банка Тинькофф (запятая-разделитель, заголовки кириллицей);
- sber — выписка Сбербанка (точка с запятой, возможна кодировка cp1251).
"""

import csv
import io
import re
from datetime import date, datetime

from pydantic import BaseModel

_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}|\d{1,2}[./-]\d{1,2}[./-]\d{2,4}")
_AMOUNT_CLEAN = re.compile(r"[\s\u00a0\u202f@]")
_HEADER_CLEAN = re.compile(r"[^a-zа-я0-9]")


class ParsedTransaction(BaseModel):
    """Одна операция, извлечённая из выписки."""

    date: date
    amount: float
    description: str
    type: str  # "income" | "expense"
    statement_category: str | None = None


# Псевдонимы заголовков -> канонические поля выписки
_DATE_ALIASES = (
    "date",
    "дата",
    "датаоперации",
    "датаплатежа",
    "датадокумента",
    "datetime",
)
_AMOUNT_ALIASES = (
    "amount",
    "sum",
    "сумма",
    "суммаоперации",
    "суммаплатежа",
    "amountrub",
    "суммаруб",
)
_DESCRIPTION_ALIASES = (
    "description",
    "name",
    "memo",
    "описание",
    "назначение",
    "назначениеплатежа",
    "название",
    "категория",
    "контрагент",
)
_TYPE_ALIASES = ("type", "тип", "типоперации", "operationtype")


def _normalize_header(value: str) -> str:
    return _HEADER_CLEAN.sub("", value.strip().lower())


def _parse_amount(value: str) -> float:
    cleaned = _AMOUNT_CLEAN.sub("", value.strip())
    if "," in cleaned and "." in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")
    return float(cleaned)


def _parse_date(value: str) -> date:
    value = value.strip()
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d.%m.%y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    match = _DATE_RE.search(value)
    if match is None:
        raise ValueError(f"Невозможно распознать дату: {value!r}")
    return _parse_date(match.group())


def _decode(data: bytes) -> str:
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("cp1251")


def _sniff_delimiter(content: str) -> str:
    try:
        dialect = csv.Sniffer().sniff(content[:4096], delimiters=",;\t|")
        return dialect.delimiter
    except csv.Error:
        return ","


def _read_all_rows(content: str) -> list[list[str]]:
    delimiter = _sniff_delimiter(content)
    reader = csv.reader(io.StringIO(content), delimiter=delimiter)
    return [row for row in reader if any(cell.strip() for cell in row)]


def _find_column(headers: list[str], aliases: tuple[str, ...]) -> int | None:
    normalized = [_normalize_header(h) for h in headers]
    for alias in aliases:
        if alias in normalized:
            return normalized.index(alias)
    return None


def _build_column_map(headers: list[str]) -> dict[str, int | None]:
    return {
        "date": _find_column(headers, _DATE_ALIASES),
        "amount": _find_column(headers, _AMOUNT_ALIASES),
        "description": _find_column(headers, _DESCRIPTION_ALIASES),
        "type": _find_column(headers, _TYPE_ALIASES),
    }


def _normalize_type(value: str) -> str:
    lowered = value.strip().lower()
    if lowered in ("income", "доход", "пополнение", "credit", "кредит"):
        return "income"
    return "expense"


def _infer_type_by_sign(amount: float) -> str:
    return "income" if amount >= 0 else "expense"


def detect_format(headers: list[str]) -> str:
    normalized = [_normalize_header(h) for h in headers]
    if "назначениеплатежа" in normalized:
        return "sber"
    tinkoff_markers = ("суммаоперации", "типоперации", "времяоперации", "номеркарты")
    if sum(1 for m in tinkoff_markers if m in normalized) >= 2:
        return "tinkoff"
    return "universal"


def _parse_tinkoff(
    rows: list[list[str]],
    headers: list[str],
) -> list[ParsedTransaction]:
    normalized = [_normalize_header(h) for h in headers]

    def col(aliases: tuple[str, ...]) -> int | None:
        for a in aliases:
            if a in normalized:
                return normalized.index(a)
        return None

    date_idx = col(_DATE_ALIASES)
    amount_idx = col(("суммаоперации", "суммаплатежа"))
    desc_idx = col(("название", "описание", "категория"))
    type_idx = col(_TYPE_ALIASES)

    results: list[ParsedTransaction] = []
    for row in rows:
        try:
            date_value = _parse_date(row[date_idx])
            raw_amount = _parse_amount(row[amount_idx])
            amount_value = abs(raw_amount)
            if desc_idx is not None and desc_idx < len(row):
                description = row[desc_idx].strip()
            else:
                description = ""
            if type_idx is not None and type_idx < len(row):
                type_value = _normalize_type(row[type_idx])
            else:
                type_value = _infer_type_by_sign(raw_amount)
            results.append(
                ParsedTransaction(
                    date=date_value,
                    amount=round(amount_value, 2),
                    description=description,
                    type=type_value,
                )
            )
        except (ValueError, IndexError):
            continue
    return results


def _parse_sber(rows: list[list[str]], headers: list[str]) -> list[ParsedTransaction]:
    mapping = _build_column_map(headers)
    results: list[ParsedTransaction] = []
    for row in rows:
        try:
            date_value = _parse_date(row[mapping["date"]])
            amount_value = _parse_amount(row[mapping["amount"]])
            desc_idx = mapping["description"]
            if desc_idx is not None and desc_idx < len(row):
                description = row[desc_idx].strip()
            else:
                description = ""
            results.append(
                ParsedTransaction(
                    date=date_value,
                    amount=abs(round(amount_value, 2)),
                    description=description,
                    type=_infer_type_by_sign(amount_value),
                )
            )
        except (ValueError, IndexError):
            continue
    return results


def _classify_value(value: str) -> str:
    value = value.strip()
    if not value:
        return "empty"
    if _DATE_RE.fullmatch(value.replace(" ", "")):
        return "date"
    try:
        _parse_amount(value)
        return "number"
    except ValueError:
        return "text"


def _infer_columns_by_values(
    rows: list[list[str]],
) -> tuple[int | None, int | None, int | None]:
    first = rows[0] if rows else []
    classified = [_classify_value(cell) for cell in first]
    date_idx = next((i for i, c in enumerate(classified) if c == "date"), None)
    number_idx = next((i for i, c in enumerate(classified) if c == "number"), None)
    text_idx = next((i for i, c in enumerate(classified) if c == "text"), None)
    return date_idx, number_idx, text_idx


def _parse_universal(
    rows: list[list[str]],
    headers: list[str],
    has_headers: bool,
) -> list[ParsedTransaction]:
    if has_headers:
        mapping = _build_column_map(headers)
        data_rows = rows
    else:
        date_idx, amount_idx, desc_idx = _infer_columns_by_values(rows)
        mapping = {
            "date": date_idx,
            "amount": amount_idx,
            "description": desc_idx,
            "type": None,
        }
        data_rows = rows

    results: list[ParsedTransaction] = []
    for row in data_rows:
        try:
            date_value = _parse_date(row[mapping["date"]])
            amount_value = _parse_amount(row[mapping["amount"]])
            desc_idx = mapping["description"]
            if desc_idx is not None and desc_idx < len(row):
                description = row[desc_idx].strip()
            else:
                description = ""
            if mapping["type"] is not None:
                type_value = _normalize_type(row[mapping["type"]])
            else:
                type_value = _infer_type_by_sign(amount_value)
            results.append(
                ParsedTransaction(
                    date=date_value,
                    amount=abs(round(amount_value, 2)),
                    description=description,
                    type=type_value,
                )
            )
        except (ValueError, IndexError):
            continue
    return results


def parse_csv(
    content: str,
    source_format: str | None = None,
) -> list[ParsedTransaction]:
    """Разобрать CSV-выписку в список операций."""
    all_rows = _read_all_rows(content)
    if not all_rows:
        return []

    first_row = all_rows[0]
    if source_format is None:
        source_format = detect_format(first_row)

    if source_format == "tinkoff":
        return _parse_tinkoff(all_rows[1:], first_row)
    if source_format == "sber":
        return _parse_sber(all_rows[1:], first_row)

    has_headers = _build_column_map(first_row)["date"] is not None
    if has_headers:
        return _parse_universal(all_rows[1:], first_row, has_headers=True)
    return _parse_universal(all_rows, first_row, has_headers=False)


def parse_csv_bytes(
    data: bytes,
    source_format: str | None = None,
) -> list[ParsedTransaction]:
    """Разобрать CSV-выписку из байтов. Кодировка: utf-8 или cp1251."""
    return parse_csv(_decode(data), source_format=source_format)
