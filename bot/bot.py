import asyncio
import logging
from os import getenv

import aiohttp
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, CommandStart

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = getenv("BOT_TOKEN")
API_URL = getenv("API_URL", "http://backend:8000").rstrip("/")

bot = Bot(token=BOT_TOKEN) if BOT_TOKEN else None
dp = Dispatcher()


@dp.message(CommandStart())
async def start(message: types.Message):
    await message.answer(
        "Добро пожаловать в FinBalance! 🏦\n\n"
        "Я помогу вам управлять семейным бюджетом.\n\n"
        "Команды:\n"
        "/start - Начать работу\n"
        "/link <код> - Привязать Telegram к веб-аккаунту\n"
        "/me - Проверить статус привязки\n"
        "/summary - Получить сводку расходов\n\n"
        "Отправьте CSV-выписку, чтобы загрузить операции в вашу семью."
    )


@dp.message(Command("link"))
async def link(message: types.Message):
    args = (message.text or "").split()
    if len(args) < 2:
        await message.answer(
            "Чтобы привязать аккаунт, отправьте /link <код>.\n\n"
            "Код можно получить в веб-приложении FinBalance."
        )
        return

    code = args[1].strip().upper()
    telegram_id = str(message.from_user.id)

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{API_URL}/api/bot/confirm",
            json={"code": code, "telegram_id": telegram_id},
        ) as resp:
            if resp.status == 204:
                await message.answer(
                    "Аккаунт успешно привязан! 🎉\n\n"
                    "Теперь можно использовать /summary "
                    "для получения сводки расходов."
                )
            else:
                detail = ""
                try:
                    data = await resp.json()
                    detail = data.get("detail", "")
                except Exception:  # noqa: BLE001
                    pass
                await message.answer(
                    "Не удалось привязать аккаунт. 😕\n\n"
                    f"Код: {code}\nСтатус: {resp.status}\n{detail}"
                )


@dp.message(Command("me"))
async def me(message: types.Message):
    telegram_id = str(message.from_user.id)
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{API_URL}/api/bot/me", params={"telegram_id": telegram_id}
        ) as resp:
            try:
                data = await resp.json()
            except Exception:  # noqa: BLE001
                data = {}
            if data.get("linked"):
                await message.answer(
                    f"Ваш Telegram привязан к аккаунту:\n{data.get('email', '')}"
                )
            else:
                await message.answer(
                    "Ваш Telegram ещё не привязан к веб-аккаунту.\n\n"
                    "Получите код в веб-приложении и отправьте /link <код>."
                )


def _format_amount(amount: float) -> str:
    return f"{amount:,.2f}".replace(",", " ").replace(".", ",")


def _format_summary(data: dict) -> str:
    total = float(data.get("total_amount", 0.0))
    by_category = data.get("by_category", []) or []
    top_payees = data.get("top_payees", []) or []

    if not by_category:
        return (
            "У вас пока нет расходов в выбранной семье. 📭\n\n"
            "Загрузите CSV-выписку, чтобы увидеть сводку."
        )

    lines = [f"💰 Общая сумма расходов: {_format_amount(total)} ₽", ""]
    if by_category:
        lines.append("📊 По категориям:")
        for item in by_category[:5]:
            cat = item.get("category", "—")
            amount = float(item.get("amount", 0.0))
            count = item.get("count", 0)
            lines.append(
                f"• {cat}: {_format_amount(amount)} ₽ ({count} оп.)"
            )
    lines.append("")
    if top_payees:
        lines.append("🏷 Топ получателей:")
        for item in top_payees[:3]:
            payee = item.get("payee", "—")
            amount = float(item.get("amount", 0.0))
            lines.append(f"• {payee}: {_format_amount(amount)} ₽")

    return "\n".join(lines)


@dp.message(Command("summary"))
async def summary(message: types.Message):
    telegram_id = str(message.from_user.id)
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{API_URL}/api/bot/summary", params={"telegram_id": telegram_id}
        ) as resp:
            try:
                data = await resp.json()
            except Exception:  # noqa: BLE001
                data = {}
            if resp.status == 200:
                await message.answer(_format_summary(data))
            elif resp.status == 401:
                await message.answer(
                    "Ваш Telegram не привязан к веб-аккаунту.\n\n"
                    "Получите код в веб-приложении и отправьте /link <код>."
                )
            elif resp.status == 400:
                await message.answer(
                    "У вас нет семьи. 👨‍👩‍👧\n\n"
                    "Семья создаётся автоматически при регистрации аккаунта; "
                    "присоединить участников можно в профиле веб-приложения."
                )
            else:
                await message.answer(
                    "Не удалось получить сводку. Попробуйте ещё раз позже."
                )


async def _download_document(message: types.Message) -> bytes | None:
    document = message.document
    if document is None:
        return None
    file = await message.bot.get_file(document.file_id)
    buffer = await message.bot.download_file(file.file_path)
    return buffer.read()


@dp.message(F.document)
async def handle_document(message: types.Message):
    document = message.document
    if document is None:
        return

    filename = document.file_name or ""
    if not filename.lower().endswith(".csv"):
        await message.answer(
            "Принимаю только CSV-выписки (*.csv).\n\n"
            "Экспортируйте выписку из интернет-банка и пришлите файл сюда."
        )
        return

    telegram_id = str(message.from_user.id)
    try:
        content = await _download_document(message)
    except Exception:  # noqa: BLE001
        await message.answer(
            "Не удалось скачать файл. Попробуйте ещё раз или отправьте другой файл."
        )
        return

    if content is None:
        await message.answer("Файл пуст. Пришлите валидную CSV-выписку.")
        return

    await message.answer("Файл получен, обрабатываю выписку…")

    form = aiohttp.FormData()
    form.add_field(
        "file",
        content,
        filename=filename,
        content_type="text/csv",
    )
    form.add_field("telegram_id", telegram_id)

    async with aiohttp.ClientSession() as session:
        async with session.post(f"{API_URL}/api/bot/upload", data=form) as resp:
            try:
                data = await resp.json()
            except Exception:  # noqa: BLE001
                data = {}
            if resp.status == 201:
                await message.answer(
                    "Выписка успешно импортирована! ✅\n\n"
                    f"Разобрано операций: {data.get('parsed', 0)}\n"
                    f"Создано: {data.get('created', 0)}\n"
                    f"Пропущено дублей: {data.get('duplicates_skipped', 0)}\n\n"
                    "Посмотреть расходы можно в дашборде "
                    "веб-приложения или через /summary."
                )
            else:
                detail = data.get("detail", "")
                status_code = resp.status
                if status_code == 401:
                    await message.answer(
                        "Ваш Telegram не привязан к веб-аккаунту.\n\n"
                        "Получите код в веб-приложении и отправьте /link <код>."
                    )
                elif status_code == 400:
                    await message.answer(
                        "Не удалось импортировать выписку: "
                        f"{detail or 'файл не подходит'}"
                    )
                else:
                    await message.answer(
                        "Внутренняя ошибка сервиса. Попробуйте ещё раз позже."
                    )


async def main():
    if not bot:
        logger.warning(
            "BOT_TOKEN не задан — telegram-бот отключён. "
            "Задайте BOT_TOKEN в .env и перезапустите сервис."
        )
        while True:
            await asyncio.sleep(3600)

    logger.info("Бот запущен")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
