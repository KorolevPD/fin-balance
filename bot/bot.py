import asyncio
import logging
import sys
from os import getenv

from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = getenv("BOT_TOKEN")
API_URL = getenv("API_URL", "http://backend:8000")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def start(message: types.Message):
    await message.answer(
        "Добро пожаловать в FinBalance! 🏦\n\n"
        "Я помогу вам управлять семейным бюджетом.\n\n"
        "Команды:\n"
        "/start - Начать работу\n"
        "/summary - Получить сводку расходов"
    )

async def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN не задан")
        sys.exit(1)
    
    logger.info("Бот запущен")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
