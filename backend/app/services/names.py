"""Определение переводов самому себе.

Выписки банков содержат переводы, которые владелец совершает на собственные
счета/карты. Такие переводы не являются расходом, поэтому их не нужно учитывать
в аналитике. Перевод считается переводом самому себе, если Имя, Отчество и
первая буква фамилии получателя (из описания операции) совпадают с теми же
компонентами имени владельца выписки (``User.name``).

Форматы получателя в описаниях разные:

- ``Перевод для И. Иван Иванович. Операция по карте`` (Сбербанк);
- ``Перевод для Иван Иванович``;
- ``P2P Ivanov Ivan I.``, ``Перевод на карту Петр Петрович`` и т.п.

Если часть компонентов (например, отчество) у владельца или получателя
отсутствует, совпадением считаются только те компоненты, которые известны
с обеих сторон; перевод распознаётся как self-transfer минимум при двух
совпавших компонентах.
"""

import re
from dataclasses import dataclass

_NAME_TOKEN_RE = re.compile(r"[A-Za-zА-Яа-яЁё][A-Za-zА-Яа-яЁё-]*")

_TRANSFER_MARKERS = (
    "перевод",
    "перечисл",
    "зачисл",
    "перевести",
    "p2p",
    "sbp",
)

_PATRONYMIC_SUFFIXES = (
    "ович",
    "евич",
    "овна",
    "евна",
    "ична",
    "вна",
    "вны",
    "ич",
    "ovich",
    "evich",
    "ovna",
    "evna",
)

# Слова, не относящиеся к имени получателя, в описании операции.
_STOPWORDS = {
    "перевод",
    "перевода",
    "переводы",
    "переводом",
    "переводов",
    "перечисление",
    "перечисление",
    "перечислил",
    "перечислено",
    "зачисление",
    "зачислено",
    "перевести",
    "перевел",
    "переведено",
    "операция",
    "операции",
    "операциям",
    "по",
    "карте",
    "карты",
    "карта",
    "счет",
    "счета",
    "счету",
    "счёт",
    "счёта",
    "счёту",
    "для",
    "на",
    "в",
    "с",
    "со",
    "и",
    "банк",
    "номер",
    "через",
    "кому",
    "от",
    "внутри",
    "своих",
    "между",
    "своими",
    "сервис",
    "сервиса",
    "сервисов",
    "сайт",
    "онлайн",
    "авторизация",
    "подтверждено",
    "успешно",
    "выполнено",
    "оплата",
    "оплаты",
    "покупка",
    "покупки",
    "списание",
    "списания",
    "пополнение",
    "пополнения",
    "снятие",
    "выдача",
    "внесение",
    "наличных",
    "банкомат",
    "сайт",
    "sbp",
    "сбп",
    "p2p",
    "сбербанк",
    "тинькофф",
    "tinkoff",
    "поступление",
    "спб",
}


@dataclass
class PersonSignature:
    """Признаки персоны: имя, отчество и первая буква фамилии.

    Все значения приводятся к нижнему регистру; инициалы — одной буквой.
    Отсутствующий компонент равен ``None``.
    """

    given_name: str | None = None
    patronymic: str | None = None
    surname_initial: str | None = None


def _normalize(token: str) -> str:
    return token.rstrip(".").strip().lower()


def _is_initial(token: str) -> bool:
    return len(_normalize(token)) == 1


def _is_patronymic(value: str) -> bool:
    return any(value.endswith(suffix) for suffix in _PATRONYMIC_SUFFIXES)


def _tokenize(text: str) -> list[str]:
    return _NAME_TOKEN_RE.findall(text or "")


def _words(tokens: list[str]) -> list[tuple[int, str]]:
    return [
        (index, _normalize(token))
        for index, token in enumerate(tokens)
        if not _is_initial(token)
    ]


def _initials(tokens: list[str]) -> list[str]:
    return [_normalize(token)[0] for token in tokens if _is_initial(token)]


