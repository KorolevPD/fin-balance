# -*- coding: utf-8 -*-

from datetime import date

from app.categorization.categorizer import (
    categorize,
    categorize_transactions,
    parse_csv_categorized,
)
from app.categorization.rules import CATEGORY_RULES, DEFAULT_CATEGORY
from app.parsers import ParsedTransaction


class TestCategorize:
    def test_продукты_определяются_по_ключевым_словам(self):
        assert categorize("Пятерочка 3250 Москва") == "Продукты"

    def test_супермаркеты_относятся_к_продуктам(self):
        assert categorize("Супермаркеты") == "Продукты"

    def test_рестораны_и_кафе_определяются_по_названию(self):
        assert categorize("Макдоналдс") == "Рестораны и кафе"

    def test_транспорт_определяется_по_слову_такси(self):
        assert categorize("Яндекс Такси") == "Транспорт"

    def test_жкх_определяется_по_описанию_платежа(self):
        assert categorize("Оплата ЖКХ за сентябрь") == "ЖКХ"

    def test_связь_и_интернет_определяются_по_провайдеру(self):
        assert categorize("Ростелеком интернет") == "Связь и интернет"

    def test_здоровье_определяется_по_аптеке(self):
        assert categorize("Аптека Алое") == "Здоровье"

    def test_зарплата_определяется_по_назначению(self):
        assert categorize("Зачисление заработной платы") == "Зарплата"

    def test_перевод_p2p_относится_к_переводам(self):
        assert categorize("P2P Иванов И.И.") == "Переводы"

    def test_кэшбэк_относится_к_возвратам(self):
        assert categorize("Возврат покупки, кэшбэк") == "Возвраты и кэшбэк"

    def test_маркетплейсы_определяются_по_названию(self):
        assert categorize("Ozon") == "Маркетплейсы и покупки"

    def test_развлечения_определяются_по_кино(self):
        assert categorize("Кинопоиск") == "Развлечения"

    def test_электроника_определяется_по_магазину(self):
        assert categorize("DNS ТВ дивайс") == "Электроника"

    def test_поиск_регистронезависим(self):
        assert categorize("OZON") == "Маркетплейсы и покупки"

    def test_неизвестное_описание_получает_категорию_прочее(self):
        assert categorize("Списание по операции") == DEFAULT_CATEGORY

    def test_пустое_описание_получает_категорию_прочее(self):
        assert categorize("") == DEFAULT_CATEGORY

    def test_все_категории_из_словаря_осмысленны(self):
        assert len(CATEGORY_RULES) > 10
        assert DEFAULT_CATEGORY not in CATEGORY_RULES


class TestStatementCategory:
    def test_супермаркеты_из_выписки_дают_продукты(self):
        assert (
            categorize("FIXPRICE 3457. Операция по карте", "Супермаркеты")
            == "Продукты"
        )

    def test_транспорт_из_выписки_определяется_по_названию_банка(self):
        assert (
            categorize("ISET TRANSPORT 1002. Операция по карте", "Транспорт")
            == "Транспорт"
        )

    def test_рестораны_из_выписки_определяются_по_названию_банка(self):
        assert (
            categorize("BK BURGER RUS. Операция по карте", "Рестораны и кафе")
            == "Рестораны и кафе"
        )

    def test_наличные_из_выписки_дают_категорию_наличные(self):
        assert (
            categorize("ATM 60002344. Операция по карте", "Внесение наличных")
            == "Наличные"
        )

    def test_переводы_из_выписки_дают_категорию_переводы(self):
        assert (
            categorize("SBOL. Операция по карте", "Перевод на карту") == "Переводы"
        )

    def test_категория_из_выписки_имеет_приоритет_над_правилами(self):
        assert (
            categorize("Пятерочка 3250 Москва", "Рестораны и кафе")
            == "Рестораны и кафе"
        )

    def test_прочие_операции_из_выписки_уступают_правилам(self):
        assert (
            categorize("SPOTIFY. Операция по карте", "Прочие операции")
            == "Подписки и сервисы"
        )

    def test_прочие_операции_без_правил_дают_прочее(self):
        assert (
            categorize("Альфа Банк", "Прочие операции") == DEFAULT_CATEGORY
        )

    def test_без_категории_из_выписки_работают_правила(self):
        assert categorize("Ozon", None) == "Маркетплейсы и покупки"

    def test_маппинг_регистронезависим(self):
        assert categorize("Ozon", "супермаркеты") == "Продукты"


class TestCategorizeTransactions:
    def test_категоризация_присваивает_категорию_каждой_операции(self):
        transactions = [
            ParsedTransaction(
                date=date(2026, 9, 1),
                amount=100.0,
                description="Лента",
                type="expense",
            ),
            ParsedTransaction(
                date=date(2026, 9, 2),
                amount=50.0,
                description="Непонятное списание",
                type="expense",
            ),
        ]
        result = categorize_transactions(transactions)

        assert result[0].category == "Продукты"
        assert result[1].category == DEFAULT_CATEGORY

    def test_сохраняются_поля_исходной_операции(self):
        transaction = ParsedTransaction(
            date=date(2026, 9, 1),
            amount=1234.56,
            description="Аптека",
            type="expense",
        )
        result = categorize_transactions([transaction])[0]

        assert result.date == date(2026, 9, 1)
        assert result.amount == 1234.56
        assert result.description == "Аптека"
        assert result.type == "expense"


class TestParseCsvCategorized:
    def test_парсинг_и_категоризация_в_одном_шаге(self):
        content = (
            "Дата,Сумма,Описание\n"
            "2026-09-01,1000.50,Пятерочка\n"
            "2026-09-02,250.00,Яндекс Такси\n"
        )
        result = parse_csv_categorized(content)

        assert len(result) == 2
        assert result[0].category == "Продукты"
        assert result[1].category == "Транспорт"

    def test_парсинг_с_категориями_для_крупной_выписки(self):
        content = (
            "date,amount,description\n"
            "2026-09-01,100,Магнит\n"
            "2026-09-02,200,Аптека\n"
            "2026-09-03,300,РЖД\n"
            "2026-09-04,400,Парфюм\n"
            "2026-09-05,500,Просто текст\n"
        )
        result = parse_csv_categorized(content)
        categories = [item.category for item in result]

        assert categories == [
            "Продукты",
            "Здоровье",
            "Транспорт",
            "Красота и уход",
            DEFAULT_CATEGORY,
        ]
