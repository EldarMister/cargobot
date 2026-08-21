from __future__ import annotations

from typing import Final

SUPPORTED_LANGUAGES: Final[tuple[str, ...]] = ("ru", "en", "zh")
DEFAULT_LANGUAGE: Final[str] = "ru"
LANGUAGE_NAMES: Final[dict[str, str]] = {
    "ru": "🇷🇺 Русский",
    "en": "🇬🇧 English",
    "zh": "🇨🇳 中文",
}


TRANSLATIONS: Final[dict[str, dict[str, str]]] = {
    "ru": {
        "choose_language": "Выберите язык",
        "language_changed": "✅ Язык изменён на русский.",
        "button.link": "🔗 Привязать существующий код",
        "button.register": "🆕 Регистрация нового клиента",
        "button.parcels": "📦 Мои товары",
        "button.track": "🔍 Поиск по трек-коду",
        "button.contacts": "📍 Контакты/Адрес склада",
        "button.schedule": "🕘 График работы",
        "button.china_address": "🏠 Адрес в Китае",
        "button.profile": "👤 Профиль",
        "button.delivered": "🗄 Выданные товары",
        "button.help": "❓ Помощь",
        "button.language": "🌐 Язык",
        "button.cancel": "❌ Отмена",
        "welcome_back": "👋 С возвращением, {name}!\nВаш код: <b>{code}</b>",
        "access_denied": "⛔ Доступ к боту ограничен. Обратитесь к поддержке.",
        "welcome": (
            "👋 <b>Добро пожаловать в {company}!</b>\n\n"
            "Если у вас уже есть код клиента — привяжите его.\n"
            "Если вы новый клиент — пройдите регистрацию."
        ),
        "cancelled": "Действие отменено.",
        "enter_name": "✍️ Введите ваше ФИО для регистрации:",
        "full_name_required": "Пожалуйста, укажите полное имя.",
        "registration_complete": (
            "🎉 <b>Регистрация завершена!</b>\n\n"
            "Ваш новый код клиента: <b>{code}</b>\n\n{warehouse}"
        ),
        "enter_client_code": "🔑 Введите ваш код клиента, например J-0001",
        "invalid_client_code": "Неверный формат. Введите код вида J-0001.",
        "enter_exact_name": "Введите ФИО точно так же, как оно записано в базе.",
        "code_already_linked": "❌ Этот старый код уже привязан к другому пользователю.",
        "too_many_attempts": "Слишком много неудачных попыток. Начните заново или обратитесь в поддержку.",
        "attempts_left": "{error}\nОсталось попыток: {count}.",
        "profile_linked": (
            "✅ <b>Профиль успешно привязан!</b>\n\n"
            "Ваш код клиента: <b>{code}</b>\n\n{warehouse}"
        ),
        "register_first": "Сначала зарегистрируйтесь через /start.",
        "access_temporarily_denied": "⛔ Доступ к боту временно ограничен. Обратитесь к поддержке.",
        "my_parcels_title": "📦 Мои товары",
        "no_active_parcels": "📦 <b>Мои товары</b>\n\nУ вас пока нет активных товаров.",
        "delivered_title": "🗄 Выданные товары",
        "no_delivered_parcels": (
            "🗄 <b>Выданные товары</b>\n\nВ вашем архиве пока нет товаров.\n"
            "Когда вы получите свои первые товары, они отобразятся здесь."
        ),
        "my_code": "Ваш код клиента: <b>{code}</b>",
        "china_address_title": "🏠 <b>Ваш адрес в Китае:</b>\n\n{warehouse}",
        "profile": (
            "👤 <b>Ваш профиль</b>\n\n🔑 Код клиента: <b>{code}</b>\n"
            "📝 ФИО: {name}{phone}{city}\n📅 Дата регистрации: {created_at}"
        ),
        "profile_phone": "\n📱 Телефон: {phone}",
        "profile_city": "\nГород: {city}",
        "contacts_title": "📍 <b>{company} — Контакты и склад</b>",
        "contact_telegram": "📱 Telegram: {contact}",
        "contact_missing": "💬 Контакт: пока не указан",
        "warehouse_local": "🏢 <b>Адрес склада:</b> {address}",
        "not_specified": "не указан",
        "work_schedule": "🕘 <b>График работы</b>\n\n{schedule}",
        "schedule_missing": "График пока не указан.",
        "help_contact": "напишите нам: {contact}",
        "help_contacts_section": "откройте раздел «Контакты/Адрес склада»",
        "help": (
            "📖 <b>Справка по боту {company}:</b>\n\n"
            "📦 <b>Мои товары</b> — список активных товаров и их статусы\n"
            "🔍 <b>Поиск по трек-коду</b> — статус конкретного товара\n"
            "📍 <b>Контакты/Адрес склада</b> — наш адрес и контакты\n"
            "🕘 <b>График работы</b> — рабочие часы\n"
            "🏠 <b>Адрес в Китае</b> — персональный адрес для отправки\n"
            "👤 <b>Профиль</b> — информация о вашем аккаунте\n"
            "🗄 <b>Выданные товары</b> — архив полученных товаров\n"
            "🌐 <b>Язык</b> — смена языка бота\n\n💡 Если нужна помощь, {contact_line}."
        ),
        "enter_tracking": "Введите трек-код:",
        "tracking_not_found": "Товар с таким трек-кодом не найден среди ваших товаров.",
        "parcel_total": "📊 Всего товаров: {count}",
        "parcel_empty": "У вас пока нет зарегистрированных товаров.",
        "sent_at": "📅 Выехал: {date}",
        "expected_at": "🗓 Примерно приедет: {date}",
        "remaining_days": "⌛ Осталось примерно: {count}",
        "expected_today": "🗓 Ожидается сегодня",
        "expected_passed": "🗓 Ожидаемая дата прибытия уже наступила",
        "warehouse_title": "📦 <b>Адрес склада в Китае</b>",
        "warehouse_receiver": "Получатель: {value}",
        "warehouse_phone": "Телефон: {value}",
        "warehouse_address": "Адрес: {value}",
        "warehouse_name": "Склад: {value}",
        "error.telegram_registered": "Этот Telegram-аккаунт уже зарегистрирован.",
        "error.full_name": "Укажите полное имя.",
        "error.phone": "Не удалось распознать номер телефона.",
        "error.client_code_assignment": "Не удалось назначить свободный код. Повторите попытку.",
        "error.other_code": "К этому Telegram-аккаунту уже привязан другой код.",
        "error.owner_mismatch": "Код или данные владельца не совпадают.",
        "error.code_linked": "Этот код уже привязан. Обратитесь к администратору.",
        "notification.new": "📦 Новый товар зарегистрирован",
        "notification.dates": "🗓 Обновлена информация о доставке",
        "notification.arrived": "🏢 Ваш товар прибыл",
        "notification.ready": "✅ Ваш товар готов к выдаче",
        "notification.updated": "🚚 Обновление по вашему товару",
        "notification.tracking": "📦 Трек-код: <code>{value}</code>",
        "notification.client_code": "🔑 Код клиента: {value}",
        "notification.status": "📊 Статус: {value}",
        "notification.new_expected": "🗓 Новая примерная дата прибытия",
        "notification.expected": "🗓 Примерно приедет",
        "reminder.approaching": "🚚 <b>Ваш товар ожидается со дня на день</b>",
        "reminder.due": "🗓 <b>Расчётный срок доставки наступил</b>",
        "reminder.tracking": "📦 Трек-код: <code>{value}</code>",
        "reminder.client_code": "🔑 Код клиента: {value}",
        "reminder.expected": "🗓 Примерная дата: {date}",
        "reminder.remaining": "⌛ Осталось примерно: {count}",
        "reminder.pending": "Точная дата прибытия уточняется.",
    },
    "en": {
        "choose_language": "Choose your language",
        "language_changed": "✅ Language changed to English.",
        "button.link": "🔗 Link an existing client code",
        "button.register": "🆕 Register as a new client",
        "button.parcels": "📦 My shipments",
        "button.track": "🔍 Track a shipment",
        "button.contacts": "📍 Contacts / Local warehouse",
        "button.schedule": "🕘 Business hours",
        "button.china_address": "🏠 My China address",
        "button.profile": "👤 Profile",
        "button.delivered": "🗄 Collected shipments",
        "button.help": "❓ Help",
        "button.language": "🌐 Language",
        "button.cancel": "❌ Cancel",
        "welcome_back": "👋 Welcome back, {name}!\nYour client code: <b>{code}</b>",
        "access_denied": "⛔ Your access to the bot has been restricted. Please contact support.",
        "welcome": (
            "👋 <b>Welcome to {company}!</b>\n\n"
            "If you already have a client code, link it to your account.\n"
            "If you are a new client, complete the registration."
        ),
        "cancelled": "Action cancelled.",
        "enter_name": "✍️ Enter your full name to register:",
        "full_name_required": "Please enter your full name.",
        "registration_complete": (
            "🎉 <b>Registration complete!</b>\n\n"
            "Your new client code: <b>{code}</b>\n\n{warehouse}"
        ),
        "enter_client_code": "🔑 Enter your client code, for example J-0001",
        "invalid_client_code": "Invalid format. Enter a code such as J-0001.",
        "enter_exact_name": "Enter your full name exactly as it appears in our records.",
        "code_already_linked": "❌ This client code is already linked to another user.",
        "too_many_attempts": "Too many unsuccessful attempts. Start again or contact support.",
        "attempts_left": "{error}\nAttempts remaining: {count}.",
        "profile_linked": (
            "✅ <b>Your profile has been linked successfully!</b>\n\n"
            "Your client code: <b>{code}</b>\n\n{warehouse}"
        ),
        "register_first": "Please register first using /start.",
        "access_temporarily_denied": "⛔ Your access is temporarily restricted. Please contact support.",
        "my_parcels_title": "📦 My shipments",
        "no_active_parcels": "📦 <b>My shipments</b>\n\nYou do not have any active shipments yet.",
        "delivered_title": "🗄 Collected shipments",
        "no_delivered_parcels": (
            "🗄 <b>Collected shipments</b>\n\nYour archive is currently empty.\n"
            "Shipments will appear here after you collect them."
        ),
        "my_code": "Your client code: <b>{code}</b>",
        "china_address_title": "🏠 <b>Your address in China:</b>\n\n{warehouse}",
        "profile": (
            "👤 <b>Your profile</b>\n\n🔑 Client code: <b>{code}</b>\n"
            "📝 Full name: {name}{phone}{city}\n📅 Registration date: {created_at}"
        ),
        "profile_phone": "\n📱 Phone: {phone}",
        "profile_city": "\nCity: {city}",
        "contacts_title": "📍 <b>{company} — Contacts and warehouse</b>",
        "contact_telegram": "📱 Telegram: {contact}",
        "contact_missing": "💬 Contact details have not been provided yet",
        "warehouse_local": "🏢 <b>Warehouse address:</b> {address}",
        "not_specified": "not provided",
        "work_schedule": "🕘 <b>Business hours</b>\n\n{schedule}",
        "schedule_missing": "Business hours have not been provided yet.",
        "help_contact": "contact us at {contact}",
        "help_contacts_section": "open “Contacts / Local warehouse”",
        "help": (
            "📖 <b>{company} bot guide:</b>\n\n"
            "📦 <b>My shipments</b> — view active shipments and their statuses\n"
            "🔍 <b>Track a shipment</b> — check a shipment by tracking number\n"
            "📍 <b>Contacts / Local warehouse</b> — our address and contact details\n"
            "🕘 <b>Business hours</b> — our opening hours\n"
            "🏠 <b>My China address</b> — your personal shipping address\n"
            "👤 <b>Profile</b> — your account information\n"
            "🗄 <b>Collected shipments</b> — archive of received shipments\n"
            "🌐 <b>Language</b> — change the bot language\n\n💡 If you need help, {contact_line}."
        ),
        "enter_tracking": "Enter the tracking number:",
        "tracking_not_found": "No shipment with this tracking number was found in your account.",
        "parcel_total": "📊 Total shipments: {count}",
        "parcel_empty": "You do not have any registered shipments yet.",
        "sent_at": "📅 Dispatched: {date}",
        "expected_at": "🗓 Estimated arrival: {date}",
        "remaining_days": "⌛ Estimated time remaining: {count}",
        "expected_today": "🗓 Expected today",
        "expected_passed": "🗓 The estimated arrival date has passed",
        "warehouse_title": "📦 <b>China warehouse address</b>",
        "warehouse_receiver": "Recipient: {value}",
        "warehouse_phone": "Phone: {value}",
        "warehouse_address": "Address: {value}",
        "warehouse_name": "Warehouse: {value}",
        "error.telegram_registered": "This Telegram account is already registered.",
        "error.full_name": "Please enter your full name.",
        "error.phone": "We could not recognize the phone number.",
        "error.client_code_assignment": "A free client code could not be assigned. Please try again.",
        "error.other_code": "A different client code is already linked to this Telegram account.",
        "error.owner_mismatch": "The client code or account holder details do not match.",
        "error.code_linked": "This client code is already linked. Please contact an administrator.",
        "notification.new": "📦 New shipment registered",
        "notification.dates": "🗓 Delivery information updated",
        "notification.arrived": "🏢 Your shipment has arrived",
        "notification.ready": "✅ Your shipment is ready for collection",
        "notification.updated": "🚚 Shipment update",
        "notification.tracking": "📦 Tracking number: <code>{value}</code>",
        "notification.client_code": "🔑 Client code: {value}",
        "notification.status": "📊 Status: {value}",
        "notification.new_expected": "🗓 New estimated arrival date",
        "notification.expected": "🗓 Estimated arrival",
        "reminder.approaching": "🚚 <b>Your shipment is expected very soon</b>",
        "reminder.due": "🗓 <b>The estimated delivery date has arrived</b>",
        "reminder.tracking": "📦 Tracking number: <code>{value}</code>",
        "reminder.client_code": "🔑 Client code: {value}",
        "reminder.expected": "🗓 Estimated date: {date}",
        "reminder.remaining": "⌛ Estimated time remaining: {count}",
        "reminder.pending": "The exact arrival date is being confirmed.",
    },
    "zh": {
        "choose_language": "请选择语言",
        "language_changed": "✅ 语言已切换为中文。",
        "button.link": "🔗 绑定已有客户编号",
        "button.register": "🆕 新客户注册",
        "button.parcels": "📦 我的货物",
        "button.track": "🔍 查询物流",
        "button.contacts": "📍 联系方式 / 当地仓库",
        "button.schedule": "🕘 营业时间",
        "button.china_address": "🏠 我的中国收货地址",
        "button.profile": "👤 个人资料",
        "button.delivered": "🗄 已领取货物",
        "button.help": "❓ 帮助",
        "button.language": "🌐 语言",
        "button.cancel": "❌ 取消",
        "welcome_back": "👋 欢迎回来，{name}！\n您的客户编号：<b>{code}</b>",
        "access_denied": "⛔ 您的机器人使用权限已受限，请联系客户服务。",
        "welcome": (
            "👋 <b>欢迎使用 {company}！</b>\n\n"
            "如果您已有客户编号，请将其绑定到您的账户。\n"
            "如果您是新客户，请先完成注册。"
        ),
        "cancelled": "操作已取消。",
        "enter_name": "✍️ 请输入您的姓名以完成注册：",
        "full_name_required": "请输入完整姓名。",
        "registration_complete": (
            "🎉 <b>注册成功！</b>\n\n您的新客户编号：<b>{code}</b>\n\n{warehouse}"
        ),
        "enter_client_code": "🔑 请输入客户编号，例如 J-0001",
        "invalid_client_code": "编号格式不正确，请输入类似 J-0001 的编号。",
        "enter_exact_name": "请输入与系统记录完全一致的姓名。",
        "code_already_linked": "❌ 此客户编号已绑定到其他用户。",
        "too_many_attempts": "尝试次数过多，请重新开始或联系客户服务。",
        "attempts_left": "{error}\n剩余尝试次数：{count}。",
        "profile_linked": (
            "✅ <b>账户绑定成功！</b>\n\n您的客户编号：<b>{code}</b>\n\n{warehouse}"
        ),
        "register_first": "请先使用 /start 完成注册。",
        "access_temporarily_denied": "⛔ 您的使用权限暂时受限，请联系客户服务。",
        "my_parcels_title": "📦 我的货物",
        "no_active_parcels": "📦 <b>我的货物</b>\n\n您目前没有运输中的货物。",
        "delivered_title": "🗄 已领取货物",
        "no_delivered_parcels": "🗄 <b>已领取货物</b>\n\n当前暂无记录。\n领取货物后，记录会显示在这里。",
        "my_code": "您的客户编号：<b>{code}</b>",
        "china_address_title": "🏠 <b>您的中国收货地址：</b>\n\n{warehouse}",
        "profile": (
            "👤 <b>个人资料</b>\n\n🔑 客户编号：<b>{code}</b>\n"
            "📝 姓名：{name}{phone}{city}\n📅 注册日期：{created_at}"
        ),
        "profile_phone": "\n📱 电话：{phone}",
        "profile_city": "\n城市：{city}",
        "contacts_title": "📍 <b>{company} — 联系方式与仓库</b>",
        "contact_telegram": "📱 Telegram：{contact}",
        "contact_missing": "💬 暂未提供联系方式",
        "warehouse_local": "🏢 <b>仓库地址：</b>{address}",
        "not_specified": "暂未提供",
        "work_schedule": "🕘 <b>营业时间</b>\n\n{schedule}",
        "schedule_missing": "暂未提供营业时间。",
        "help_contact": "请通过 {contact} 联系我们",
        "help_contacts_section": "请打开“联系方式 / 当地仓库”",
        "help": (
            "📖 <b>{company} 机器人使用指南：</b>\n\n"
            "📦 <b>我的货物</b> — 查看运输中的货物及其状态\n"
            "🔍 <b>查询物流</b> — 按运单号查询货物\n"
            "📍 <b>联系方式 / 当地仓库</b> — 查看地址和联系方式\n"
            "🕘 <b>营业时间</b> — 查看工作时间\n"
            "🏠 <b>我的中国收货地址</b> — 您的专属发货地址\n"
            "👤 <b>个人资料</b> — 查看账户信息\n"
            "🗄 <b>已领取货物</b> — 查看已收货记录\n"
            "🌐 <b>语言</b> — 更改机器人语言\n\n💡 如需帮助，{contact_line}。"
        ),
        "enter_tracking": "请输入运单号：",
        "tracking_not_found": "您的账户中未找到此运单号对应的货物。",
        "parcel_total": "📊 货物总数：{count}",
        "parcel_empty": "您目前没有已登记的货物。",
        "sent_at": "📅 发出日期：{date}",
        "expected_at": "🗓 预计到达：{date}",
        "remaining_days": "⌛ 预计剩余时间：{count}",
        "expected_today": "🗓 预计今天到达",
        "expected_passed": "🗓 预计到达日期已过",
        "warehouse_title": "📦 <b>中国仓库地址</b>",
        "warehouse_receiver": "收件人：{value}",
        "warehouse_phone": "电话：{value}",
        "warehouse_address": "地址：{value}",
        "warehouse_name": "仓库：{value}",
        "error.telegram_registered": "此 Telegram 账户已完成注册。",
        "error.full_name": "请输入完整姓名。",
        "error.phone": "无法识别该电话号码。",
        "error.client_code_assignment": "暂时无法分配新的客户编号，请重试。",
        "error.other_code": "此 Telegram 账户已绑定其他客户编号。",
        "error.owner_mismatch": "客户编号或客户信息不匹配。",
        "error.code_linked": "此客户编号已绑定，请联系管理员。",
        "notification.new": "📦 新货物已登记",
        "notification.dates": "🗓 配送信息已更新",
        "notification.arrived": "🏢 您的货物已到达",
        "notification.ready": "✅ 您的货物可以领取",
        "notification.updated": "🚚 货物状态更新",
        "notification.tracking": "📦 运单号：<code>{value}</code>",
        "notification.client_code": "🔑 客户编号：{value}",
        "notification.status": "📊 状态：{value}",
        "notification.new_expected": "🗓 新的预计到达日期",
        "notification.expected": "🗓 预计到达",
        "reminder.approaching": "🚚 <b>您的货物即将到达</b>",
        "reminder.due": "🗓 <b>预计送达日期已到</b>",
        "reminder.tracking": "📦 运单号：<code>{value}</code>",
        "reminder.client_code": "🔑 客户编号：{value}",
        "reminder.expected": "🗓 预计日期：{date}",
        "reminder.remaining": "⌛ 预计剩余时间：{count}",
        "reminder.pending": "准确到达日期正在确认中。",
    },
}


