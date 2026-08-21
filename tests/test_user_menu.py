from app.bot.keyboards.user import language_keyboard, main_menu_keyboard, start_keyboard


def _button_texts(keyboard):
    return [[button.text for button in row] for row in keyboard.keyboard]


def test_reference_registration_actions_are_available():
    assert _button_texts(start_keyboard()) == [
        ["🔗 Привязать существующий код"],
        ["🆕 Регистрация нового клиента"],
    ]


def test_user_language_keyboard_only_contains_russian_and_english():
    keyboard = language_keyboard()

    assert [button.callback_data for row in keyboard.inline_keyboard for button in row] == [
        "language:start:ru",
        "language:start:en",
    ]


def test_reference_client_menu_has_all_actions_and_language_switcher():
    assert _button_texts(main_menu_keyboard()) == [
        ["📦 Мои товары", "🔍 Поиск по трек-коду"],
        ["📍 Контакты/Адрес склада", "🕘 График работы"],
        ["🏠 Адрес в Китае", "👤 Профиль"],
        ["🗄 Выданные товары", "❓ Помощь"],
        ["🌐 Язык"],
    ]


def test_client_menu_is_available_in_english():
    assert _button_texts(main_menu_keyboard("en"))[0] == ["📦 My shipments", "🔍 Track a shipment"]
