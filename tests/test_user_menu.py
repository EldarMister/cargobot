from app.bot.keyboards.user import main_menu_keyboard, start_keyboard


def _button_texts(keyboard):
    return [[button.text for button in row] for row in keyboard.keyboard]


def test_reference_registration_actions_are_available():
    assert _button_texts(start_keyboard()) == [
        ["🔗 Привязать существующий код"],
        ["🆕 Регистрация нового клиента"],
    ]


def test_reference_client_menu_has_all_eight_actions():
    assert _button_texts(main_menu_keyboard()) == [
        ["📦 Мои товары", "🔍 Поиск по трек-коду"],
        ["📍 Контакты/Адрес склада", "🕘 График работы"],
        ["🏠 Адрес в Китае", "👤 Профиль"],
        ["🗄 Выданные товары", "❓ Помощь"],
    ]
