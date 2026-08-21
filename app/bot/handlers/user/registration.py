import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.user import (
    cancel_keyboard,
    main_menu_keyboard,
    start_keyboard,
)
from app.bot.states.user import LinkStates, RegistrationStates
from app.db.repositories import SettingRepository
from app.services.normalization import is_valid_client_code, normalize_client_code
from app.services.presentation import warehouse_text
from app.services.user_service import UserService, UserServiceError

logger = logging.getLogger(__name__)
router = Router(name="registration")


@router.message(F.text.in_({"🆕 Регистрация нового клиента", "🆕 Новый клиент"}))
async def new_client(message: Message, state: FSMContext) -> None:
    await state.set_state(RegistrationStates.full_name)
    await message.answer("✍️ Введите ваше ФИО для регистрации:", reply_markup=cancel_keyboard())


@router.message(RegistrationStates.full_name, F.text)
async def registration_name(message: Message, state: FSMContext, session: AsyncSession) -> None:
    full_name = " ".join(message.text.split())
    if len(full_name) < 3:
        await message.answer("Пожалуйста, укажите полное имя.")
        return
    try:
        user = await UserService(session).register(
            telegram_id=message.from_user.id,
            full_name=full_name,
        )
    except UserServiceError as exc:
        await state.clear()
        await message.answer(str(exc), reply_markup=main_menu_keyboard())
        return
    await state.clear()
    settings = await SettingRepository(session).all()
    await message.answer(
        "🎉 <b>Регистрация завершена!</b>\n\n"
        f"Ваш новый код клиента: <b>{user.client_code}</b>\n\n"
        f"{warehouse_text(settings, user.client_code)}",
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(),
    )
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
        if str(exc).startswith("Этот код уже привязан"):
            await state.clear()
            await message.answer(
                "❌ Этот старый код уже привязан к другому пользователю.",
                reply_markup=start_keyboard(),
            )
            return
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
        f"Ваш код клиента: <b>{user.client_code}</b>\n\n"
        f"{warehouse_text(settings, user.client_code)}",
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(),
    )
    logger.info("Client linked: code=%s telegram_id=%s", user.client_code, message.from_user.id)
