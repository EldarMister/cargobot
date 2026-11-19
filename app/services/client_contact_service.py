import re
from html import escape

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.db.models import User
from app.services.client_message_service import ClientMessageError


async def open_client_contact(bot: Bot, user: User, *, expected_telegram_id: int, admin_id: int) -> dict:
    if not user.telegram_id:
        raise ClientMessageError(
            "Telegram клиента не привязан. Клиент должен открыть бота и привязать свой H-код."
        )
    if user.telegram_id != expected_telegram_id:
        raise ClientMessageError("Telegram клиента изменился. Откройте карточку заново.")
    # Resolve the current username rather than keeping a potentially reassigned one in the database.
    username = None
    try:
        chat = await bot.get_chat(user.telegram_id)
        username = chat.username
    except TelegramAPIError:
        pass
    if isinstance(username, str) and re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,31}", username):
        return {"url": f"https://t.me/{username}", "profile_sent": False}
    # tg://user links are supported by Bot API profile buttons, not by normal Mini App links.
    # Send only to the requesting admin; never contact the client as a side effect of opening a profile.
    try:
        await bot.send_message(
            chat_id=admin_id,
            text=(
                "👤 <b>Личный Telegram клиента</b>\n"
                f"{escape(user.full_name)} · {escape(user.client_code)}\n\n"
                "Откройте профиль кнопкой ниже и нажмите «Сообщение». "
                "Возможность написать зависит от настроек приватности клиента."
            ),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="Открыть профиль клиента", url=f"tg://user?id={user.telegram_id}"),
            ]]),
        )
    except TelegramAPIError as exc:
        raise ClientMessageError("Не удалось открыть контакт. Попробуйте ещё раз.", 502) from exc
    return {"url": None, "profile_sent": True}
