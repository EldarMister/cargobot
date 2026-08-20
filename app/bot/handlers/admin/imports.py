import asyncio
import logging
import tempfile
from datetime import datetime
from html import escape
from pathlib import Path

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.bot.keyboards.admin import (
    admin_menu_keyboard,
    import_confirmation_keyboard,
    import_status_keyboard,
    optional_date_keyboard,
)
from app.bot.keyboards.user import cancel_keyboard
from app.bot.states.admin import AdminStates
from app.core.dates import delivery_date_order_is_valid, local_date_text, parse_local_date
from app.core.enums import ParcelStatus
from app.db.models import Import
from app.services.excel_importer import ExcelImporter
from app.services.import_service import ImportService
from app.services.notification_service import send_notification

logger = logging.getLogger(__name__)
router = Router(name="admin_imports")


def _stored_date(data: dict, key: str) -> datetime | None:
    value = data.get(key)
    return datetime.fromisoformat(value) if value else None


async def _request_excel(message: Message) -> None:
    await message.answer(
        "📎 Теперь отправьте Excel-файл с товарами (.xls или .xlsx, до 20 МБ).",
        reply_markup=cancel_keyboard(),
    )


@router.message(F.text == "📥 Загрузить Excel")
async def import_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(AdminStates.import_status)
    await message.answer("Выберите статус товаров:", reply_markup=import_status_keyboard())


@router.callback_query(F.data == "import_flow:cancel")
async def import_flow_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("Импорт отменён. Данные не изменены.")
    await callback.message.answer("Панель администратора", reply_markup=admin_menu_keyboard())
    await callback.answer()


