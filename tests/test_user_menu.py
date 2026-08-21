from app.bot.keyboards.user import main_menu_keyboard, start_keyboard


def _button_texts(keyboard):
    return [[button.text for button in row] for row in keyboard.keyboard]


def test_reference_registration_actions_are_available():
    assert _button_texts(start_keyboard()) == [
        ["🔗 Привязать существующий код"],
        ["🆕 Регистрация нового клиента"],
    ]


def test_reference_client_menu_has_all_actions_and_language_switcher():
    assert _button_texts(main_menu_keyboard()) == [
        ["📦 Мои товары", "🔍 Поиск по трек-коду"],
        ["📍 Контакты/Адрес склада", "🕘 График работы"],
        ["🏠 Адрес в Китае", "👤 Профиль"],
        ["🗄 Выданные товары", "❓ Помощь"],
        ["🌐 Язык"],
    ]


def test_client_menu_is_available_in_english_and_chinese():
    assert _button_texts(main_menu_keyboard("en"))[0] == ["📦 My shipments", "🔍 Track a shipment"]
    assert _button_texts(main_menu_keyboard("zh"))[0] == ["📦 我的货物", "🔍 查询物流"]