def _signature_from_tokens(tokens: list[str]) -> PersonSignature | None:
    """Собрать признаки персоны из набора токенов имени."""
    normalized = [_normalize(token) for token in tokens]
    if not normalized:
        return None

    patronymic_index = next(
        (index for index, value in enumerate(normalized) if _is_patronymic(value)),
        None,
    )

    given_name: str | None = None
    surname_initial: str | None = None
    patronymic: str | None = None

    if patronymic_index is not None:
        patronymic = normalized[patronymic_index]
        words_before = _words(tokens[:patronymic_index])
        if words_before:
            given_name = words_before[-1][1]
        # первая буква фамилии: инициал перед отчеством или слово слева от имени
        initials_before = _initials(tokens[:patronymic_index])
        if initials_before:
            surname_initial = initials_before[0]
        elif len(words_before) >= 2:
            surname_initial = words_before[-2][1][0]
    else:
        words_all = _words(tokens)
        initials_all = _initials(tokens)
        if words_all:
            if initials_all:
                # Формат «Фамилия Имя» + инициалы: имя — последнее слово,
                # первая буква фамилии — первая буква слова слева от имени.
                given_name = words_all[-1][1]
                if len(words_all) >= 2:
                    surname_initial = words_all[0][1][0]
                else:
                    surname_initial = initials_all[0]
            elif len(words_all) >= 2:
                # Формат «Имя Фамилия»: имя — первое слово.
                given_name = words_all[0][1]
                surname_initial = words_all[1][1][0]
            else:
                given_name = words_all[0][1]
        elif initials_all:
            surname_initial = initials_all[0]

    if given_name is None and surname_initial is None:
        return None
    return PersonSignature(
        given_name=given_name,
        patronymic=patronymic,
        surname_initial=surname_initial,
    )


def parse_person_name(value: str | None) -> PersonSignature:
    """Разобрать полное имя владельца (``User.name``) на признаки.

    Поддерживаются форматы: ``Фамилия Имя Отчество``, ``Имя Отчество``,
    ``Имя Фамилия``, ``Имя``, латиница и инициалы (``И.`` / ``I.``).
    """
    if not value:
        return PersonSignature()
    return _signature_from_tokens(_tokenize(value)) or PersonSignature()


def parse_transfer_recipient(description: str | None) -> PersonSignature | None:
    """Извлечь признаки получателя из описания операции-перевода.

    Возвращает ``None``, если описание не похоже на перевод или в нём не
    удалось найти компоненты имени.
    """
    if not description:
        return None
    lowered = description.lower()
    if not any(marker in lowered for marker in _TRANSFER_MARKERS):
        return None

    tokens = [
        token
        for token in _tokenize(description)
        if _is_initial(token) or _normalize(token) not in _STOPWORDS
    ]
    return _signature_from_tokens(tokens)


def _signatures_match(owner: PersonSignature, recipient: PersonSignature) -> bool:
    """Совпадают ли признаки владельца и получателя.

    Сравниваются только компоненты, известные с обеих сторон; инициал отчества
    получателя сверяется с первой буквой полного отчества. Требуется минимум
    два совпавших компонента (имя + отчество, или имя + первая буква фамилии,
    или отчество + первая буква фамилии).
    """
    matched = 0

    if recipient.given_name and owner.given_name:
        if recipient.given_name != owner.given_name:
            return False
        matched += 1

    if recipient.patronymic and owner.patronymic:
        if len(recipient.patronymic) == 1:
            if not owner.patronymic.startswith(recipient.patronymic):
                return False
        elif recipient.patronymic != owner.patronymic:
            return False
        matched += 1

    if recipient.surname_initial and owner.surname_initial:
        if recipient.surname_initial != owner.surname_initial:
            return False
        matched += 1

    return matched >= 2


def is_transfer_to_self(owner_name: str | None, description: str | None) -> bool:
    """Является ли операция переводом самому себе."""
    if not owner_name:
        return False
    recipient = parse_transfer_recipient(description)
    if recipient is None:
        return False
    return _signatures_match(parse_person_name(owner_name), recipient)


def mark_self_transfers(transactions, owner_name: str | None) -> list:
    """Пометить операции выписки как переводы самому себе.

    Меняет ``is_self_transfer`` у переданных объектов на месте и возвращает их.
    """
    for item in transactions:
        if not item.is_self_transfer:
            item.is_self_transfer = is_transfer_to_self(owner_name, item.description)
    return list(transactions)
