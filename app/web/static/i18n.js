(function () {
  const translations = {
    en: {
      "Статистика": "Dashboard", "Товары": "Shipments", "Клиенты": "Clients",
      "Партии и Excel": "Batches and Excel", "Настройки": "Settings", "Доступ": "Access",
      "Панель": "Admin panel", "Онлайн": "Online", "Нет связи": "Offline",
      "Карго из Китая": "Cargo from China", "Товаров в пути": "Shipments in transit",
      "активные отправления": "active shipments", "Прибыло": "Arrived", "в Кыргызстане": "in Kyrgyzstan",
      "Общая статистика": "Overview", "Обновляется онлайн": "Updates in real time",
      "Все товары": "All shipments", "В базе": "In the database", "Всего профилей": "Total profiles",
      "Telegram привязан": "Telegram linked", "Telegram не привязан": "Telegram not linked",
      "Получают уведомления": "Receiving notifications", "Статусы товаров": "Shipment statuses",
      "Все отправления": "All shipments", "Последние товары": "Recent shipments", "Показать все": "View all",
      "Загрузка…": "Loading…", "Все статусы": "All statuses", "Сначала обновлённые": "Recently updated first",
      "По трек-коду": "By tracking number", "Поиск": "Search", "Трек-код или H-код": "Tracking number or H-code",
      "Трек-код": "Tracking number", "Клиент": "Client", "Статус": "Status", "Обновить": "Refresh",
      "Клиенты и H-коды": "Clients and H-codes", "Поиск клиентов": "Search clients",
      "ФИО, телефон или H-код": "Name, phone number, or H-code", "H-код": "H-code", "Управление": "Actions",
      "Загрузите список — бот сам распределит товары по H-кодам.": "Upload a list and the bot will assign shipments by H-code automatically.",
      "Добавить": "Add", "Статус всей партии:": "Batch status:",
      "откройте нужную строку и выберите новый статус. Он применится ко всем товарам партии, а клиенты получат уведомления.": "open a batch and select a new status. It will be applied to every shipment in that batch, and clients will be notified.",
      "Файл": "File", "Даты": "Dates", "Товары и действия": "Shipments and actions",
      "Основные настройки": "General settings", "Название компании": "Company name",
      "Срок доставки по умолчанию, дней": "Default delivery time, days", "Адрес склада в Китае": "China warehouse address",
      "Получатель": "Recipient", "Телефон": "Phone", "Адрес": "Address", "Название склада": "Warehouse name",
      "Адрес склада в Китае №1": "China warehouse address #1", "Адрес склада в Китае №2": "China warehouse address #2",
      "Удалить склад 2": "Delete warehouse 2", "Удалить склад 2 и все его данные?": "Delete warehouse 2 and all its data?",
      "Склад 2 удалён": "Warehouse 2 deleted", "Демо: склад 2 удалён": "Demo: warehouse 2 deleted",
      "Поддержка": "Support", "Telegram поддержки": "Support Telegram", "Сохранить настройки": "Save settings",
      "WhatsApp": "WhatsApp",
      "График работы": "Business hours", "Рабочие дни и часы": "Working days and hours",
      "Адрес склада в Бишкеке": "Bishkek warehouse address",
      "Откройте панель через Telegram": "Open the panel through Telegram",
      "Доступ разрешён только администраторам BCL EXPRESS.": "Access is restricted to BCL EXPRESS administrators.",
      "Попробовать снова": "Try again", "ИЗМЕНЕНИЕ ТОВАРА": "EDIT SHIPMENT", "Статус товара": "Shipment status",
      "Новый статус": "New status", "Отмена": "Cancel", "Сохранить": "Save",
      "ИНФОРМАЦИЯ О ПАРТИИ": "BATCH INFORMATION", "Партия": "Batch", "Закрыть": "Close",
      "Новый статус партии": "New batch status", "Дата выезда": "Dispatch date", "Срок доставки, дней": "Delivery time, days",
      "Применить ко всей партии": "Apply to entire batch", "КЛИЕНТ": "CLIENT", "Профиль клиента": "Client profile",
      "Редактировать": "Edit", "Все товары": "All shipments", "Блокировка": "Restrictions",
      "УПРАВЛЕНИЕ КЛИЕНТОМ": "MANAGE CLIENT", "Добавить клиента": "Add client", "ФИО": "Full name", "Город": "City",
      "Оставьте пустым для автоназначения": "Leave blank to assign automatically", "Можно оставить пустым": "Optional",
      "ДОСТУП К БОТУ": "BOT ACCESS", "Блокировка клиента": "Client restrictions", "Действие": "Action",
      "Заблокировать временно": "Block temporarily", "Заблокировать навсегда": "Block permanently", "Разблокировать": "Unblock",
      "Срок блокировки": "Restriction period", "1 день": "1 day", "3 дня": "3 days", "7 дней": "7 days",
      "14 дней": "14 days", "30 дней": "30 days", "90 дней": "90 days",
      "Заблокированный клиент не сможет пользоваться ботом и получать уведомления до снятия ограничения.": "A blocked client cannot use the bot or receive notifications until the restriction is removed.",
      "Применить": "Apply", "ТОВАРЫ КЛИЕНТА": "CLIENT SHIPMENTS", "Выберите вариант": "Select an option",
      "НОВАЯ ПАРТИЯ": "NEW BATCH", "Загрузить Excel": "Upload Excel", "Выбрать файл": "Choose file",
      ".xls или .xlsx, до 20 МБ": ".xls or .xlsx, up to 20 MB", "Статус партии": "Batch status", "Импортировать": "Import",
      "Быстрое действие": "Quick action", "Открыть меню": "Open menu", "Навигация": "Navigation", "Обновить клиентов": "Refresh clients",
      "Список клиентов обновлён": "Client list refreshed",
      "Не удалось выполнить действие": "The action could not be completed", "Дата не указана": "Date not provided",
      "Клиент не привязан": "Client not linked", "Остальные статусы": "Other statuses",
      "Статистика появится после загрузки товаров": "Statistics will appear after shipments are uploaded", "Товаров пока нет": "No shipments yet",
      "По этому запросу товары не найдены": "No shipments match your search", "Клиенты не найдены": "No clients found",
      "Заблокирован": "Blocked", "указанного срока": "the specified date", "Открыть": "Open", "товаров": "shipments",
      "Ожидается": "Expected", "Без расчётной даты": "No estimated date", "новых / обновлено": "new / updated",
      "Статус партии": "Batch status", "Импортов пока нет": "No imports yet", "Активен": "Active",
      "Заблокирован навсегда": "Blocked permanently", "Заблокировать": "Block", "Изменить блокировку": "Change restriction",
      "Не указан": "Not provided", "Не указана": "Not provided", "Не привязан": "Not linked", "Доступ": "Access",
      "Текущий статус": "Current status", "Ожидаемая дата": "Estimated arrival", "Не рассчитана": "Not calculated",
      "У клиента пока нет товаров": "This client has no shipments yet", "Выберите статус": "Select a status",
      "Сортировать товары": "Sort shipments", "Демо: партия отмечена прибывшей": "Demo: batch marked as arrived",
      "Демо: статус обновлён": "Demo: status updated", "Статус обновлён, клиент уведомлён": "Status updated and client notified",
      "Статус обновлён": "Status updated", "Демо: статус всей партии обновлён": "Demo: batch status updated",
      "Данные клиента обновлены": "Client details updated", "Клиент добавлен": "Client added",
      "Клиент разблокирован": "Client unblocked", "Ограничение применено": "Restriction applied",
      "Обрабатываю…": "Processing…", "Демо: Excel обработан": "Demo: Excel processed",
      "Демо: настройки сохранены": "Demo: settings saved", "Настройки сохранены": "Settings saved",
      "Администратор": "Administrator", "Обычный пользователь": "Regular user", "Выдать админку": "Grant admin access",
      "Убрать админку": "Revoke admin access", "Главный администратор": "Primary administrator",
      "Админ-доступ выдан": "Admin access granted", "Админ-доступ отозван": "Admin access revoked", "Редактировать клиента": "Edit client",
      "Некорректная дата": "Invalid date", "Нет доступа": "Access denied", "Нет доступа к админ-панели": "You do not have access to the admin panel",
      "Товар не найден": "Shipment not found", "Проверьте ФИО и телефон": "Check the full name and phone number",
      "Код клиента должен быть в формате H-801": "The client code must use the H-801 format", "H-код или Telegram ID уже используется": "This H-code or Telegram ID is already in use",
      "Клиент не найден": "Client not found", "Этот Telegram ID уже привязан к другому клиенту": "This Telegram ID is linked to another client",
      "Сначала привяжите Telegram ID клиента": "Link the client's Telegram ID first", "Главного администратора нельзя лишить доступа из панели": "Primary administrator access cannot be revoked from the panel",
      "Нужен файл .xls или .xlsx": "Upload an .xls or .xlsx file", "Файл больше 20 МБ": "The file is larger than 20 MB",
      "Срок должен быть от 1 до 90 дней": "The delivery time must be between 1 and 90 days", "Партия уже обновлена": "The batch has already been updated", "Партия не найдена": "Batch not found",
      "Редактировать товар": "Edit shipment", "H-код клиента": "Client H-code", "Удалить": "Delete",
      "Товар обновлён": "Shipment updated", "Товар обновлён, клиент уведомлён": "Shipment updated and client notified", "Товар удалён": "Shipment deleted",
      "Ожидаемая дата не может быть раньше даты выезда": "The estimated arrival date cannot be earlier than the dispatch date",
      "Язык": "Language", "Русский": "Russian", "Английский": "English", "Китайский": "Chinese",
      "ЗАГРУЗКА ПАРТИИ": "BATCH UPLOAD", "Куда загрузить": "Upload destination", "Создать новую партию": "Create a new batch",
      "После выбора файла система проверит похожие партии.": "After you select a file, the system will check for similar batches.",
      "Проверяю файл и ищу похожую партию…": "Checking the file and looking for a similar batch…",
      "Этот файл уже загружен в партию №{id}. Повторный импорт не требуется.": "This file has already been uploaded to batch #{id}. No repeat import is needed.",
      "Найдена похожая партия №{id}: совпало {overlap} из {total} трек-кодов. Будет обновлена эта партия.": "Similar batch #{id} found: {overlap} of {total} tracking numbers match. This batch will be updated.",
      "Похожая партия не найдена. Будет создана новая партия.": "No similar batch was found. A new batch will be created.",
      "Этот файл уже был загружен": "This file has already been uploaded", "Партия обновлена": "Batch updated",
      "Новая партия создана": "New batch created", "Новых": "New", "обновлено": "updated",
      "Язык интерфейса": "Interface language", "Удалить партию": "Delete batch", "Партия удалена": "Batch deleted",
      "УДАЛЕНИЕ ПАРТИИ": "DELETE BATCH", "Что удалить": "What to delete",
      "Только карточку партии и историю": "Batch record and history only", "Партию вместе с товарами": "Batch and shipments",
      "Товары останутся в базе без привязки к партии.": "Shipments will remain in the database without a batch.",
      "Партия, история и все её товары будут удалены без возможности восстановления.": "The batch, its history, and all its shipments will be permanently deleted.",
      "Подтвердить удаление": "Confirm deletion"
    },
    zh: {
      "Статистика": "数据概览", "Товары": "货物", "Клиенты": "客户", "Партии и Excel": "批次与 Excel",
      "Настройки": "设置", "Доступ": "访问权限", "Панель": "管理面板", "Онлайн": "在线", "Нет связи": "连接中断",
      "Карго из Китая": "中国货运", "Товаров в пути": "运输中的货物", "активные отправления": "运输中的货物",
      "Прибыло": "已到达", "в Кыргызстане": "已到吉尔吉斯斯坦", "Общая статистика": "总体数据", "Обновляется онлайн": "实时更新",
      "Все товары": "全部货物", "В базе": "数据库记录", "Всего профилей": "客户总数", "Telegram привязан": "已绑定 Telegram",
      "Telegram не привязан": "未绑定 Telegram", "Получают уведомления": "可接收通知", "Статусы товаров": "货物状态",
      "Все отправления": "全部货物", "Последние товары": "最新货物", "Показать все": "查看全部", "Загрузка…": "加载中…",
      "Все статусы": "全部状态", "Сначала обновлённые": "最近更新优先", "По трек-коду": "按运单号排序", "Поиск": "搜索",
      "Трек-код или H-код": "运单号或 H 编号", "Трек-код": "运单号", "Клиент": "客户", "Статус": "状态", "Обновить": "刷新",
      "Клиенты и H-коды": "客户与 H 编号", "Поиск клиентов": "搜索客户", "ФИО, телефон или H-код": "姓名、电话或 H 编号",
      "H-код": "H 编号", "Управление": "操作", "Загрузите список — бот сам распределит товары по H-кодам.": "上传清单后，机器人会按 H 编号自动分配货物。",
      "Добавить": "添加", "Статус всей партии:": "整批状态：", "откройте нужную строку и выберите новый статус. Он применится ко всем товарам партии, а клиенты получат уведомления.": "打开相应批次并选择新状态。该状态会应用到本批次全部货物，客户也会收到通知。",
      "Файл": "文件", "Даты": "日期", "Товары и действия": "货物与操作", "Основные настройки": "基本设置",
      "Название компании": "公司名称", "Срок доставки по умолчанию, дней": "默认运输时长（天）", "Адрес склада в Китае": "中国仓库地址",
      "Получатель": "收件人", "Телефон": "电话", "Адрес": "地址", "Название склада": "仓库名称", "Поддержка": "客户服务",
      "Адрес склада в Китае №1": "中国仓库地址 1", "Адрес склада в Китае №2": "中国仓库地址 2",
      "Удалить склад 2": "删除仓库 2", "Удалить склад 2 и все его данные?": "删除仓库 2 及其全部数据？",
      "Склад 2 удалён": "仓库 2 已删除", "Демо: склад 2 удалён": "演示：仓库 2 已删除",
      "Telegram поддержки": "客服 Telegram", "Сохранить настройки": "保存设置", "Откройте панель через Telegram": "请通过 Telegram 打开管理面板",
      "WhatsApp": "WhatsApp",
      "График работы": "营业时间", "Рабочие дни и часы": "工作日及时间",
      "Адрес склада в Бишкеке": "比什凯克仓库地址",
      "Доступ разрешён только администраторам BCL EXPRESS.": "仅 BCL EXPRESS 管理员可以访问。", "Попробовать снова": "重试",
      "ИЗМЕНЕНИЕ ТОВАРА": "修改货物", "Статус товара": "货物状态", "Новый статус": "新状态", "Отмена": "取消", "Сохранить": "保存",
      "ИНФОРМАЦИЯ О ПАРТИИ": "批次信息", "Партия": "批次", "Закрыть": "关闭", "Новый статус партии": "批次新状态",
      "Дата выезда": "发出日期", "Срок доставки, дней": "运输时长（天）", "Применить ко всей партии": "应用到整个批次",
      "КЛИЕНТ": "客户", "Профиль клиента": "客户资料", "Редактировать": "编辑", "Блокировка": "权限限制",
      "УПРАВЛЕНИЕ КЛИЕНТОМ": "客户管理", "Добавить клиента": "添加客户", "ФИО": "姓名", "Город": "城市",
      "Оставьте пустым для автоназначения": "留空则自动分配", "Можно оставить пустым": "可选填", "ДОСТУП К БОТУ": "机器人访问权限",
      "Блокировка клиента": "限制客户权限", "Действие": "操作", "Заблокировать временно": "暂时限制", "Заблокировать навсегда": "永久限制",
      "Разблокировать": "解除限制", "Срок блокировки": "限制时长", "1 день": "1 天", "3 дня": "3 天", "7 дней": "7 天",
      "14 дней": "14 天", "30 дней": "30 天", "90 дней": "90 天", "Заблокированный клиент не сможет пользоваться ботом и получать уведомления до снятия ограничения.": "解除限制前，该客户无法使用机器人或接收通知。",
      "Применить": "应用", "ТОВАРЫ КЛИЕНТА": "客户货物", "Выберите вариант": "请选择", "НОВАЯ ПАРТИЯ": "新批次",
      "Загрузить Excel": "上传 Excel", "Выбрать файл": "选择文件", ".xls или .xlsx, до 20 МБ": ".xls 或 .xlsx，最大 20 MB",
      "Статус партии": "批次状态", "Импортировать": "导入", "Быстрое действие": "快捷操作", "Открыть меню": "打开菜单",
      "Навигация": "导航", "Обновить клиентов": "刷新客户", "Не удалось выполнить действие": "操作失败", "Дата не указана": "未提供日期",
      "Список клиентов обновлён": "客户列表已刷新",
      "Клиент не привязан": "未绑定客户", "Остальные статусы": "其他状态", "Статистика появится после загрузки товаров": "上传货物后将显示统计数据",
      "Товаров пока нет": "暂无货物", "По этому запросу товары не найдены": "未找到符合条件的货物", "Клиенты не найдены": "未找到客户",
      "Заблокирован": "已限制", "указанного срока": "指定日期", "Открыть": "打开", "товаров": "件货物", "Ожидается": "预计",
      "Без расчётной даты": "暂无预计日期", "новых / обновлено": "新增 / 更新", "Импортов пока нет": "暂无导入记录", "Активен": "正常",
      "Заблокирован навсегда": "永久限制", "Заблокировать": "限制", "Изменить блокировку": "修改限制", "Не указан": "未提供",
      "Не указана": "未提供", "Не привязан": "未绑定", "Доступ": "访问权限", "Текущий статус": "当前状态", "Ожидаемая дата": "预计到达日期",
      "Не рассчитана": "未计算", "У клиента пока нет товаров": "该客户暂无货物", "Выберите статус": "选择状态", "Сортировать товары": "货物排序",
      "Демо: партия отмечена прибывшей": "演示：批次已标记为到达", "Демо: статус обновлён": "演示：状态已更新",
      "Статус обновлён, клиент уведомлён": "状态已更新，并已通知客户", "Статус обновлён": "状态已更新",
      "Демо: статус всей партии обновлён": "演示：批次状态已更新", "Данные клиента обновлены": "客户资料已更新", "Клиент добавлен": "客户已添加",
      "Клиент разблокирован": "客户限制已解除", "Ограничение применено": "限制已生效", "Обрабатываю…": "处理中…",
      "Демо: Excel обработан": "演示：Excel 已处理", "Демо: настройки сохранены": "演示：设置已保存", "Настройки сохранены": "设置已保存",
      "Администратор": "管理员", "Обычный пользователь": "普通用户", "Выдать админку": "授予管理员权限", "Убрать админку": "撤销管理员权限",
      "Главный администратор": "主管理员", "Админ-доступ выдан": "已授予管理员权限", "Админ-доступ отозван": "已撤销管理员权限", "Редактировать клиента": "编辑客户",
      "Некорректная дата": "日期格式不正确", "Нет доступа": "无访问权限", "Нет доступа к админ-панели": "您无权访问管理面板",
      "Товар не найден": "未找到货物", "Проверьте ФИО и телефон": "请检查姓名和电话号码",
      "Код клиента должен быть в формате H-801": "客户编号格式应为 H-801", "H-код или Telegram ID уже используется": "该 H 编号或 Telegram ID 已被使用",
      "Клиент не найден": "未找到客户", "Этот Telegram ID уже привязан к другому клиенту": "该 Telegram ID 已绑定其他客户",
      "Сначала привяжите Telegram ID клиента": "请先绑定客户的 Telegram ID", "Главного администратора нельзя лишить доступа из панели": "无法在面板中撤销主管理员权限",
      "Нужен файл .xls или .xlsx": "请上传 .xls 或 .xlsx 文件", "Файл больше 20 МБ": "文件超过 20 MB",
      "Срок должен быть от 1 до 90 дней": "运输时长应为 1 至 90 天", "Партия уже обновлена": "该批次已更新", "Партия не найдена": "未找到批次",
      "Редактировать товар": "编辑货物", "H-код клиента": "客户 H 编号", "Удалить": "删除",
      "Товар обновлён": "货物已更新", "Товар обновлён, клиент уведомлён": "货物已更新，并已通知客户", "Товар удалён": "货物已删除",
      "Ожидаемая дата не может быть раньше даты выезда": "预计到达日期不能早于发出日期",
      "Язык": "语言", "Русский": "俄语", "Английский": "英语", "Китайский": "中文",
      "ЗАГРУЗКА ПАРТИИ": "上传批次", "Куда загрузить": "上传到", "Создать новую партию": "创建新批次",
      "После выбора файла система проверит похожие партии.": "选择文件后，系统会检查是否存在相似批次。",
      "Проверяю файл и ищу похожую партию…": "正在检查文件并查找相似批次…",
      "Этот файл уже загружен в партию №{id}. Повторный импорт не требуется.": "该文件已上传至批次 #{id}，无需重复导入。",
      "Найдена похожая партия №{id}: совпало {overlap} из {total} трек-кодов. Будет обновлена эта партия.": "发现相似批次 #{id}：{total} 个运单号中有 {overlap} 个一致。系统将更新该批次。",
      "Похожая партия не найдена. Будет создана новая партия.": "未找到相似批次，将创建新批次。",
      "Этот файл уже был загружен": "该文件已上传", "Партия обновлена": "批次已更新",
      "Новая партия создана": "已创建新批次", "Новых": "新增", "обновлено": "更新",
      "Язык интерфейса": "界面语言", "Удалить партию": "删除批次", "Партия удалена": "批次已删除",
      "УДАЛЕНИЕ ПАРТИИ": "删除批次", "Что удалить": "请选择删除内容",
      "Только карточку партии и историю": "仅删除批次记录及历史", "Партию вместе с товарами": "删除批次及其中货物",
      "Товары останутся в базе без привязки к партии.": "货物将保留在数据库中，但不再关联任何批次。",
      "Партия, история и все её товары будут удалены без возможности восстановления.": "该批次、历史记录及其中全部货物将被永久删除，无法恢复。",
      "Подтвердить удаление": "确认删除"
    }
  };

  const statuses = {
    ru: { CHINA_WAREHOUSE: "На складе в Китае", PREPARING: "Готовится к отправке", IN_TRANSIT: "В пути", ARRIVED_COUNTRY: "Прибыл", LOCAL_WAREHOUSE: "На местном складе", READY_FOR_PICKUP: "Готов к выдаче", DELIVERED: "Получен", CANCELLED: "Отменён" },
    en: { CHINA_WAREHOUSE: "At the China warehouse", PREPARING: "Preparing for dispatch", IN_TRANSIT: "In transit", ARRIVED_COUNTRY: "Arrived in destination country", LOCAL_WAREHOUSE: "At the local warehouse", READY_FOR_PICKUP: "Ready for collection", DELIVERED: "Collected", CANCELLED: "Cancelled" },
    zh: { CHINA_WAREHOUSE: "已到中国仓库", PREPARING: "准备发货", IN_TRANSIT: "运输中", ARRIVED_COUNTRY: "已到达目的国", LOCAL_WAREHOUSE: "已到当地仓库", READY_FOR_PICKUP: "可领取", DELIVERED: "已领取", CANCELLED: "已取消" }
  };

  const knownKeys = new Set(Object.keys(translations.en).concat(Object.keys(translations.zh)));
  const textNodes = new Map();

  function detectLanguage() {
    const saved = localStorage.getItem("bcl-admin-language");
    if (["ru", "en", "zh"].includes(saved)) return saved;
    const telegramLanguage = window.Telegram?.WebApp?.initDataUnsafe?.user?.language_code || "";
    if (telegramLanguage.toLowerCase().startsWith("zh")) return "zh";
    if (telegramLanguage.toLowerCase().startsWith("en")) return "en";
    return "ru";
  }

  let language = detectLanguage();

  function translate(key, values = {}) {
    let result = language === "ru" ? key : (translations[language]?.[key] || key);
    Object.entries(values).forEach(([name, value]) => {
      result = result.replaceAll(`{${name}}`, String(value));
    });
    return result;
  }

  function registerStaticNodes() {
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    while (walker.nextNode()) {
      const node = walker.currentNode;
      const key = node.nodeValue.trim();
      if (knownKeys.has(key)) textNodes.set(node, key);
    }
    document.querySelectorAll("[placeholder], [aria-label]").forEach((element) => {
      for (const attribute of ["placeholder", "aria-label"]) {
        const key = element.getAttribute(attribute);
        if (knownKeys.has(key)) element.dataset[`i18n${attribute === "placeholder" ? "Placeholder" : "Aria"}`] = key;
      }
    });
  }

  function applyStatic() {
    if (!textNodes.size) registerStaticNodes();
    textNodes.forEach((key, node) => {
      const leading = node.nodeValue.match(/^\s*/)?.[0] || "";
      const trailing = node.nodeValue.match(/\s*$/)?.[0] || "";
      node.nodeValue = `${leading}${translate(key)}${trailing}`;
    });
    document.querySelectorAll("[data-i18n-placeholder]").forEach((element) => { element.placeholder = translate(element.dataset.i18nPlaceholder); });
    document.querySelectorAll("[data-i18n-aria]").forEach((element) => { element.setAttribute("aria-label", translate(element.dataset.i18nAria)); });
    document.documentElement.lang = language === "zh" ? "zh-CN" : language;
    document.querySelectorAll("[data-language]").forEach((button) => {
      button.setAttribute("aria-pressed", String(button.dataset.language === language));
    });
  }

  function setLanguage(nextLanguage) {
    if (!["ru", "en", "zh"].includes(nextLanguage)) return;
    language = nextLanguage;
    localStorage.setItem("bcl-admin-language", language);
    applyStatic();
  }

  window.AdminI18n = {
    applyStatic,
    get language() { return language; },
    setLanguage,
    status(value) { return statuses[language]?.[value] || value; },
    t: translate,
  };
})();
