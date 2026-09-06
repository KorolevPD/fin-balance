# -*- coding: utf-8 -*-

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.parsers import parse_pdf_bytes  # noqa: E402

SBER_PDF = REPO_ROOT / "examples" / "sber.pdf"


def _sber_bytes() -> bytes:
    return SBER_PDF.read_bytes()


class TestSberPdfParser:
    def test_разбирает_все_операции_из_примера(self):
        transactions = parse_pdf_bytes(_sber_bytes())

        assert len(transactions) == 255

    def test_извлекает_даты_суммы_и_типы(self):
        transactions = parse_pdf_bytes(_sber_bytes())

        expense_2000 = next(
            item
            for item in transactions
            if item.amount == 2000.00 and item.type == "expense"
        )
        assert expense_2000.date.isoformat() == "2026-06-11"
        assert expense_2000.amount == 2000.00

        income_2000 = next(
            item
            for item in transactions
            if item.amount == 2000.00 and item.type == "income"
        )
        assert income_2000.date.isoformat() == "2026-06-04"

        incomes = [item for item in transactions if item.type == "income"]
        assert len(incomes) > 4
        assert {"2026-06-04", "2026-05-30", "2026-02-27", "2026-01-28"}.issubset(
            {item.date.isoformat() for item in incomes}
        )

        assert any(item.amount == 22682.22 for item in transactions)
        assert any(item.amount == 22600.00 for item in transactions)

    def test_извлекает_описание_контрагента(self):
        transactions = parse_pdf_bytes(_sber_bytes())

        descriptions = {item.description for item in transactions}
        assert "Перевод для И. Иван Иванович. Операция по карте" in descriptions
        assert any("ATM 60210799" in item.description for item in transactions)
        assert all("****" not in item.description for item in transactions)

    def test_битые_данные_вызывают_valueerror(self):
        with pytest.raises(ValueError):
            parse_pdf_bytes(b"this is not a pdf")

    def test_извлекает_категорию_из_колонки_категория(self):
        transactions = parse_pdf_bytes(_sber_bytes())

        assert any(
            item.statement_category == "Супермаркеты" for item in transactions
        )
        assert any(
            item.statement_category == "Транспорт" for item in transactions
        )
        assert any(
            item.statement_category == "Внесение наличных" for item in transactions
        )

    def test_супермаркеты_имеют_категорию_из_выписки(self):
        from app.categorization import categorize_transactions

        categorized = categorize_transactions(parse_pdf_bytes(_sber_bytes()))

        supermarts = [
            item
            for item in categorized
            if item.statement_category == "Супермаркеты"
        ]
        assert len(supermarts) > 40
        assert all(item.category == "Продукты" for item in supermarts)

    def test_транспорт_имеет_категорию_из_выписки(self):
        from app.categorization import categorize_transactions

        categorized = categorize_transactions(parse_pdf_bytes(_sber_bytes()))

        transport = [
            item
            for item in categorized
            if item.statement_category == "Транспорт"
        ]
        assert len(transport) > 40
        assert all(item.category == "Транспорт" for item in transport)

    def test_большинство_операций_получают_категорию(self):
        from app.categorization import categorize_transactions

        categorized = categorize_transactions(parse_pdf_bytes(_sber_bytes()))
        other = sum(1 for item in categorized if item.category == "Прочее")

        assert other / len(categorized) < 0.3
