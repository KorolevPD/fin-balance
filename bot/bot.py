import asyncio
import logging
from os import getenv

import aiohttp
from aiogram import Bot, Dispatcher, types
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
        "/summary - Получить сводку расходов"
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
