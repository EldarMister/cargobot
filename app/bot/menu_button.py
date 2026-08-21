from aiogram import Bot
from aiogram.types import MenuButtonWebApp, WebAppInfo

from app.core.config import Settings


async def set_admin_menu_button(bot: Bot, telegram_id: int, settings: Settings) -> bool:
    """Expose the web admin panel in a specific administrator's private chat."""
    web_url = settings.public_web_url
    if not web_url:
        return False
    await bot.set_chat_menu_button(
        chat_id=telegram_id,
        menu_button=MenuButtonWebApp(
            text="Админ-панель",
            web_app=WebAppInfo(url=f"{web_url}/panel"),
        ),
    )
    return True
