from html import escape

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.user import cancel_keyboard, main_menu_keyboard
from app.bot.states.user import TrackingStates
from app.core.dates import local_date_text
from app.db.repositories import ParcelRepository, SettingRepository, UserRepository
from app.services.normalization import normalize_tracking_number
from app.services.presentation import format_parcel, format_parcel_list, warehouse_text

router = Router(name="user_parcels")


async def _current_user(message: Message, session: AsyncSession):
    user = await UserRepository(session).by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("Сначала зарегистрируйтесь через /start.")
        return None
    if not user.has_access():
        await message.answer("⛔ Доступ к боту временно ограничен. Обратитесь к поддержке.")
        return None
    return user


@router.message(F.text == "📦 Мои товары")
async def my_parcels(message: Message, session: AsyncSession) -> None:
    user = await _current_user(message, session)
    if not user:
        return
    parcels = await ParcelRepository(session).for_client(user.client_code)
    await message.answer(format_parcel_list(parcels), parse_mode="HTML")


@router.message(F.text == "🔑 Мой код")
async def my_code(message: Message, session: AsyncSession) -> None:
    user = await _current_user(message, session)
    if user:
        await message.answer(f"Ваш код клиента: <b>{user.client_code}</b>", parse_mode="HTML")


@router.message(F.text == "🇨🇳 Адрес склада")
async def warehouse(message: Message, session: AsyncSession) -> None:
    user = await _current_user(message, session)
    if user:
        settings = await SettingRepository(session).all()
        await message.answer(warehouse_text(settings, user.client_code), parse_mode="HTML")


@router.message(F.text == "👤 Профиль")
async def profile(message: Message, session: AsyncSession) -> None:
    user = await _current_user(message, session)
    if user:
        city = f"\nГород: {escape(user.city)}" if user.city else ""
        await message.answer(
            "👤 <b>Профиль</b>\n\n"
            f"ФИО: {escape(user.full_name)}\n"
            f"Код: <b>{user.client_code}</b>\n"
            f"Телефон: {escape(user.phone)}{city}\n"
            f"Регистрация: {local_date_text(user.created_at)}",
            parse_mode="HTML",
        )


@router.message(F.text == "☎️ Поддержка")
async def support(message: Message, session: AsyncSession) -> None:
    contact = await SettingRepository(session).get("support_username")
    await message.answer(f"☎️ Поддержка: {escape(contact) if contact else 'контакт пока не указан'}")


@router.message(F.text == "🔎 Проверить трек")
async def tracking_start(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if not await _current_user(message, session):
        return
    await state.set_state(TrackingStates.tracking_number)
    await message.answer("Введите трек-код:", reply_markup=cancel_keyboard())


@router.message(TrackingStates.tracking_number, F.text)
async def tracking_result(message: Message, state: FSMContext, session: AsyncSession) -> None:
    user = await _current_user(message, session)
    if not user:
        await state.clear()
        return
    tracking = normalize_tracking_number(message.text)
    parcel = await ParcelRepository(session).by_tracking(tracking)
    await state.clear()
    if not parcel or parcel.client_code != user.client_code:
        await message.answer(
            "Товар с таким трек-кодом не найден среди ваших товаров.",
            reply_markup=main_menu_keyboard(),
        )
        return
    await message.answer(
        f"{parcel.status.label}\n\n{format_parcel(parcel)}",
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(),
    )
