import logging
from html import escape

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.user import (
    cancel_keyboard,
    city_keyboard,
    main_menu_keyboard,
    phone_keyboard,
)
from app.bot.states.user import LinkStates, RegistrationStates
from app.db.repositories import SettingRepository
from app.services.normalization import is_valid_client_code, normalize_client_code
from app.services.presentation import warehouse_text
from app.services.user_service import UserService, UserServiceError

logger = logging.getLogger(__name__)
router = Router(name="registration")


@router.message(F.text == "🆕 Новый клиент")
async def new_client(message: Message, state: FSMContext) -> None:
    await state.set_state(RegistrationStates.full_name)
    await message.answer("Введите ваше ФИО:", reply_markup=cancel_keyboard())


@router.message(RegistrationStates.full_name, F.text)
async def registration_name(message: Message, state: FSMContext) -> None:
    full_name = " ".join(message.text.split())
    if len(full_name) < 3:
        await message.answer("Пожалуйста, укажите полное имя.")
        return
    await state.update_data(full_name=full_name)
    await state.set_state(RegistrationStates.phone)
    await message.answer("Поделитесь номером телефона кнопкой ниже:", reply_markup=phone_keyboard())


@router.message(RegistrationStates.phone, F.contact)
async def registration_phone(message: Message, state: FSMContext) -> None:
    if message.contact.user_id not in (None, message.from_user.id):
        await message.answer("Нужно отправить именно свой номер телефона.")
        return
    await state.update_data(phone=message.contact.phone_number)
    await state.set_state(RegistrationStates.city)
    await message.answer("Укажите город или нажмите «Пропустить»:", reply_markup=city_keyboard())


@router.message(RegistrationStates.phone)
async def registration_phone_invalid(message: Message) -> None:
    await message.answer("Используйте кнопку «📱 Поделиться номером».", reply_markup=phone_keyboard())


@router.message(RegistrationStates.city, F.text)
async def registration_city(message: Message, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    city = None if message.text.casefold() == "пропустить" else " ".join(message.text.split())
    try:
        user = await UserService(session).register(
            telegram_id=message.from_user.id,
            full_name=data["full_name"],
            phone=data["phone"],
            city=city,
        )
    except UserServiceError as exc:
        await state.clear()
        await message.answer(str(exc), reply_markup=main_menu_keyboard())
        return
    await state.clear()
    settings = await SettingRepository(session).all()
    await message.answer(
        "✅ <b>Регистрация завершена</b>\n\n"
        f"Ваш код клиента: <b>{user.client_code}</b>\n"
        "Добавляйте этот код к данным получателя при каждой покупке.",
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(),
    )
    await message.answer(warehouse_text(settings, user.client_code), parse_mode="HTML")
    logger.info("New client registered: code=%s telegram_id=%s", user.client_code, message.from_user.id)


@router.message(F.text == "🔗 Привязать существующий код")
async def link_client(message: Message, state: FSMContext) -> None:
    await state.set_state(LinkStates.client_code)
    await message.answer("🔑 Введите ваш код клиента, например J-0001", reply_markup=cancel_keyboard())


@router.message(LinkStates.client_code, F.text)
async def link_code(message: Message, state: FSMContext) -> None:
    if not is_valid_client_code(message.text):
        await message.answer("Неверный формат. Введите код вида J-0001.")
        return
    await state.update_data(client_code=normalize_client_code(message.text), attempts=0)
    await state.set_state(LinkStates.full_name)
    await message.answer("Введите ФИО точно так же, как оно записано в базе.")


@router.message(LinkStates.full_name, F.text)
async def link_name(message: Message, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    try:
        user = await UserService(session).link_existing(
            telegram_id=message.from_user.id,
            client_code=data["client_code"],
            full_name=message.text,
        )
    except UserServiceError as exc:
        attempts = int(data.get("attempts", 0)) + 1
        if attempts >= 5:
            await state.clear()
            await message.answer(
                "Слишком много неудачных попыток. Начните заново или обратитесь в поддержку.",
                reply_markup=main_menu_keyboard(),
            )
        else:
            await state.update_data(attempts=attempts)
            await message.answer(f"{exc}\nОсталось попыток: {5 - attempts}.")
        return
    await state.clear()
    settings = await SettingRepository(session).all()
    await message.answer(
        "✅ <b>Профиль успешно привязан!</b>\n\n"
        f"ФИО: {escape(user.full_name)}\n"
        f"Код клиента: <b>{user.client_code}</b>\n"
        f"Телефон: {escape(user.phone)}",
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(),
    )
    await message.answer(warehouse_text(settings, user.client_code), parse_mode="HTML")
    logger.info("Client linked: code=%s telegram_id=%s", user.client_code, message.from_user.id)
