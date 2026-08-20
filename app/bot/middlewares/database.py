import logging
from collections.abc import Awaitable, Callable
from contextlib import suppress
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger(__name__)


class DatabaseMiddleware(BaseMiddleware):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async with self.session_factory() as session:
            data["session"] = session
            try:
                result = await handler(event, data)
                await session.commit()
                return result
            except Exception:
                await session.rollback()
                logger.exception("Unhandled update error")
                message = event if hasattr(event, "answer") else getattr(event, "message", None)
                callback = getattr(event, "callback_query", None)
                with suppress(Exception):
                    if message:
                        await message.answer("❌ Произошла ошибка. Повторите действие позже.")
                    elif callback:
                        await callback.answer("Произошла ошибка. Повторите позже.", show_alert=True)
                return None
