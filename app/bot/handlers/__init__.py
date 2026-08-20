from aiogram import Dispatcher

from app.bot.handlers.admin import build_admin_router
from app.bot.handlers.user import build_user_router
from app.core.config import Settings


def register_routers(dispatcher: Dispatcher, settings: Settings) -> None:
    dispatcher.include_router(build_admin_router(settings))
    dispatcher.include_router(build_user_router())
