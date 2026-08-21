import asyncio
import logging
from contextlib import contextmanager, suppress

import uvicorn
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import MenuButtonCommands
from sqlalchemy import select

from app.bot.handlers import register_routers
from app.bot.menu_button import set_admin_menu_button
from app.bot.middlewares import DatabaseMiddleware
from app.core.config import Settings, get_settings
from app.core.logging import setup_logging
from app.db.models import User
from app.db.session import create_engine_and_sessionmaker
from app.services.delivery_reminder_service import delivery_reminder_loop
from app.web.app import create_web_app

logger = logging.getLogger(__name__)


class EmbeddedUvicornServer(uvicorn.Server):
    @contextmanager
    def capture_signals(self):
        """Let aiogram own process signals while Uvicorn runs in the same event loop."""
        yield


async def configure_menu_buttons(bot: Bot, settings: Settings, session_factory=None) -> None:
    """Keep the default command menu for clients and expose the Mini App to admins."""
    await bot.set_chat_menu_button(menu_button=MenuButtonCommands())
    if not settings.public_web_url:
        logger.warning(
            "Admin Mini App menu button is disabled: WEB_APP_URL and RAILWAY_PUBLIC_DOMAIN are empty"
        )
        return

    admin_ids = set(settings.admin_id_set)
    if session_factory is not None:
        async with session_factory() as session:
            database_admin_ids = await session.scalars(
                select(User.telegram_id).where(
                    User.telegram_id.is_not(None),
                    User.is_admin.is_(True),
                )
            )
            admin_ids.update(database_admin_ids)

    for admin_id in sorted(admin_ids):
        try:
            await set_admin_menu_button(bot, admin_id, settings)
        except TelegramAPIError:
            logger.exception("Could not configure Mini App menu button for admin %s", admin_id)


async def main() -> None:
    settings = get_settings()
    setup_logging(settings.log_level)
    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN is empty. Fill it in .env before starting the bot.")

    engine, session_factory = create_engine_and_sessionmaker(settings)
    storage = MemoryStorage()
    bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dispatcher = Dispatcher(storage=storage)
    dispatcher.update.outer_middleware(DatabaseMiddleware(session_factory))
    register_routers(dispatcher, settings)
    web_server = EmbeddedUvicornServer(
        uvicorn.Config(
            create_web_app(bot, session_factory, settings),
            host="0.0.0.0",
            port=settings.port,
            log_config=None,
            access_log=False,
        )
    )
    web_task = asyncio.create_task(web_server.serve(), name="web-panel")
    reminder_task = asyncio.create_task(
        delivery_reminder_loop(bot, session_factory),
        name="delivery-reminders",
    )

    logger.info("Starting BCL Express bot")
    try:
        await bot.delete_webhook(drop_pending_updates=False)
        await configure_menu_buttons(bot, settings, session_factory)
        await dispatcher.start_polling(bot, allowed_updates=dispatcher.resolve_used_update_types())
    finally:
        web_server.should_exit = True
        reminder_task.cancel()
        with suppress(asyncio.CancelledError):
            await reminder_task
        await web_task
        await storage.close()
        await bot.session.close()
        await engine.dispose()
        logger.info("BCL Express bot stopped")


if __name__ == "__main__":
    asyncio.run(main())
