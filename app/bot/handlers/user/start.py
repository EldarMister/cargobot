from contextlib import suppress
from html import escape

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.user import (
    USER_SELECTABLE_LANGUAGES,
    language_keyboard,
    main_menu_keyboard,
    start_keyboard,
)
from app.bot.menu_button import set_admin_menu_button
from app.core.config import get_settings
from app.db.repositories import SettingRepository, UserRepository
from app.i18n import language_for_text, normalize_language, t, text_variants

router = Router(name="user_start")


async def _language_for(message: Message, state: FSMContext, session: AsyncSession) -> str:
    user = await UserRepository(session).by_telegram_id(message.from_user.id)
    if user and user.language:
        return normalize_language(user.language)
    return normalize_language((await state.get_data()).get("language"))


async def _send_start(
    message: Message,
    session: AsyncSession,
    language: str,
    telegram_id: int | None = None,
) -> None:
    user = await UserRepository(session).by_telegram_id(telegram_id or message.from_user.id)
    if user:
        if user.has_access():
            await message.answer(
                t(
                    "welcome_back",
                    language,
                    name=escape(user.full_name),
                    code=user.client_code,
                ),
                parse_mode="HTML",
                reply_markup=main_menu_keyboard(language),
            )
        else:
            await message.answer(t("access_denied", language))
        return
    settings = await SettingRepository(session).all()
    company_name = escape(settings["company_name"] or "BCL EXPRESS")
    await message.answer(
        t("welcome", language, company=company_name),
        parse_mode="HTML",
        reply_markup=start_keyboard(language),
    )


@router.message(CommandStart())
async def start(message: Message, state: FSMContext, session: AsyncSession, bot: Bot) -> None:
    await state.clear()
    user = await UserRepository(session).by_telegram_id(message.from_user.id)
    settings = get_settings()
    if message.from_user.id in settings.admin_id_set or (user and user.is_admin):
        with suppress(TelegramAPIError):
            await set_admin_menu_button(bot, message.from_user.id, settings)
    if user and user.language:
        await _send_start(message, session, normalize_language(user.language))
        return
    await message.answer(
        "Выберите язык · Choose your language",
        reply_markup=language_keyboard("start"),
    )


@router.callback_query(F.data.startswith("language:"))
async def select_language(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    _, context, language = callback.data.split(":", 2)
    if language not in USER_SELECTABLE_LANGUAGES or not callback.message:
        await callback.answer()
        return
    user = await UserRepository(session).by_telegram_id(callback.from_user.id)
    if user:
        user.language = language
        await session.commit()
    await state.update_data(language=language)
    with suppress(TelegramAPIError):
        await callback.message.delete()
    await callback.answer()
    if context == "change":
        await callback.message.answer(
            t("language_changed", language),
            reply_markup=main_menu_keyboard(language) if user else start_keyboard(language),
        )
    else:
        await _send_start(callback.message, session, language, callback.from_user.id)


@router.message(Command("language"))
@router.message(F.text.in_(text_variants("button.language")))
async def change_language(message: Message) -> None:
    await message.answer(
        "Выберите язык · Choose your language",
        reply_markup=language_keyboard("change"),
    )


@router.message(F.text.in_(text_variants("button.cancel")))
@router.message(Command("cancel"))
async def cancel(message: Message, state: FSMContext, session: AsyncSession) -> None:
    language = language_for_text(
        "button.cancel",
        message.text or "",
        await _language_for(message, state, session),
    )
    await state.clear()
    user = await UserRepository(session).by_telegram_id(message.from_user.id)
    markup = main_menu_keyboard(language) if user and user.has_access() else start_keyboard(language)
    await message.answer(t("cancelled", language), reply_markup=markup)
