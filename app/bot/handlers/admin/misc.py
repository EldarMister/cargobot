import logging
from datetime import UTC, datetime
from html import escape
from zoneinfo import ZoneInfo

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.admin import admin_menu_keyboard, settings_keyboard
from app.bot.keyboards.user import cancel_keyboard
from app.bot.states.admin import AdminStates
from app.core.config import get_settings
from app.core.enums import ParcelStatus
from app.db.models import Import, Parcel, User
from app.db.repositories import SettingRepository

logger = logging.getLogger(__name__)
router = Router(name="admin_misc")


@router.message(F.text == "📊 Статистика")
async def statistics(message: Message, session: AsyncSession) -> None:
    async def count(model, *conditions) -> int:
        return int(await session.scalar(select(func.count(model.id)).where(*conditions)) or 0)

    timezone_name = get_settings().timezone
    today = datetime.now(ZoneInfo(timezone_name)).date()
    parcel_local_date = func.date(func.timezone(timezone_name, Parcel.created_at))
    import_local_date = func.date(func.timezone(timezone_name, Import.created_at))
    lines = [
        "📊 <b>Статистика</b>",
        "",
        f"Всего клиентов: {await count(User)}",
        f"Клиентов с Telegram: {await count(User, User.telegram_id.is_not(None))}",
        f"Всего товаров: {await count(Parcel)}",
        f"🇨🇳 На складе Китая: {await count(Parcel, Parcel.status == ParcelStatus.CHINA_WAREHOUSE)}",
        f"🚚 В пути: {await count(Parcel, Parcel.status == ParcelStatus.IN_TRANSIT)}",
        f"🛬 Прибывших: {await count(Parcel, Parcel.status == ParcelStatus.ARRIVED_COUNTRY)}",
        f"📦 Готовых к выдаче: {await count(Parcel, Parcel.status == ParcelStatus.READY_FOR_PICKUP)}",
        f"✅ Выданных: {await count(Parcel, Parcel.status == ParcelStatus.DELIVERED)}",
        f"Товаров за сегодня: {await count(Parcel, parcel_local_date == today)}",
        f"Импортов за сегодня: {await count(Import, import_local_date == today)}",
    ]
    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(F.text == "⚙️ Настройки")
async def settings_menu(message: Message, session: AsyncSession) -> None:
    values = await SettingRepository(session).all()
    await message.answer(
        "⚙️ <b>Настройки</b>\n\n"
        f"Компания: {escape(values['company_name']) or '—'}\n"
        f"Стандартный срок: {escape(values['default_transit_days']) or '12'} дней\n"
        f"<b>Склад 1</b>\n"
        f"Получатель: {escape(values['warehouse_receiver']) or '—'}\n"
        f"Телефон: {escape(values['warehouse_phone']) or '—'}\n"
        f"Адрес: {escape(values['warehouse_address']) or '—'}\n"
        f"Название: {escape(values['warehouse_name']) or '—'}\n\n"
        f"<b>Склад 2</b>\n"
        f"Получатель: {escape(values['warehouse_receiver_2']) or '—'}\n"
        f"Телефон: {escape(values['warehouse_phone_2']) or '—'}\n"
        f"Адрес: {escape(values['warehouse_address_2']) or '—'}\n"
        f"Название: {escape(values['warehouse_name_2']) or '—'}\n\n"
        f"Telegram поддержки: {escape(values['support_username']) or '—'}\n"
        f"WhatsApp: {escape(values['contact_whatsapp']) or '—'}\n"
        f"Местный склад: {escape(values['local_warehouse_address']) or '—'}\n"
        f"График работы: {escape(values['work_schedule']) or '—'}",
        parse_mode="HTML",
        reply_markup=settings_keyboard(),
    )


@router.callback_query(F.data.startswith("setting:"))
async def setting_start(callback: CallbackQuery, state: FSMContext) -> None:
    key = callback.data.split(":", 1)[1]
    if key not in {
        "company_name",
        "default_transit_days",
        "warehouse_receiver",
        "warehouse_phone",
        "warehouse_address",
        "warehouse_name",
        "warehouse_receiver_2",
        "warehouse_phone_2",
        "warehouse_address_2",
        "warehouse_name_2",
        "support_username",
        "contact_whatsapp",
        "local_warehouse_address",
        "work_schedule",
    }:
        await callback.answer("Неизвестная настройка", show_alert=True)
        return
    await state.set_state(AdminStates.setting_value)
    await state.update_data(setting_key=key)
    await callback.message.answer("Введите новое значение:", reply_markup=cancel_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("warehouse_delete:"))
