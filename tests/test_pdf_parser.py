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
    def test_разбирает_восемь_операций_из_примера(self):
        transactions = parse_pdf_bytes(_sber_bytes())

        assert len(transactions) == 8

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
        assert len(incomes) == 4
        assert all(
            item.date.isoformat()
            in {"2026-06-04", "2026-05-30", "2026-02-27", "2026-01-28"}
            for item in incomes
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
