import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage

from app.bot.handlers import register_routers
from app.bot.middlewares import DatabaseMiddleware
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.db.session import create_engine_and_sessionmaker

logger = logging.getLogger(__name__)


async def main() -> None:
    settings = get_settings()
    setup_logging(settings.log_level)
    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN is empty. Fill it in .env before starting the bot.")

    engine, session_factory = create_engine_and_sessionmaker(settings)
    storage = RedisStorage.from_url(settings.redis_url)
    bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dispatcher = Dispatcher(storage=storage)
    dispatcher.update.outer_middleware(DatabaseMiddleware(session_factory))
    register_routers(dispatcher, settings)

    logger.info("Starting Cargo Express bot")
    try:
        await bot.delete_webhook(drop_pending_updates=False)
        await dispatcher.start_polling(bot, allowed_updates=dispatcher.resolve_used_update_types())
    finally:
        await storage.close()
        await bot.session.close()
        await engine.dispose()
        logger.info("Cargo Express bot stopped")


if __name__ == "__main__":
    asyncio.run(main())