async def warehouse_delete_start(callback: CallbackQuery) -> None:
    slot = int(callback.data.rsplit(":", 1)[1])
    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Да, удалить", callback_data=f"warehouse_delete_confirm:{slot}"
                ),
                InlineKeyboardButton(text="❌ Отмена", callback_data="warehouse_delete_cancel"),
            ]
        ]
    )
    await callback.message.answer(
        f"Удалить все данные склада {slot}? Восстановить их автоматически не получится.",
        reply_markup=markup,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("warehouse_delete_confirm:"))
async def warehouse_delete_confirm(callback: CallbackQuery, session: AsyncSession) -> None:
    slot = int(callback.data.rsplit(":", 1)[1])
    await SettingRepository(session).clear_warehouse(slot)
    await callback.message.edit_text(f"✅ Склад {slot} удалён.")
    await callback.answer()


@router.callback_query(F.data == "warehouse_delete_cancel")
async def warehouse_delete_cancel(callback: CallbackQuery) -> None:
    await callback.message.edit_text("Удаление склада отменено.")
    await callback.answer()


@router.message(AdminStates.setting_value, F.text)
async def setting_save(message: Message, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    key = data["setting_key"]
    value = message.text.strip()
    if key == "default_transit_days":
        try:
            days = int(value)
        except ValueError:
            await message.answer("Введите целое количество дней, например 12.")
            return
        if not 1 <= days <= 90:
            await message.answer("Срок доставки должен быть от 1 до 90 дней.")
            return
        value = str(days)
    await SettingRepository(session).set(key, value)
    await state.clear()
    await message.answer("✅ Настройка сохранена.", reply_markup=admin_menu_keyboard())


@router.message(F.text == "📢 Рассылка")
async def broadcast_start(message: Message, state: FSMContext) -> None:
    await state.set_state(AdminStates.broadcast_text)
    await message.answer(
        "Введите текст рассылки (поддерживается обычный текст):", reply_markup=cancel_keyboard()
    )


@router.message(AdminStates.broadcast_text, F.text)
async def broadcast_preview(message: Message, state: FSMContext, session: AsyncSession) -> None:
    text = message.text.strip()
    if not text:
        await message.answer("Текст не может быть пустым.")
        return
    recipients = int(
        await session.scalar(
            select(func.count(User.id)).where(
                User.telegram_id.is_not(None),
                User.is_active.is_(True),
                or_(User.blocked_until.is_(None), User.blocked_until <= datetime.now(UTC)),
            )
        )
        or 0
    )
    await state.update_data(broadcast_text=text)
    await state.set_state(AdminStates.broadcast_confirm)
    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Отправить", callback_data="broadcast:send"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="broadcast:cancel"),
            ]
        ]
    )
    await message.answer(
        f"📢 <b>Предпросмотр</b>\n\n{escape(text)}\n\nПолучателей: {recipients}",
        parse_mode="HTML",
        reply_markup=markup,
    )


@router.callback_query(AdminStates.broadcast_confirm, F.data.startswith("broadcast:"))
async def broadcast_send(callback: CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot) -> None:
    action = callback.data.split(":", 1)[1]
    if action == "cancel":
        await state.clear()
        await callback.message.edit_text("Рассылка отменена.")
        await callback.answer()
        return
    data = await state.get_data()
    telegram_ids = list(
        await session.scalars(
            select(User.telegram_id).where(
                User.telegram_id.is_not(None),
                User.is_active.is_(True),
                or_(User.blocked_until.is_(None), User.blocked_until <= datetime.now(UTC)),
            )
        )
    )
    sent = 0
    failed = 0
    for telegram_id in telegram_ids:
        try:
            await bot.send_message(telegram_id, data["broadcast_text"], parse_mode=None)
            sent += 1
        except TelegramAPIError:
            failed += 1
            logger.warning("Broadcast delivery failed: telegram_id=%s", telegram_id)
    await state.clear()
    await callback.message.edit_text(f"✅ Рассылка завершена.\nДоставлено: {sent}\nОшибок: {failed}")
    await callback.answer()