STATUS_TRANSLATIONS: Final[dict[str, dict[str, str]]] = {
    "ru": {
        "CHINA_WAREHOUSE": "🇨🇳 На складе в Китае",
        "PREPARING": "📦 Готовится к отправке",
        "IN_TRANSIT": "🚚 В пути",
        "ARRIVED_COUNTRY": "🏢 Прибыл",
        "LOCAL_WAREHOUSE": "🏢 На местном складе",
        "READY_FOR_PICKUP": "✅ Готов к выдаче",
        "DELIVERED": "📬 Получен",
        "CANCELLED": "❌ Отменён",
    },
    "en": {
        "CHINA_WAREHOUSE": "🇨🇳 At the China warehouse",
        "PREPARING": "📦 Preparing for dispatch",
        "IN_TRANSIT": "🚚 In transit",
        "ARRIVED_COUNTRY": "🏢 Arrived in destination country",
        "LOCAL_WAREHOUSE": "🏢 At the local warehouse",
        "READY_FOR_PICKUP": "✅ Ready for collection",
        "DELIVERED": "📬 Collected",
        "CANCELLED": "❌ Cancelled",
    },
    "zh": {
        "CHINA_WAREHOUSE": "🇨🇳 已到中国仓库",
        "PREPARING": "📦 准备发货",
        "IN_TRANSIT": "🚚 运输中",
        "ARRIVED_COUNTRY": "🏢 已到达目的国",
        "LOCAL_WAREHOUSE": "🏢 已到当地仓库",
        "READY_FOR_PICKUP": "✅ 可领取",
        "DELIVERED": "📬 已领取",
        "CANCELLED": "❌ 已取消",
    },
}


def normalize_language(language: str | None) -> str:
    return language if language in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE


def t(key: str, language: str | None = None, **values: object) -> str:
    selected = normalize_language(language)
    template = TRANSLATIONS.get(selected, {}).get(key) or TRANSLATIONS[DEFAULT_LANGUAGE][key]
    return template.format(**values)


def text_variants(key: str) -> set[str]:
    return {translations[key] for translations in TRANSLATIONS.values() if key in translations}


def language_for_text(key: str, text: str, fallback: str | None = None) -> str:
    for language, translations in TRANSLATIONS.items():
        if translations.get(key) == text:
            return language
    return normalize_language(fallback)


def status_label(status: object, language: str | None = None) -> str:
    value = getattr(status, "value", str(status))
    selected = normalize_language(language)
    return STATUS_TRANSLATIONS[selected].get(value, value)
