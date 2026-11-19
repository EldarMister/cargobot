from html import escape
from secrets import token_urlsafe

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.admin import admin_menu_keyboard
from app.bot.keyboards.user import cancel_keyboard
from app.bot.states.admin import AdminStates
from app.core.dates import local_date_text
from app.db.models import User
from app.db.repositories import UserRepository
from app.services.client_message_service import (
    ClientMessageError,
    client_message_unavailable_reason,
    send_client_message,
)
from app.services.normalization import (
    is_valid_client_code,
    normalize_client_code,
    normalize_phone,
)
from app.services.user_service import UserService

router = Router(name="admin_users")


def user_actions(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✉️ Написать клиенту", callback_data=f"user_message:{user_id}")],
            [
                InlineKeyboardButton(text="✏️ ФИО", callback_data=f"user_edit:{user_id}:full_name"),
                InlineKeyboardButton(text="✏️ Телефон", callback_data=f"user_edit:{user_id}:phone"),
            ],
            [InlineKeyboardButton(text="✏️ Город", callback_data=f"user_edit:{user_id}:city")],
            [InlineKeyboardButton(text="🔗 Отвязать Telegram", callback_data=f"user_unlink:{user_id}")],
        ]
    )


async def user_text(user: User, repository: UserRepository) -> str:
    total, transit, delivered = await repository.parcel_counts(user.id)
    return (
        "👤 <b>Клиент</b>\n\n"
        f"ФИО: {escape(user.full_name)}\n"
        f"Код: <b>{user.client_code}</b>\n"
        f"Телефон: {escape(user.phone)}\n"
        f"Город: {escape(user.city) if user.city else 'не указан'}\n"
        f"Telegram: {user.telegram_id or 'не привязан'}\n"
        f"Всего товаров: {total}\n"
        f"В пути: {transit}\n"
        f"Получено: {delivered}\n"
        f"Создан: {local_date_text(user.created_at)}"
    )


@router.message(F.text.in_({"🔎 Найти клиента", "✏️ Редактировать клиента", "🔗 Отвязать Telegram"}))
async def search_start(message: Message, state: FSMContext) -> None:
    await state.set_state(AdminStates.user_search)
    await state.update_data(
        unlink_requested=message.text == "🔗 Отвязать Telegram",
        edit_requested=message.text == "✏️ Редактировать клиента",
    )
    await message.answer(
        "Введите H-код, трек-код груза, ФИО, телефон или Telegram ID:",
        reply_markup=cancel_keyboard(),
    )


@router.message(AdminStates.user_search, F.text)
async def search_result(message: Message, state: FSMContext, session: AsyncSession) -> None:
    repository = UserRepository(session)
    users = await repository.search(message.text.strip())
    data = await state.get_data()
    await state.clear()
    if not users:
        await message.answer("Клиенты не найдены.", reply_markup=admin_menu_keyboard())
        return
    for user in users[:10]:
        await message.answer(
            await user_text(user, repository),
            parse_mode="HTML",
            reply_markup=user_actions(user.id),
        )
    if data.get("unlink_requested"):
        await message.answer("Нажмите «Отвязать Telegram» в карточке нужного клиента.")
    elif data.get("edit_requested"):
        await message.answer("Нажмите кнопку редактирования нужного поля в карточке клиента.")


@router.message(F.text == "👥 Клиенты")
async def recent_users(message: Message, session: AsyncSession) -> None:
    users = list(await session.scalars(select(User).order_by(User.created_at.desc()).limit(15)))
    if not users:
        await message.answer("Клиентов пока нет.")
        return
    lines = ["👥 <b>Последние клиенты</b>"]
    for user in users:
        marker = "📲" if user.telegram_id else "▫️"
        lines.append(f"{marker} <b>{user.client_code}</b> · {escape(user.full_name)}")
    await message.answer("\n".join(lines), parse_mode="HTML")


@router.callback_query(F.data.startswith("user_message:"))
async def client_message_start(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    user = await session.get(User, int(callback.data.split(":", 1)[1]))
    reason = client_message_unavailable_reason(user) if user else "Клиент не найден"
    if reason:
        await callback.answer(reason, show_alert=True)
        return
    await state.set_state(AdminStates.client_message_text)
    await state.update_data(message_client_id=user.id, message_telegram_id=user.telegram_id)
    await callback.message.answer(
        f"Сообщение для {escape(user.full_name)} · <b>{user.client_code}</b>.\n"
        "Введите текст (до 4096 символов). Клиент получит его в чате с ботом.\n\n"
        f"Например: Здравствуйте! Ваш груз по коду {user.client_code} прибыл. "
        "Пожалуйста, заберите его на нашем складе.",
        reply_markup=cancel_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AdminStates.client_message_text, F.text)
async def client_message_preview(message: Message, state: FSMContext, session: AsyncSession) -> None:
    text = message.text.strip()
    if not text or len(text.encode("utf-16-le")) // 2 > 4096:
        await message.answer("Введите сообщение длиной от 1 до 4096 символов.")
        return
    data = await state.get_data()
    user = await session.get(User, data["message_client_id"])
    if not user:
        await state.clear()
        await message.answer("Клиент не найден.", reply_markup=admin_menu_keyboard())
        return
    token = token_urlsafe(8)
    await state.update_data(client_message=text, client_message_token=token)
    await state.set_state(AdminStates.client_message_confirm)
    # Separate recipient and text so the preview itself stays within Telegram's limit.
    await message.answer(text, parse_mode=None)
    await message.answer(
        f"Отправить этот текст клиенту {escape(user.full_name)} · <b>{user.client_code}</b>?",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="✉️ Отправить", callback_data=f"client_message:send:{token}"),
            InlineKeyboardButton(text="Отмена", callback_data=f"client_message:cancel:{token}"),
        ]]),
    )


