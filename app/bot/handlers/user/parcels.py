from html import escape

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.user import cancel_keyboard, main_menu_keyboard
from app.bot.states.user import TrackingStates
from app.core.dates import local_datetime_text
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
    parcels = await ParcelRepository(session).active_for_client(user.client_code)
    await message.answer(
        format_parcel_list(
            parcels,
            empty_message="📦 <b>Мои товары</b>\n\nУ вас пока нет активных товаров.",
        ),
        parse_mode="HTML",
    )


@router.message(F.text == "🗄 Выданные товары")
async def delivered_parcels(message: Message, session: AsyncSession) -> None:
    user = await _current_user(message, session)
    if not user:
        return
    parcels = await ParcelRepository(session).delivered_for_client(user.client_code)
    await message.answer(
        format_parcel_list(
            parcels,
            title="🗄 Выданные товары",
            empty_message=(
                "🗄 <b>Выданные товары</b>\n\n"
                "В вашем архиве пока нет товаров.\n"
                "Когда вы получите свои первые товары, они отобразятся здесь."
            ),
        ),
        parse_mode="HTML",
    )


@router.message(F.text == "🔑 Мой код")
async def my_code(message: Message, session: AsyncSession) -> None:
    user = await _current_user(message, session)
    if user:
        await message.answer(f"Ваш код клиента: <b>{user.client_code}</b>", parse_mode="HTML")


@router.message(F.text.in_({"🏠 Адрес в Китае", "🇨🇳 Адрес склада"}))
async def warehouse(message: Message, session: AsyncSession) -> None:
    user = await _current_user(message, session)
    if user:
        settings = await SettingRepository(session).all()
        await message.answer(
            "🏠 <b>Ваш адрес в Китае:</b>\n\n" + warehouse_text(settings, user.client_code),
            parse_mode="HTML",
        )


@router.message(F.text == "👤 Профиль")
async def profile(message: Message, session: AsyncSession) -> None:
    user = await _current_user(message, session)
    if user:
        city = f"\nГород: {escape(user.city)}" if user.city else ""
        phone = f"\n📱 Телефон: {escape(user.phone)}" if user.phone else ""
        await message.answer(
            "👤 <b>Ваш профиль</b>\n\n"
            f"🔑 Код клиента: <b>{user.client_code}</b>\n"
            f"📝 ФИО: {escape(user.full_name)}"
            f"{phone}{city}\n"
            f"📅 Дата регистрации: {local_datetime_text(user.created_at)}",
            parse_mode="HTML",
        )


@router.message(F.text.in_({"📍 Контакты/Адрес склада", "☎️ Поддержка"}))
async def contacts(message: Message, session: AsyncSession) -> None:
    if not await _current_user(message, session):
        return
    settings = await SettingRepository(session).all()
    company = escape(settings.get("company_name") or "BCL EXPRESS")
    whatsapp = settings.get("contact_whatsapp", "").strip()
    phone_digits = "".join(character for character in whatsapp if character.isdigit())
    support = settings.get("support_username", "").strip()
    address = escape(settings.get("local_warehouse_address", "").strip()) or "пока не указан"
    lines = [f"📍 <b>{company} — Контакты и склад</b>", ""]
    if whatsapp:
        lines.append(f"💬 WhatsApp: {escape(whatsapp)}")
    if phone_digits:
        url = f"https://wa.me/{phone_digits}"
        lines.append(f'📱 Ссылка: <a href="{url}">wa.me/{phone_digits}</a>')
    elif support:
        lines.append(f"📱 Telegram: {escape(support)}")
    else:
        lines.append("💬 Контакт: пока не указан")
    lines.extend(["", f"🏢 <b>Адрес склада:</b> {address}"])
    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(F.text == "🕘 График работы")
async def work_schedule(message: Message, session: AsyncSession) -> None:
    if not await _current_user(message, session):
        return
    schedule = await SettingRepository(session).get("work_schedule")
    await message.answer(
        "🕘 <b>График работы</b>\n\n"
        + (escape(schedule) if schedule else "График пока не указан."),
        parse_mode="HTML",
    )


@router.message(F.text == "❓ Помощь")
async def help_message(message: Message, session: AsyncSession) -> None:
    if not await _current_user(message, session):
        return
    settings = await SettingRepository(session).all()
    company = escape(settings.get("company_name") or "BCL EXPRESS")
    contact = settings.get("contact_whatsapp") or settings.get("support_username")
    contact_line = (
        f"напишите нам: {escape(contact)}" if contact else "откройте раздел «Контакты/Адрес склада»"
    )
    await message.answer(
        f"📖 <b>Справка по боту {company}:</b>\n\n"
        "📦 <b>Мои товары</b> — список активных товаров и их статусы\n"
        "🔍 <b>Поиск по трек-коду</b> — статус конкретного товара\n"
        "📍 <b>Контакты/Адрес склада</b> — наш адрес и контакты\n"
        "🕘 <b>График работы</b> — рабочие часы\n"
        "🏠 <b>Адрес в Китае</b> — персональный адрес для отправки\n"
        "👤 <b>Профиль</b> — информация о вашем аккаунте\n"
        "🗄 <b>Выданные товары</b> — архив полученных товаров\n\n"
        f"💡 Если нужна помощь, {contact_line}.",
        parse_mode="HTML",
    )


@router.message(F.text.in_({"🔍 Поиск по трек-коду", "🔎 Проверить трек"}))
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