@router.callback_query(AdminStates.import_status, F.data.startswith("import_status:"))
async def import_status(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        status = ParcelStatus(callback.data.split(":", 1)[1])
    except ValueError:
        await callback.answer("Неизвестный статус", show_alert=True)
        return
    await state.update_data(selected_status=status.value, sent_at=None, expected_at=None)
    await callback.message.edit_text(f"Выбран статус: {status.label}")
    if status == ParcelStatus.IN_TRANSIT:
        await state.set_state(AdminStates.import_departure_date)
        await callback.message.answer(
            "📅 Укажите дату выезда в формате ДД.ММ.ГГГГ:",
            reply_markup=optional_date_keyboard(),
        )
    else:
        await state.set_state(AdminStates.import_file)
        await _request_excel(callback.message)
    await callback.answer()


@router.message(AdminStates.import_departure_date, F.text)
async def import_departure_date(message: Message, state: FSMContext) -> None:
    if message.text.casefold() == "пропустить":
        sent_at = None
    else:
        try:
            sent_at = parse_local_date(message.text)
        except ValueError:
            await message.answer("❌ Невозможная или некорректная дата. Используйте формат ДД.ММ.ГГГГ.")
            return
    await state.update_data(sent_at=sent_at.isoformat() if sent_at else None)
    await state.set_state(AdminStates.import_expected_at)
    await message.answer(
        "🗓 Укажите примерную дату прибытия в формате ДД.ММ.ГГГГ:",
        reply_markup=optional_date_keyboard(),
    )


@router.message(AdminStates.import_expected_at, F.text)
async def import_expected_date(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    sent_at = _stored_date(data, "sent_at")
    if message.text.casefold() == "пропустить":
        expected_at = None
    else:
        try:
            expected_at = parse_local_date(message.text)
        except ValueError:
            await message.answer("❌ Невозможная или некорректная дата. Используйте формат ДД.ММ.ГГГГ.")
            return
        if not delivery_date_order_is_valid(sent_at, expected_at):
            await message.answer("❌ Дата прибытия не может быть раньше даты выезда.")
            return
    await state.update_data(expected_at=expected_at.isoformat() if expected_at else None)
    await state.set_state(AdminStates.import_file)
    await _request_excel(message)


@router.message(AdminStates.import_file, F.document)
async def import_file_preview(message: Message, state: FSMContext) -> None:
    document = message.document
    filename = Path(document.file_name or "import").name
    suffix = Path(filename).suffix.lower()
    if suffix not in {".xls", ".xlsx"}:
        await message.answer("❌ Поддерживаются только файлы .xls и .xlsx.")
        return
    if document.file_size and document.file_size > 20 * 1024 * 1024:
        await message.answer("❌ Файл больше 20 МБ.")
        return
    await state.update_data(file_id=document.file_id, filename=filename, suffix=suffix)
    data = await state.get_data()
    status = ParcelStatus(data["selected_status"])
    sent_at = _stored_date(data, "sent_at")
    expected_at = _stored_date(data, "expected_at")
    lines = ["<b>Подтвердите импорт:</b>", "", f"📊 Статус: {status.label}"]
    if sent_at:
        lines.append(f"📅 Выехал: {local_date_text(sent_at)}")
    if expected_at:
        lines.append(f"🗓 Приедет примерно: {local_date_text(expected_at)}")
    lines.extend([f"📄 Файл: <code>{escape(filename)}</code>", "", "Продолжить?"])
    await state.set_state(AdminStates.import_confirmation)
    await message.answer(
        "\n".join(lines),
        parse_mode="HTML",
        reply_markup=import_confirmation_keyboard(),
    )


@router.message(AdminStates.import_file)
async def import_file_invalid(message: Message) -> None:
    await message.answer("Отправьте Excel-файл как документ (.xls или .xlsx).")


@router.callback_query(AdminStates.import_confirmation, F.data == "import_confirm:cancel")
async def import_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("Импорт отменён. Данные не изменены.")
    await callback.message.answer("Панель администратора", reply_markup=admin_menu_keyboard())
    await callback.answer()


@router.callback_query(AdminStates.import_confirmation, F.data == "import_confirm:yes")
async def import_confirm(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
) -> None:
    data = await state.get_data()
    await state.clear()
    filename = data["filename"]
    suffix = data["suffix"]
    selected_status = ParcelStatus(data["selected_status"])
    sent_at = _stored_date(data, "sent_at")
    expected_at = _stored_date(data, "expected_at")
    await callback.message.edit_text("⏳ Обрабатываю все листы файла…")
    await callback.answer("Импорт начат")

    try:
        with tempfile.TemporaryDirectory(prefix="cargo_import_") as temp_dir:
            path = Path(temp_dir) / f"upload{suffix}"
            await bot.download(data["file_id"], destination=path)
            parsed = await asyncio.to_thread(ExcelImporter().parse, path)
        outcome = await ImportService(session).process(
            parsed=parsed,
            filename=filename,
            selected_status=selected_status,
            uploaded_by=callback.from_user.id,
            sent_at=sent_at,
            expected_at=expected_at,
        )
        await session.commit()
    except Exception as exc:
        logger.exception("Excel import failed: file=%s admin=%s", filename, callback.from_user.id)
        await session.rollback()
        await callback.message.answer(
            f"❌ Не удалось обработать файл. Проверьте формат Excel.\nПричина: {type(exc).__name__}",
            reply_markup=admin_menu_keyboard(),
        )
        return

    delivered = 0
    for event in outcome.notifications:
        delivered += int(await send_notification(bot, event))
    record = outcome.import_record
    reasons_markup = None
    if record.skipped_rows:
        reasons_markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="⚠️ Причины пропуска",
                        callback_data=f"import_errors:{record.id}",
                    )
                ]
            ]
        )
    lines = [
        "✅ <b>Импорт завершён</b>",
        "",
        f"📄 Файл: <code>{escape(filename)}</code>",
        f"📊 Статус: {selected_status.label}",
    ]
    if sent_at:
        lines.append(f"📅 Дата выезда: {local_date_text(sent_at)}")
    if expected_at:
        lines.append(f"🗓 Примерное прибытие: {local_date_text(expected_at)}")
    lines.extend(
        [
            "",
            f"Всего найдено: {record.valid_rows}",
            f"➕ Новых товаров: {record.created_rows}",
            f"🔄 Обновлено/проверено: {record.updated_rows}",
            f"⚠️ Пропущено: {record.skipped_rows}",
            f"📨 Отправлено уведомлений: {delivered}",
        ]
    )
    await callback.message.answer(
        "\n".join(lines),
        parse_mode="HTML",
        reply_markup=reasons_markup,
    )
    await callback.message.answer("Панель администратора", reply_markup=admin_menu_keyboard())
    logger.info("Import completed: id=%s file=%s", record.id, filename)


@router.callback_query(F.data.startswith("import_errors:"))
async def import_errors(callback: CallbackQuery, session: AsyncSession) -> None:
    import_id = int(callback.data.split(":", 1)[1])
    record = await session.scalar(
        select(Import).options(selectinload(Import.rows)).where(Import.id == import_id)
    )
    if not record:
        await callback.answer("Импорт не найден", show_alert=True)
        return
    errors = [row for row in record.rows if row.error]
    lines = ["⚠️ <b>Причины пропуска</b>"]
    for row in errors[:40]:
        lines.append(f"{escape(row.sheet_name)}, строка {row.row_number}: {escape(row.error or '')}")
    if len(errors) > 40:
        lines.append(f"…и ещё {len(errors) - 40}")
    await callback.message.answer("\n".join(lines), parse_mode="HTML")
    await callback.answer()
