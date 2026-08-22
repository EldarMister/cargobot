from html import escape

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.user import cancel_keyboard, main_menu_keyboard
from app.bot.states.user import TrackingStates
from app.core.dates import local_datetime_text
from app.db.repositories import ParcelRepository, SettingRepository, UserRepository
from app.i18n import normalize_language, status_label, t, text_variants
from app.services.normalization import normalize_tracking_number
from app.services.presentation import format_parcel, format_parcel_list, warehouse_text

router = Router(name="user_parcels")


def whatsapp_link(value: str) -> str | None:
    value = value.strip()
    lowered = value.lower()
    allowed_hosts = ("wa.me/", "api.whatsapp.com/", "chat.whatsapp.com/")
    if lowered.startswith(tuple(f"https://{host}" for host in allowed_hosts)):
        return value
    if lowered.startswith(allowed_hosts):
        return f"https://{value}"
    phone_digits = "".join(character for character in value if character.isdigit())
    return f"https://wa.me/{phone_digits}" if phone_digits else None


async def _current_user(message: Message, session: AsyncSession):
    user = await UserRepository(session).by_telegram_id(message.from_user.id)
    if not user:
        await message.answer(t("register_first"))
        return None
    if not user.has_access():
        await message.answer(t("access_temporarily_denied", user.language))
        return None
    return user


@router.message(F.text.in_(text_variants("button.parcels")))
async def my_parcels(message: Message, session: AsyncSession) -> None:
    user = await _current_user(message, session)
    if not user:
        return
    language = normalize_language(user.language)
    parcels = await ParcelRepository(session).active_for_client(user.client_code)
    await message.answer(
        format_parcel_list(
            parcels,
            title=t("my_parcels_title", language),
            empty_message=t("no_active_parcels", language),
            language=language,
        ),
        parse_mode="HTML",
    )


@router.message(F.text.in_(text_variants("button.delivered")))
async def delivered_parcels(message: Message, session: AsyncSession) -> None:
    user = await _current_user(message, session)
    if not user:
        return
    language = normalize_language(user.language)
    parcels = await ParcelRepository(session).delivered_for_client(user.client_code)
    await message.answer(
        format_parcel_list(
            parcels,
            title=t("delivered_title", language),
            empty_message=t("no_delivered_parcels", language),
            language=language,
        ),
        parse_mode="HTML",
    )


@router.message(F.text == "🔑 Мой код")
async def my_code(message: Message, session: AsyncSession) -> None:
    user = await _current_user(message, session)
    if user:
        await message.answer(
            t("my_code", user.language, code=user.client_code),
            parse_mode="HTML",
        )


@router.message(F.text.in_(text_variants("button.china_address") | {"🇨🇳 Адрес склада"}))
async def warehouse(message: Message, session: AsyncSession) -> None:
    user = await _current_user(message, session)
    if user:
        settings = await SettingRepository(session).all()
        await message.answer(
            t(
                "china_address_title",
                user.language,
                warehouse=warehouse_text(settings, user.client_code, user.language),
            ),
            parse_mode="HTML",
        )


@router.message(F.text.in_(text_variants("button.profile")))
async def profile(message: Message, session: AsyncSession) -> None:
    user = await _current_user(message, session)
    if user:
        language = normalize_language(user.language)
        city = t("profile_city", language, city=escape(user.city)) if user.city else ""
        phone = t("profile_phone", language, phone=escape(user.phone)) if user.phone else ""
        await message.answer(
            t(
                "profile",
                language,
                code=user.client_code,
                name=escape(user.full_name),
                phone=phone,
                city=city,
                created_at=local_datetime_text(user.created_at),
            ),
            parse_mode="HTML",
        )


@router.message(F.text.in_(text_variants("button.contacts") | {"☎️ Поддержка"}))
async def contacts(message: Message, session: AsyncSession) -> None:
    user = await _current_user(message, session)
    if not user:
        return
    language = normalize_language(user.language)
    settings = await SettingRepository(session).all()
    company = escape(settings.get("company_name") or "BCL EXPRESS")
    whatsapp = settings.get("contact_whatsapp", "").strip()
    support = settings.get("support_username", "").strip()
    address = escape(settings.get("local_warehouse_address", "").strip()) or t(
        "not_specified", language
    )
    lines = [t("contacts_title", language, company=company), ""]
    if whatsapp:
        url = whatsapp_link(whatsapp)
        label = escape(whatsapp)
        lines.append(
            f'💬 WhatsApp: <a href="{escape(url, quote=True)}">{label}</a>'
            if url
            else f"💬 WhatsApp: {label}"
        )
    if support:
        lines.append(t("contact_telegram", language, contact=escape(support)))
    if not whatsapp and not support:
        lines.append(t("contact_missing", language))
    lines.extend(["", t("warehouse_local", language, address=address)])
    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(F.text.in_(text_variants("button.schedule")))
async def work_schedule(message: Message, session: AsyncSession) -> None:
    user = await _current_user(message, session)
    if not user:
        return
    schedule = await SettingRepository(session).get("work_schedule")
    await message.answer(
        t(
            "work_schedule",
            user.language,
            schedule=escape(schedule) if schedule else t("schedule_missing", user.language),
        ),
        parse_mode="HTML",
    )


@router.message(F.text.in_(text_variants("button.help")))
async def help_message(message: Message, session: AsyncSession) -> None:
    user = await _current_user(message, session)
    if not user:
        return
    language = normalize_language(user.language)
    settings = await SettingRepository(session).all()
    company = escape(settings.get("company_name") or "BCL EXPRESS")
    contact = settings.get("contact_whatsapp") or settings.get("support_username")
    contact_line = (
        t("help_contact", language, contact=escape(contact))
        if contact
        else t("help_contacts_section", language)
    )
    await message.answer(
        t("help", language, company=company, contact_line=contact_line),
        parse_mode="HTML",
    )


@router.message(F.text.in_(text_variants("button.track") | {"🔎 Проверить трек"}))
async def tracking_start(message: Message, state: FSMContext, session: AsyncSession) -> None:
    user = await _current_user(message, session)
    if not user:
        return
    await state.set_state(TrackingStates.tracking_number)
    await message.answer(
        t("enter_tracking", user.language),
        reply_markup=cancel_keyboard(user.language),
    )


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
            t("tracking_not_found", user.language),
            reply_markup=main_menu_keyboard(user.language),
        )
        return
    await message.answer(
        f"{status_label(parcel.status, user.language)}\n\n{format_parcel(parcel, user.language)}",
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(user.language),
    )
