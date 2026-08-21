from html import escape

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.bot.keyboards.admin import (
    admin_menu_keyboard,
    confirm_keyboard,
    parcel_actions,
    status_keyboard,
)
from app.bot.keyboards.user import cancel_keyboard
from app.bot.states.admin import AdminStates
from app.core.dates import (
    as_local,
    delivery_date_order_is_valid,
    local_date_text,
    local_datetime_text,
    parse_local_date,
)
from app.core.enums import ParcelStatus
from app.db.models import Parcel
from app.db.repositories import ParcelRepository
from app.services.normalization import normalize_tracking_number
from app.services.notification_service import notify_parcel_status
from app.services.parcel_service import ParcelService, apply_delivery_dates

router = Router(name="admin_parcels")


def parcel_text(parcel: Parcel) -> str:
    user = parcel.user
    lines = [
        "📦 <b>Карточка товара</b>",
        "",
        f"Трек: <code>{escape(parcel.tracking_number)}</code>",
        f"Код клиента: <b>{parcel.client_code}</b>",
        f"ФИО: {escape(user.full_name) if user else 'клиент не создан'}",
        f"Telegram: {user.telegram_id if user and user.telegram_id else 'не привязан'}",
        f"Статус: {parcel.status.label}",
        f"Создан: {local_datetime_text(parcel.created_at)}",
        f"Обновлён: {local_datetime_text(parcel.updated_at)}",
    ]
    for label, value in [
        ("Выехал", parcel.sent_at),
        ("Примерно приедет", parcel.expected_at),
        ("Прибыл", parcel.arrived_at),
        ("Готов к выдаче", parcel.ready_at),
        ("Выдан", parcel.delivered_at),
    ]:
        if value:
            lines.append(f"{label}: {local_date_text(value)}")
    return "\n".join(lines)


@router.message(F.text.in_({"🔎 Найти трек", "🔄 Изменить статус"}))
async def parcel_search_start(message: Message, state: FSMContext) -> None:
    await state.set_state(AdminStates.parcel_search)
    await state.update_data(change_immediately=message.text == "🔄 Изменить статус")
    await message.answer("Введите трек-код:", reply_markup=cancel_keyboard())


@router.message(AdminStates.parcel_search, F.text)
async def parcel_search_result(message: Message, state: FSMContext, session: AsyncSession) -> None:
    parcel = await ParcelRepository(session).by_tracking(normalize_tracking_number(message.text))
    data = await state.get_data()
    await state.clear()
    if not parcel:
        await message.answer("Товар не найден.", reply_markup=admin_menu_keyboard())
        return
    await message.answer(parcel_text(parcel), parse_mode="HTML", reply_markup=parcel_actions(parcel.id))
    if data.get("change_immediately"):
        await message.answer("Выберите новый статус:", reply_markup=status_keyboard(f"pstatus:{parcel.id}"))


@router.message(F.text == "📦 Товары")
async def recent_parcels(message: Message, session: AsyncSession) -> None:
    rows = await session.scalars(
        select(Parcel).options(selectinload(Parcel.user)).order_by(Parcel.updated_at.desc()).limit(15)
    )
    parcels = list(rows)
    if not parcels:
        await message.answer("Товаров пока нет.")
        return
    text = ["📦 <b>Последние товары</b>"]
    for parcel in parcels:
        text.append(f"\n<code>{parcel.tracking_number}</code> · {parcel.client_code}\n{parcel.status.label}")
    await message.answer("\n".join(text), parse_mode="HTML")


@router.callback_query(F.data.startswith("parcel_status:"))
async def parcel_status_start(callback: CallbackQuery) -> None:
    parcel_id = int(callback.data.rsplit(":", 1)[1])
    await callback.message.answer(
        "Выберите новый статус:", reply_markup=status_keyboard(f"pstatus:{parcel_id}")
    )
    await callback.answer()


