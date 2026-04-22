import asyncio
import os
from os import getenv
from zoneinfo import ZoneInfo

import sentry_sdk
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
from loguru import logger

from database.db import engine
from database.models import Base
from database.orm_query import BadWordsRepository
from handlers.user_handler import router
from logger_config import setup_logging
from scheduler import send_daily_report


load_dotenv()
TOKEN = getenv("BOT_TOKEN")

setup_logging()

if not TOKEN:
    logger.error("❌ BOT_TOKEN не найден в .env!")
    raise ValueError("BOT_TOKEN must be set")

ALLOWED_UPDATES = [
    "message",
    "edited_message",
    "channel_post",
    "edited_channel_post",
    "callback_query",
    "inline_query",
    "chosen_inline_result",
    "shipping_query",
    "pre_checkout_query",
    "poll",
    "poll_answer",
    "my_chat_member",
    "chat_member",
    "chat_join_request",
]

bot = Bot(token=TOKEN)

dp = Dispatcher(storage=MemoryStorage())

dp.include_router(router)


async def on_startup(bot):
    run_param = False

    logger.info("🚀 Инициализация базы данных...")
    try:
        if run_param:
            logger.warning("⚠️ Пересоздание базы данных...")
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            logger.info("✓ База данных очищена")

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✓ База данных инициализирована успешно")
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации базы данных: {e}")
        raise


async def on_shutdown(bot):
    logger.info("⛔ Бот завершает работу")


async def main() -> None:
    logger.info("📱 Запуск бота...")
    await bot.delete_webhook(drop_pending_updates=True)
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    scheduler = AsyncIOScheduler(timezone=ZoneInfo("Europe/Kyiv"))
    try:
        scheduler.add_job(send_daily_report, "cron", hour=23, minute=1, args=[bot])
        scheduler.add_job(
            BadWordsRepository.clear_old_logs, trigger="cron", hour=3, minute=0, args=[7]
        )

        scheduler.start()
        logger.info("✓ Планировщик запущен")
        logger.info("✅ Бот готов к приему сообщений")
        await dp.start_polling(bot, allowed_updates=ALLOWED_UPDATES)
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        raise


if __name__ == "__main__":
    logger.info("🔧 Инициализация приложения...")
    asyncio.run(main())