@router.callback_query(AdminStates.client_message_confirm, F.data.startswith("client_message:"))
async def client_message_confirm(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    _, action, token = callback.data.split(":", 2)
    if token != data.get("client_message_token") or action not in {"send", "cancel"}:
        await callback.answer("Это подтверждение устарело. Используйте последнее сообщение.", show_alert=True)
        return
    await state.clear()
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    if action == "cancel":
        await callback.message.answer("Отправка отменена.", reply_markup=admin_menu_keyboard())
        return
    user = await session.get(User, data["message_client_id"])
    if not user:
        await callback.message.answer("Клиент не найден.", reply_markup=admin_menu_keyboard())
        return
    try:
        await send_client_message(
            callback.bot, user, data["client_message"],
            expected_telegram_id=data["message_telegram_id"], admin_id=callback.from_user.id,
        )
    except ClientMessageError as exc:
        await callback.message.answer(str(exc), reply_markup=admin_menu_keyboard())
        return
    await callback.message.answer("✅ Сообщение отправлено клиенту.", reply_markup=admin_menu_keyboard())


@router.callback_query(F.data.startswith("user_unlink:"))
async def unlink_user(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await session.get(User, int(callback.data.split(":", 1)[1]))
    if not user:
        await callback.answer("Клиент не найден", show_alert=True)
        return
    if user.telegram_id is None:
        await callback.answer("Telegram уже не привязан", show_alert=True)
        return
    await UserService(session).unlink(user)
    await callback.message.answer(f"✅ Telegram отвязан от {user.client_code}.")
    await callback.answer()


@router.callback_query(F.data.startswith("user_edit:"))
async def edit_user_start(callback: CallbackQuery, state: FSMContext) -> None:
    _, user_id, field = callback.data.split(":", 2)
    if field not in {"full_name", "phone", "city"}:
        await callback.answer("Поле недоступно", show_alert=True)
        return
    await state.set_state(AdminStates.user_edit_value)
    await state.update_data(user_id=int(user_id), field=field)
    labels = {"full_name": "новое ФИО", "phone": "новый телефон", "city": "новый город"}
    label = labels[field]
    await callback.message.answer(f"Введите {label}:", reply_markup=cancel_keyboard())
    await callback.answer()


@router.message(AdminStates.user_edit_value, F.text)
async def edit_user_value(message: Message, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    user = await session.get(User, data["user_id"])
    if not user:
        await state.clear()
        await message.answer("Клиент не найден.")
        return
    value = " ".join(message.text.split())
    if data["field"] == "phone":
        value = normalize_phone(value)
        if len(value) < 8:
            await message.answer("Некорректный телефон.")
            return
    elif data["field"] == "city":
        value = None if value in {"-", "—"} else value
    elif len(value) < 3:
        await message.answer("ФИО слишком короткое.")
        return
    setattr(user, data["field"], value)
    await state.clear()
    await message.answer("✅ Данные клиента обновлены.", reply_markup=admin_menu_keyboard())


@router.message(F.text == "➕ Добавить клиента")
async def add_user_start(message: Message, state: FSMContext) -> None:
    await state.set_state(AdminStates.user_add_name)
    await message.answer("Введите ФИО клиента:", reply_markup=cancel_keyboard())


@router.message(AdminStates.user_add_name, F.text)
async def add_user_name(message: Message, state: FSMContext) -> None:
    name = " ".join(message.text.split())
    if len(name) < 3:
        await message.answer("ФИО слишком короткое.")
        return
    await state.update_data(full_name=name)
    await state.set_state(AdminStates.user_add_phone)
    await message.answer("Введите номер телефона:")


@router.message(AdminStates.user_add_phone, F.text)
async def add_user_phone(message: Message, state: FSMContext) -> None:
    phone = normalize_phone(message.text)
    if len(phone) < 8:
        await message.answer("Некорректный телефон.")
        return
    await state.update_data(phone=phone)
    await state.set_state(AdminStates.user_add_code)
    await message.answer("Введите H-код или слово «Авто» для назначения следующего свободного:")


@router.message(AdminStates.user_add_code, F.text)
async def add_user_code(message: Message, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    repository = UserRepository(session)
    if message.text.strip().casefold() == "авто":
        code = f"H-{await repository.next_client_number()}"
    elif is_valid_client_code(message.text):
        code = normalize_client_code(message.text)
    else:
        await message.answer("Введите код вида H-801 или слово «Авто».")
        return
    user = User(client_code=code, full_name=data["full_name"], phone=data["phone"])
    session.add(user)
    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
        await message.answer("Этот код уже существует. Введите другой код.")
        return
    await repository.attach_parcels(user)
    await state.clear()
    await message.answer(
        f"✅ Клиент создан. Код: <b>{code}</b>",
        parse_mode="HTML",
        reply_markup=admin_menu_keyboard(),
    )