@router.callback_query(F.data.startswith("pstatus:"))
async def parcel_status_apply(callback: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    _, parcel_id, status_value = callback.data.split(":", 2)
    parcel = await session.scalar(
        select(Parcel).options(selectinload(Parcel.user)).where(Parcel.id == int(parcel_id))
    )
    if not parcel:
        await callback.answer("Товар не найден", show_alert=True)
        return
    new_status = ParcelStatus(status_value)
    changed = await ParcelService(session).change_status(parcel, new_status, callback.from_user.id)
    if not changed:
        await callback.answer("Статус уже установлен", show_alert=True)
        return
    await session.commit()
    notified = await notify_parcel_status(bot, parcel, status_changed=True)
    await callback.message.answer(
        f"✅ Статус изменён: {new_status.label}" + ("\nКлиент уведомлён." if notified else "")
    )
    await callback.answer()


@router.callback_query(F.data.startswith("parcel_sent:"))
async def sent_date_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminStates.parcel_sent_at)
    await state.update_data(parcel_id=int(callback.data.rsplit(":", 1)[1]))
    await callback.message.answer(
        "Введите новую дату выезда в формате ДД.ММ.ГГГГ:",
        reply_markup=cancel_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("parcel_expected:"))
async def expected_date_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminStates.parcel_expected_at)
    await state.update_data(parcel_id=int(callback.data.rsplit(":", 1)[1]))
    await callback.message.answer(
        "Введите новую примерную дату прибытия в формате ДД.ММ.ГГГГ:",
        reply_markup=cancel_keyboard(),
    )
    await callback.answer()


async def _save_date(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
    field: str,
) -> None:
    try:
        value = parse_local_date(message.text)
    except ValueError:
        await message.answer("Невозможная или некорректная дата. Используйте формат ДД.ММ.ГГГГ.")
        return
    data = await state.get_data()
    parcel = await session.scalar(
        select(Parcel).options(selectinload(Parcel.user)).where(Parcel.id == data["parcel_id"])
    )
    if not parcel:
        await state.clear()
        await message.answer("Товар не найден.")
        return
    value_date = as_local(value).date()
    if field == "expected_at" and not delivery_date_order_is_valid(parcel.sent_at, value):
        await message.answer("Дата прибытия не может быть раньше даты выезда.")
        return
    if field == "sent_at" and not delivery_date_order_is_valid(value, parcel.expected_at):
        await message.answer("Дата выезда не может быть позже ожидаемой даты прибытия.")
        return
    current_value = getattr(parcel, field)
    if current_value and as_local(current_value).date() == value_date:
        await state.clear()
        await message.answer("Дата не изменилась.", reply_markup=admin_menu_keyboard())
        return
    if field == "expected_at":
        apply_delivery_dates(parcel, expected_at=value)
    else:
        setattr(parcel, field, value)
    await session.commit()
    notified = await notify_parcel_status(
        bot,
        parcel,
        dates_changed=True,
        sent_at_changed=field == "sent_at",
        expected_at_changed=field == "expected_at",
    )
    await state.clear()
    result = "✅ Дата сохранена."
    if notified:
        result += "\nКлиент уведомлён."
    await message.answer(result, reply_markup=admin_menu_keyboard())


@router.message(AdminStates.parcel_sent_at, F.text)
async def save_sent_date(message: Message, state: FSMContext, session: AsyncSession, bot: Bot) -> None:
    await _save_date(message, state, session, bot, "sent_at")


@router.message(AdminStates.parcel_expected_at, F.text)
async def save_expected_date(message: Message, state: FSMContext, session: AsyncSession, bot: Bot) -> None:
    await _save_date(message, state, session, bot, "expected_at")


@router.callback_query(F.data.startswith("parcel_delete:"))
async def delete_start(callback: CallbackQuery) -> None:
    parcel_id = int(callback.data.rsplit(":", 1)[1])
    await callback.message.answer(
        "Удалить товар и его историю? Это действие необратимо.",
        reply_markup=confirm_keyboard("delete_parcel", parcel_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm:"))
async def confirm_action(callback: CallbackQuery, session: AsyncSession) -> None:
    _, action, object_id = callback.data.split(":", 2)
    if action == "cancel":
        await callback.message.edit_text("Действие отменено.")
        await callback.answer()
        return
    if action == "delete_parcel":
        parcel = await session.get(Parcel, int(object_id))
        if not parcel:
            await callback.answer("Товар не найден", show_alert=True)
            return
        tracking = parcel.tracking_number
        await session.delete(parcel)
        await session.flush()
        await callback.message.edit_text(f"✅ Товар {tracking} удалён.")
    await callback.answer()
