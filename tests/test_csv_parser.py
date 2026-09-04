# -*- coding: utf-8 -*-

from datetime import date

from app.parsers.csv_parser import detect_format, parse_csv, parse_csv_bytes


class TestUniversal:
    def test_универсальный_парсер_извлекает_дату_сумму_описание(self):
        content = (
            "Дата,Сумма,Описание\n"
            "2026-09-01,1000.50,Покупка продуктов\n"
            "2026-09-02,250.00,Оплата ЖКХ\n"
        )
        result = parse_csv(content)

        assert len(result) == 2
        assert result[0].date == date(2026, 9, 1)
        assert result[0].amount == 1000.50
        assert result[0].description == "Покупка продуктов"

    def test_универсальный_тип_определяется_по_знаку_суммы(self):
        content = (
            "date,amount,description\n"
            "2026-09-01,-500,Продукты\n"
            "2026-09-02,2000,Зарплата\n"
        )
        result = parse_csv(content)
        assert result[0].type == "expense"
        assert result[1].type == "income"
        assert result[0].amount == 500
        assert result[1].amount == 2000

    def test_универсальный_язык_заголовков_русский_и_английский(self):
        ru_content = (
            "Дата операции;Сумма операции;Назначение платежа\n"
            "01.09.2026;1 234,56;Перевод Иванову И.И.\n"
        )
        ru = parse_csv(ru_content)
        en = parse_csv("date;amount;description\n2026-09-01;1234.56;Transfer\n")

        assert ru[0].date == date(2026, 9, 1)
        assert ru[0].amount == 1234.56
        assert en[0].amount == 1234.56

    def test_универсальный_парсер_без_заголовков_по_типам_значений(self):
        content = "01.09.2026,P2P перевод,80.00\n"
        result = parse_csv(content)
        assert len(result) == 1
        assert result[0].date == date(2026, 9, 1)
        assert result[0].amount == 80.0
        assert result[0].description == "P2P перевод"

    def test_пропускает_строки_с_битыми_данными(self):
        content = (
            "date,amount,description\n"
            "2026-09-01,100,ok\n"
            "не-дата,0,nope\n"
            "2026-09-02,abc,bad amount\n"
        )
        result = parse_csv(content)
        assert len(result) == 1
        assert result[0].description == "ok"

    def test_пустой_файл_возвращает_пустой_список(self):
        assert parse_csv("date,amount,description\n") == []
        assert parse_csv("") == []

    def test_универсальный_явная_колонка_типа_операции(self):
        content = (
            "Дата,Сумма,Описание,Тип операции\n"
            "2026-09-01,300,Магазин,Пополнение\n"
        )
        result = parse_csv(content)
        assert result[0].type == "income"
        assert result[0].amount == 300


class TestTinkoff:
    TINKOFF_HEADERS = (
        "Тип операции,Дата операции,Время операции,Номер карты,Статус,"
        "Сумма операции,Валюта операции,Сумма платежа,Валюта платежа,"
        "Категория,MCC,Название,Описание,Комментарий"
    )

    def test_детект_формата_тинкофф_по_заголовкам(self):
        headers = self.TINKOFF_HEADERS.split(",")
        assert detect_format(headers) == "tinkoff"

    def test_tinkoff_извлекает_операцию_как_расход(self):
        content = self.TINKOFF_HEADERS + "\n"
        content += (
            'Операция,02.09.2026,12:30:00,*5312,OK,"1 500,00",RUB,"1 500,00",RUB,'
            "Супермаркеты,5411,Ozon,Fix,order\n"
        )
        result = parse_csv(content, source_format="tinkoff")

        assert len(result) == 1
        assert result[0].date == date(2026, 9, 2)
        assert result[0].amount == 1500.00
        assert result[0].type == "expense"
        assert result[0].description == "Ozon"

    def test_tinkoff_пополнение_считается_доходом(self):
        content = self.TINKOFF_HEADERS + "\n"
        content += (
            'Пополнение,02.09.2026,09:00:00,,OK,"10 000,00",RUB,"10 000,00",RUB,'
            "Переводы,,От Иванова И.,,Зачисление\n"
        )
        result = parse_csv(content, source_format="tinkoff")

        assert len(result) == 1
        assert result[0].type == "income"
        assert result[0].amount == 10000.00


class TestSber:
    def test_детект_формата_сбер_по_заголовкам(self):
        headers = (
            "Номер документа;Дата операции;Дата платежа;Сумма операции;"
            "Назначение платежа"
        ).split(";")
        assert detect_format(headers) == "sber"

    def test_sber_расход_отрицательная_сумма_с_запятой(self):
        content = (
            "Номер документа;Дата операции;Дата платежа;Сумма операции;"
            "Валюта операции;Категория;Назначение платежа\n"
            "1;01.09.2026;01.09.2026;-1 234,56;RUB;Оплата услуг;Интернет-провайдер\n"
            "2;01.09.2026;01.09.2026;5 000,00;RUB;Перевод;Зарплата\n"
        )
        result = parse_csv(content, source_format="sber")

        assert len(result) == 2
        assert result[0].type == "expense"
        assert result[0].amount == 1234.56
        assert result[0].description == "Интернет-провайдер"
        assert result[1].type == "income"
        assert result[1].amount == 5000.00


class TestEncodings:
    def test_кодировка_cp1251_из_байтов(self):
        content = (
            "Дата операции;Сумма операции;Назначение платежа\n"
            "01.09.2026;100,00;Продукты\n"
        )
        data = content.encode("cp1251")
        result = parse_csv_bytes(data)
        assert result[0].date == date(2026, 9, 1)
        assert result[0].amount == 100.0
        assert result[0].description == "Продукты"

    def test_кодировка_utf8_с_bom(self):
        content = "Дата;Сумма;Описание\n2026-09-01;50;Кофе\n"
        data = b"\xef\xbb\xbf" + content.encode("utf-8")
        result = parse_csv_bytes(data)
        assert result[0].amount == 50.0
