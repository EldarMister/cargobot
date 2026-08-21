from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from app.core.enums import IMPORT_BATCH_STATUSES, ParcelStatus


def admin_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📥 Загрузить Excel"), KeyboardButton(text="📦 Товары")],
            [KeyboardButton(text="👥 Клиенты"), KeyboardButton(text="🔎 Найти трек")],
            [KeyboardButton(text="🔎 Найти клиента"), KeyboardButton(text="🔄 Изменить статус")],
            [KeyboardButton(text="➕ Добавить клиента"), KeyboardButton(text="✏️ Редактировать клиента")],
            [KeyboardButton(text="🔗 Отвязать Telegram")],
            [KeyboardButton(text="📢 Рассылка"), KeyboardButton(text="📊 Статистика")],
            [KeyboardButton(text="⚙️ Настройки"), KeyboardButton(text="↩️ Меню клиента")],
        ],
        resize_keyboard=True,
    )


def status_keyboard(
    prefix: str = "status",
    statuses: tuple[ParcelStatus, ...] | None = None,
) -> InlineKeyboardMarkup:
    statuses = statuses or tuple(ParcelStatus)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=status.label, callback_data=f"{prefix}:{status.value}")]
            for status in statuses
        ]
    )


def import_status_keyboard() -> InlineKeyboardMarkup:
    keyboard = status_keyboard("import_status", IMPORT_BATCH_STATUSES)
    keyboard.inline_keyboard.append(
        [InlineKeyboardButton(text="❌ Отмена", callback_data="import_flow:cancel")]
    )
    return keyboard


def departure_date_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📅 Сегодня")],
            [KeyboardButton(text="❌ Отмена")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def expected_date_keyboard(default_days: int) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=f"⏳ Автоматически: {default_days} дней")],
            [KeyboardButton(text="❌ Отмена")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def import_confirmation_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Импортировать", callback_data="import_confirm:yes"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="import_confirm:cancel"),
            ]
        ]
    )


def parcel_actions(parcel_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Изменить статус", callback_data=f"parcel_status:{parcel_id}")],
            [
                InlineKeyboardButton(
                    text="📅 Изменить дату выезда", callback_data=f"parcel_sent:{parcel_id}"
                ),
                InlineKeyboardButton(
                    text="🗓 Изменить дату прибытия", callback_data=f"parcel_expected:{parcel_id}"
                ),
            ],
            [InlineKeyboardButton(text="❌ Удалить товар", callback_data=f"parcel_delete:{parcel_id}")],
        ]
    )


def confirm_keyboard(action: str, object_id: int = 0) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm:{action}:{object_id}"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="confirm:cancel:0"),
            ]
        ]
    )


def settings_keyboard() -> InlineKeyboardMarkup:
    labels = {
        "company_name": "Название компании",
        "default_transit_days": "Стандартный срок доставки",
        "warehouse_receiver": "Получатель склада",
        "warehouse_phone": "Телефон склада",
        "warehouse_address": "Адрес склада",
        "warehouse_name": "Название склада",
        "support_username": "Контакт поддержки",
        "contact_whatsapp": "WhatsApp",
        "local_warehouse_address": "Адрес местного склада",
        "work_schedule": "График работы",
    }
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=label, callback_data=f"setting:{key}")]
            for key, label in labels.items()
        ]
    )
