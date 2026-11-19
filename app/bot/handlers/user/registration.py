import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.user import (
    cancel_keyboard,
    main_menu_keyboard,
    phone_keyboard,
    start_keyboard,
)
from app.bot.states.user import LinkStates, RegistrationStates
from app.db.repositories import SettingRepository, UserRepository
from app.i18n import language_for_text, normalize_language, t, text_variants
from app.services.normalization import is_valid_client_code, normalize_client_code, normalize_phone
from app.services.presentation import warehouse_text
from app.services.user_service import UserService, UserServiceError

logger = logging.getLogger(__name__)
router = Router(name="registration")


async def _state_language(state: FSMContext) -> str:
    return normalize_language((await state.get_data()).get("language"))


@router.message(F.text.in_(text_variants("button.register") | {"🆕 Новый клиент"}))
async def new_client(message: Message, state: FSMContext) -> None:
    language = language_for_text("button.register", message.text, await _state_language(state))
    await state.update_data(language=language)
    await state.set_state(RegistrationStates.full_name)
    await message.answer(t("enter_name", language), reply_markup=cancel_keyboard(language))


@router.message(RegistrationStates.full_name, F.text)
async def registration_name(message: Message, state: FSMContext, session: AsyncSession) -> None:
    language = await _state_language(state)
    full_name = " ".join(message.text.split())
    if len(full_name) < 3:
        await message.answer(t("full_name_required", language))
        return
    await state.update_data(full_name=full_name)
    await state.set_state(RegistrationStates.phone)
    await message.answer(t("phone_request", language), reply_markup=phone_keyboard(language))


def _own_phone(message: Message) -> str:
    if message.contact:
        if message.contact.user_id != message.from_user.id or message.chat.type != "private":
            return ""
        return normalize_phone("+" + message.contact.phone_number.lstrip("+"))
    return normalize_phone(message.text or "")


@router.message(RegistrationStates.phone, F.contact)
@router.message(RegistrationStates.phone, F.text)
async def registration_phone(message: Message, state: FSMContext, session: AsyncSession) -> None:
    language = await _state_language(state)
    phone = _own_phone(message)
    if not phone:
        await message.answer(t("phone_invalid", language), reply_markup=phone_keyboard(language))
        return
    data = await state.get_data()
    try:
        user = await UserService(session).register(
            telegram_id=message.from_user.id,
            full_name=data["full_name"],
            phone=phone,
            language=language,
        )
    except UserServiceError as exc:
        await state.clear()
        await message.answer(
            t(f"error.{exc.code}", language),
            reply_markup=main_menu_keyboard(language),
        )
        return
    await state.clear()
    settings = await SettingRepository(session).all()
    await message.answer(
        t(
            "registration_complete",
            language,
            code=user.client_code,
            warehouse=warehouse_text(settings, user.client_code, language),
        ),
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(language),
    )
    logger.info("New client registered: code=%s telegram_id=%s", user.client_code, message.from_user.id)


@router.message(F.text.in_(text_variants("button.link")))
async def link_client(message: Message, state: FSMContext) -> None:
    language = language_for_text("button.link", message.text, await _state_language(state))
    await state.update_data(language=language)
    await state.set_state(LinkStates.client_code)
    await message.answer(t("enter_client_code", language), reply_markup=cancel_keyboard(language))


@router.message(LinkStates.client_code, F.text)
async def link_code(message: Message, state: FSMContext) -> None:
    language = await _state_language(state)
    if not is_valid_client_code(message.text):
        await message.answer(t("invalid_client_code", language))
        return
    await state.update_data(client_code=normalize_client_code(message.text), attempts=0)
    await state.set_state(LinkStates.full_name)
    await message.answer(t("enter_exact_name", language))


@router.message(LinkStates.full_name, F.text)
async def link_name(message: Message, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    language = normalize_language(data.get("language"))
    try:
        user = await UserService(session).link_existing(
            telegram_id=message.from_user.id,
            client_code=data["client_code"],
            full_name=message.text,
        )
    except UserServiceError as exc:
        if exc.code == "code_linked":
            await state.clear()
            await message.answer(
                t("code_already_linked", language),
                reply_markup=start_keyboard(language),
            )
            return
        attempts = int(data.get("attempts", 0)) + 1
        if attempts >= 5:
            await state.clear()
            await message.answer(
                t("too_many_attempts", language),
                reply_markup=main_menu_keyboard(language),
            )
        else:
            await state.update_data(attempts=attempts)
            await message.answer(
                t(
                    "attempts_left",
                    language,
                    error=t(f"error.{exc.code}", language),
                    count=5 - attempts,
                )
            )
        return
    user.language = language
    await state.clear()
    settings = await SettingRepository(session).all()
    await message.answer(
        t(
            "profile_linked",
            language,
            code=user.client_code,
            warehouse=warehouse_text(settings, user.client_code, language),
        ),
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(language),
    )
    logger.info("Client linked: code=%s telegram_id=%s", user.client_code, message.from_user.id)
    if not normalize_phone(user.phone):
        await message.answer(t("phone_request_existing", language), reply_markup=phone_keyboard(language))


@router.message(F.contact)
async def update_own_phone(message: Message, session: AsyncSession) -> None:
    user = await UserRepository(session).by_telegram_id(message.from_user.id)
    if not user or not user.has_access():
        return
    phone = _own_phone(message)
    language = normalize_language(user.language)
    if not phone:
        await message.answer(t("phone_invalid", language), reply_markup=phone_keyboard(language))
        return
    user.phone = phone
    await session.flush()
    await message.answer(t("phone_saved", language), reply_markup=main_menu_keyboard(language))
