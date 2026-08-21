from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def start_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔗 Привязать существующий код")],
            [KeyboardButton(text="🆕 Регистрация нового клиента")],
        ],
        resize_keyboard=True,
    )


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📦 Мои товары"), KeyboardButton(text="🔍 Поиск по трек-коду")],
            [KeyboardButton(text="📍 Контакты/Адрес склада"), KeyboardButton(text="🕘 График работы")],
            [KeyboardButton(text="🏠 Адрес в Китае"), KeyboardButton(text="👤 Профиль")],
            [KeyboardButton(text="🗄 Выданные товары"), KeyboardButton(text="❓ Помощь")],
        ],
        resize_keyboard=True,
    )


def cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True, one_time_keyboard=True
    )
