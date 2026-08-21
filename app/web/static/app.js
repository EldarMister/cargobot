const tg = window.Telegram?.WebApp;
const i18n = window.AdminI18n;
const tr = (key, values = {}) => i18n.t(key, values);

const state = {
  authenticated: false,
  demo: false,
  currentView: "dashboard",
  statusFilter: "",
  activePicker: null,
  statuses: [],
  defaultTransitDays: 12,
  parcels: [],
  clients: [],
  imports: [],
  settings: null,
  selectedParcel: null,
  selectedClient: null,
  selectedImport: null,
  reloadTimer: null,
};

const pageTitles = {
  dashboard: "Статистика",
  parcels: "Товары",
  clients: "Клиенты",
  imports: "Партии и Excel",
  settings: "Настройки",
  auth: "Доступ",
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
i18n.applyStatic();

function refreshIcons() {
  window.lucide?.createIcons({
    attrs: {
      "stroke-width": 1.8,
      "aria-hidden": "true",
    },
  });
}

function escapeHtml(value = "") {
  return String(value).replace(/[&<>'"]/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;",
  })[char]);
}

function toast(message, error = false) {
  const element = $("#toast");
  element.textContent = message;
  element.className = `toast show${error ? " error" : ""}`;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => { element.className = "toast"; }, 2800);
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    credentials: "same-origin",
    headers: options.body instanceof FormData ? {} : { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail ? tr(data.detail) : tr("Не удалось выполнить действие"));
  }
  return response.json();
}

function openDrawer() {
  $("#drawer").classList.add("open");
  $("#drawer").setAttribute("aria-hidden", "false");
  $("#drawer-backdrop").hidden = false;
  $("#menu-toggle").setAttribute("aria-expanded", "true");
}

function closeDrawer() {
  $("#drawer").classList.remove("open");
  $("#drawer").setAttribute("aria-hidden", "true");
  $("#drawer-backdrop").hidden = true;
  $("#menu-toggle").setAttribute("aria-expanded", "false");
}

function showView(name) {
  state.currentView = name;
  $$(".view").forEach((view) => view.classList.toggle("active", view.dataset.view === name));
  $$("[data-nav]").forEach((button) => button.classList.toggle("active", button.dataset.nav === name));
  $("#page-title").textContent = tr(pageTitles[name] || "Панель");
  $("#floating-action").hidden = !["clients", "imports"].includes(name);
  closeDrawer();
  if (name !== "auth") loadView(name);
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function empty(message) {
  return `<div class="empty-state">${escapeHtml(message)}</div>`;
}

function statusTone(status) {
  return ({
    CHINA_WAREHOUSE: "orange",
    PREPARING: "amber",
    IN_TRANSIT: "blue",
    ARRIVED_COUNTRY: "violet",
    LOCAL_WAREHOUSE: "violet",
    READY_FOR_PICKUP: "green",
    DELIVERED: "slate",
    CANCELLED: "red",
  })[status] || "blue";
}

function statusText(label) {
  return String(label || "").replace(/^(?:🇨🇳|📦|🚚|🏢|✅|📬|❌)\s*/u, "");
}

function statusIcon(status) {
  return ({
    CHINA_WAREHOUSE: "flag",
    PREPARING: "package",
    IN_TRANSIT: "truck",
    ARRIVED_COUNTRY: "building-2",
    LOCAL_WAREHOUSE: "warehouse",
    READY_FOR_PICKUP: "square-check",
    DELIVERED: "circle-check",
    CANCELLED: "circle-x",
  })[status] || "circle";
}

function statusBadge(parcel, actions) {
  const tag = actions ? "button" : "span";
  const action = actions ? ` type="button" data-edit-parcel="${parcel.id}"` : "";
  return `<${tag} class="status-badge ${statusTone(parcel.status)}"${action}><i data-lucide="${statusIcon(parcel.status)}" aria-hidden="true"></i><span>${escapeHtml(i18n.status(parcel.status))}</span></${tag}>`;
}

function parcelRow(parcel, actions = true) {
  return `
    <article class="table-row parcel-row">
      <div><strong>${escapeHtml(parcel.tracking_number)}</strong><small>${parcel.expected_at ? escapeHtml(parcel.expected_at) : tr("Дата не указана")}</small></div>
      <div><span class="table-cell-code">${escapeHtml(parcel.client_code)}</span><small>${escapeHtml(parcel.client_name || tr("Клиент не привязан"))}</small></div>
      <div>${statusBadge(parcel, actions)}</div>
    </article>`;
}

function renderDashboard(data) {
  $("#hero-transit").textContent = data.in_transit;
  $("#stat-parcels").textContent = data.total_parcels;
  $("#stat-clients").textContent = data.total_clients;
  $("#stat-linked").textContent = data.linked_clients;
  $("#stat-arrived").textContent = data.arrived;

  const statusCounts = data.status_counts || {
    IN_TRANSIT: data.in_transit,
    ARRIVED_COUNTRY: data.arrived,
    OTHER: Math.max(0, data.total_parcels - data.in_transit - data.arrived),
  };
  const labels = Object.fromEntries(state.statuses.map((item) => [item.value, i18n.status(item.value)]));
  labels.OTHER = tr("Остальные статусы");
  $("#status-summary").innerHTML = Object.entries(statusCounts)
    .filter(([, count]) => count > 0)
    .map(([value, count]) => `
      <div class="status-line">
        <span><i data-lucide="${statusIcon(value)}" class="status-dot ${statusTone(value)}" aria-hidden="true"></i>${escapeHtml(labels[value] || value)}</span><b>${count}</b>
      </div>`).join("") || empty(tr("Статистика появится после загрузки товаров"));

  const recent = state.parcels.slice(0, 5);
  $("#recent-parcels").innerHTML = recent.length
    ? recent.map((parcel) => parcelRow(parcel, false)).join("")
    : empty(tr("Товаров пока нет"));
  refreshIcons();
}

function sortedParcels() {
  const rows = [...state.parcels];
  if ($("#parcel-sort").value === "tracking") {
    rows.sort((a, b) => a.tracking_number.localeCompare(b.tracking_number, i18n.language));
  }
  return rows;
}

function renderParcels() {
  const rows = sortedParcels();
  const summary = i18n.language === "en"
    ? `Shipments shown: <b>${rows.length}</b>${state.statusFilter ? " · status filter applied" : " · all statuses"}`
    : i18n.language === "zh"
      ? `显示货物：<b>${rows.length}</b>${state.statusFilter ? " · 已按状态筛选" : " · 全部状态"}`
      : `Показано товаров: <b>${rows.length}</b>${state.statusFilter ? " · применён фильтр по статусу" : " · все статусы"}`;
  $("#parcel-summary").innerHTML = summary;
  $("#parcel-list").innerHTML = rows.length
    ? rows.map((parcel) => parcelRow(parcel)).join("")
    : empty(tr("По этому запросу товары не найдены"));
  refreshIcons();
}

function renderClients() {
  $("#client-list").innerHTML = state.clients.length
    ? state.clients.map((client) => `
      <article class="table-row">
        <div><strong>${escapeHtml(client.full_name)}</strong><small>${escapeHtml(client.phone)} · ${client.telegram_id ? tr("Telegram привязан") : tr("Telegram не привязан")}${client.is_admin ? ` · ${tr("Администратор")}` : ""}</small>${client.is_blocked ? `<span class="block-badge">${client.block_mode === "permanent" ? tr("Заблокирован") : `${i18n.language === "en" ? "Until" : i18n.language === "zh" ? "截至" : "До"} ${escapeHtml(client.blocked_until_text || tr("указанного срока"))}`}</span>` : ""}</div>
        <div><span class="table-cell-code">${escapeHtml(client.client_code)}</span></div>
        <div><b>${client.parcels}</b><small>${tr("товаров")}</small><button class="manage-action" data-manage-client="${client.id}">${tr("Открыть")}</button></div>
      </article>`).join("")
    : empty(tr("Клиенты не найдены"));
}

function importRow(item) {
  return `
    <article class="table-row import-row" data-edit-import="${item.id}" role="button" tabindex="0" aria-label="${tr("Открыть")} ${tr("Партия")} №${item.id}">
      <div><div class="import-name"><span class="excel-mark"><i data-lucide="file-spreadsheet" aria-hidden="true"></i></span><strong>${escapeHtml(item.filename)}</strong></div><small>${tr("Партия")} №${item.id} · ${escapeHtml(i18n.status(item.status))}</small></div>
      <div>${item.sent_at ? `<span>${escapeHtml(item.sent_at)}</span>` : "—"}<small>${item.expected_at ? `${tr("Ожидается")} ${escapeHtml(item.expected_at)}` : tr("Без расчётной даты")}</small></div>
      <div><b>+${item.created_rows}</b> / ${item.updated_rows}<small>${tr("новых / обновлено")}</small><button class="manage-action" data-edit-import="${item.id}">${tr("Статус партии")}</button></div><i data-lucide="chevron-right" class="row-chevron" aria-hidden="true"></i>
    </article>`;
}

function renderImports() {
  $("#import-list").innerHTML = state.imports.length
    ? state.imports.map(importRow).join("")
    : empty(tr("Импортов пока нет"));
  refreshIcons();
}

function closeDialog(id) {
  const dialog = $(`#${id}`);
  if (dialog?.open) dialog.close();
}

function clientBlockText(client) {
  if (!client.is_blocked) return tr("Активен");
  if (client.block_mode === "permanent") return tr("Заблокирован навсегда");
  if (i18n.language === "en") return `Blocked until ${client.blocked_until_text || tr("указанного срока")}`;
  if (i18n.language === "zh") return `限制至 ${client.blocked_until_text || tr("указанного срока")}`;
  return `Заблокирован до ${client.blocked_until_text || tr("указанного срока")}`;
}

function openClientDetail(clientId) {
  state.selectedClient = state.clients.find((client) => client.id === Number(clientId));
  if (!state.selectedClient) return;
  const client = state.selectedClient;
  $("#client-detail-name").textContent = client.full_name;
  $("#client-detail").innerHTML = `
    <div><span>${tr("J-код")}</span><b>${escapeHtml(client.client_code)}</b></div>
    <div><span>${tr("Телефон")}</span><b>${escapeHtml(client.phone)}</b></div>
    <div><span>${tr("Город")}</span><b>${escapeHtml(client.city || tr("Не указан"))}</b></div>
    <div><span>Telegram ID</span><b>${escapeHtml(client.telegram_id || tr("Не привязан"))}</b></div>
    <div><span>${tr("Товары")}</span><b>${client.parcels}</b></div>
    <div><span>${tr("Язык")}</span><b>${client.language === "en" ? tr("Английский") : client.language === "zh" ? tr("Китайский") : client.language === "ru" ? tr("Русский") : tr("Не указан")}</b></div>
    <div><span>${tr("Доступ")}</span><b>${escapeHtml(clientBlockText(client))}</b></div>
    <div><span>${tr("Администратор")}</span><b>${client.is_system_admin ? tr("Главный администратор") : client.is_admin ? tr("Администратор") : tr("Обычный пользователь")}</b></div>`;
  $("#client-block-action").textContent = client.is_blocked ? tr("Изменить блокировку") : tr("Заблокировать");
  $("#client-admin-action").textContent = client.is_admin ? tr("Убрать админку") : tr("Выдать админку");
  $("#client-admin-action").disabled = Boolean(client.is_system_admin);
  $("#client-detail-sheet").showModal();
}

function openClientForm(client = null) {
  state.selectedClient = client;
  $("#client-form").reset();
  $("#client-form-id").value = client?.id || "";
  $("#client-form-title").textContent = client ? tr("Редактировать клиента") : tr("Добавить клиента");
  $("#client-code-field").hidden = Boolean(client);
  $("#client-form-code").value = client?.client_code || "";
  $("#client-form-name").value = client?.full_name || "";
  $("#client-form-phone").value = client?.phone || "";
  $("#client-form-city").value = client?.city || "";
  $("#client-form-telegram").value = client?.telegram_id || "";
  $("#client-form-sheet").showModal();
}

function openBatchStatus(importId) {
  state.selectedImport = state.imports.find((item) => item.id === Number(importId));
  if (!state.selectedImport) return;
  $("#batch-status-title").textContent = `${tr("Партия")} №${state.selectedImport.id}`;
  $("#batch-status-detail").innerHTML = `
    <div><span>${tr("Файл")}</span><b>${escapeHtml(state.selectedImport.filename)}</b></div>
    <div><span>${tr("Текущий статус")}</span><b>${escapeHtml(i18n.status(state.selectedImport.status))}</b></div>
    <div><span>${tr("Дата выезда")}</span><b>${escapeHtml(state.selectedImport.sent_at || tr("Не указана"))}</b></div>
    <div><span>${tr("Ожидаемая дата")}</span><b>${escapeHtml(state.selectedImport.expected_at || tr("Не рассчитана"))}</b></div>
    <div><span>${tr("Товары")}</span><b>+${state.selectedImport.created_rows} / ${state.selectedImport.updated_rows} · ${tr("новых / обновлено")}</b></div>`;
  $("#batch-status-select").value = state.selectedImport.status;
  $("#batch-sent-date").value = state.selectedImport.sent_date || "";
  $("#batch-expected-date").value = state.selectedImport.expected_date || "";
  $("#batch-transit-days").value = state.defaultTransitDays;
  $("#batch-status-sheet").showModal();
}

function renderClientParcels(client, parcels) {
  $("#client-parcels-title").textContent = `${client.full_name} · ${client.client_code}`;
  $("#client-parcels-list").innerHTML = parcels.length
    ? parcels.map((parcel) => parcelRow(parcel, false)).join("")
    : empty(tr("У клиента пока нет товаров"));
  refreshIcons();
}

function renderSettings(values) {
  state.settings = values;
  $("#setting-company").value = values.company_name || "";
  $("#setting-days").value = values.default_transit_days || 12;
  $("#setting-receiver").value = values.warehouse_receiver || "";
  $("#setting-phone").value = values.warehouse_phone || "";
  $("#setting-address").value = values.warehouse_address || "";
  $("#setting-name").value = values.warehouse_name || "";
  $("#setting-support").value = values.support_username || "";
}

function buildStatusControls() {
  const options = state.statuses.map((item) => `<option value="${item.value}">${escapeHtml(i18n.status(item.value))}</option>`).join("");
  $("#status-select").innerHTML = options;
  $("#import-status").innerHTML = options;
  $("#batch-status-select").innerHTML = options;
  $("#parcel-status-filter").innerHTML = `<option value="">${tr("Все статусы")}</option>${options}`;
  $("#parcel-status-filter").value = state.statusFilter;
  $("#import-status").value = "IN_TRANSIT";
  $("#transit-days").value = state.defaultTransitDays;
  $("#batch-transit-days").value = state.defaultTransitDays;
  $("#picker-status-value").textContent = state.statusFilter
    ? i18n.status(state.statusFilter)
    : tr("Все статусы");
  $("#picker-sort-value").textContent = $("#parcel-sort").value === "tracking"
    ? tr("По трек-коду")
    : tr("Сначала обновлённые");
}

function pickerItems(name) {
  if (name === "status") {
    return [{ value: "", label: tr("Все статусы") }, ...state.statuses.map((item) => ({ ...item, label: i18n.status(item.value) }))];
  }
  return [
    { value: "recent", label: tr("Сначала обновлённые") },
    { value: "tracking", label: tr("По трек-коду") },
  ];
}

function setPickerExpanded(name = null) {
  $$('[data-open-picker]').forEach((button) => {
    const expanded = button.dataset.openPicker === name;
    button.classList.toggle("expanded", expanded);
    button.setAttribute("aria-expanded", String(expanded));
  });
}

function openPicker(name) {
  state.activePicker = name;
  setPickerExpanded(name);
  const select = name === "status" ? $("#parcel-status-filter") : $("#parcel-sort");
  $("#picker-title").textContent = name === "status" ? tr("Выберите статус") : tr("Сортировать товары");
  $("#picker-options").innerHTML = pickerItems(name).map((item) => `
    <button class="picker-option${item.value === select.value ? " selected" : ""}" type="button" data-picker-value="${escapeHtml(item.value)}">
      <span class="picker-label">${escapeHtml(statusText(item.label))}</span><span class="picker-radio" aria-hidden="true"><i data-lucide="check"></i></span>
    </button>`).join("");
  refreshIcons();
  $("#picker-sheet").showModal();
}

async function choosePickerValue(value) {
  const name = state.activePicker;
  const select = name === "status" ? $("#parcel-status-filter") : $("#parcel-sort");
  const item = pickerItems(name).find((candidate) => candidate.value === value);
  if (!item) return;
  select.value = value;
  $(name === "status" ? "#picker-status-value" : "#picker-sort-value").textContent = item.label;
  $("#picker-sheet").close();
  if (name === "status") {
    state.statusFilter = value;
    await loadParcels();
  } else {
    renderParcels();
  }
}

async function loadDashboard() {
  const data = state.demo ? demo.dashboard : await api("/api/dashboard");
  renderDashboard(data);
}

async function loadParcels() {
  if (state.demo) {
    const query = $("#parcel-search").value.trim().toLowerCase();
    state.parcels = demo.parcels.filter((parcel) =>
      (!state.statusFilter || parcel.status === state.statusFilter)
      && (!query || `${parcel.tracking_number} ${parcel.client_code}`.toLowerCase().includes(query)));
  } else {
    const query = encodeURIComponent($("#parcel-search").value.trim());
    const statusQuery = state.statusFilter ? `&parcel_status=${state.statusFilter}` : "";
    state.parcels = await api(`/api/parcels?query=${query}${statusQuery}`);
  }
  renderParcels();
}

async function loadClients() {
  if (state.demo) {
    const query = $("#client-search").value.trim().toLowerCase();
    state.clients = demo.clients.filter((client) =>
      `${client.full_name} ${client.client_code} ${client.phone}`.toLowerCase().includes(query));
  } else {
    state.clients = await api(`/api/clients?query=${encodeURIComponent($("#client-search").value.trim())}`);
  }
  renderClients();
}

async function loadImports() {
  state.imports = state.demo ? demo.imports : await api("/api/imports");
  renderImports();
}

async function loadSettings() {
  const values = state.demo ? state.settings || demo.settings : await api("/api/settings");
  renderSettings(values);
}

async function loadView(name) {
  try {
    if (name === "dashboard") {
      if (!state.parcels.length) await loadParcels();
      await loadDashboard();
    } else if (name === "parcels") await loadParcels();
    else if (name === "clients") await loadClients();
    else if (name === "imports") await loadImports();
    else if (name === "settings") await loadSettings();
  } catch (error) {
    toast(error.message, true);
  }
}

function connectEvents() {
  if (state.demo) return;
  const events = new EventSource("/api/events");
  events.addEventListener("change", () => {
    clearTimeout(state.reloadTimer);
    state.reloadTimer = setTimeout(async () => {
      await loadParcels();
      await loadDashboard();
      if (state.currentView === "clients") await loadClients();
      if (state.currentView === "imports") await loadImports();
      if (state.currentView === "settings") await loadSettings();
    }, 250);
  });
  events.onopen = () => {
    $("#live-pill").classList.remove("offline");
    $("#live-pill b").textContent = tr("Онлайн");
  };
  events.onerror = () => {
    $("#live-pill").classList.add("offline");
    $("#live-pill b").textContent = tr("Нет связи");
  };
}

function refreshLanguage() {
  i18n.applyStatic();
  $("#page-title").textContent = tr(pageTitles[state.currentView] || "Панель");
  $("#live-pill b").textContent = tr($("#live-pill").classList.contains("offline") ? "Нет связи" : "Онлайн");
  if (state.statuses.length) buildStatusControls();
  if (state.parcels.length || state.currentView === "parcels") renderParcels();
  if (state.clients.length || state.currentView === "clients") renderClients();
  if (state.imports.length || state.currentView === "imports") renderImports();
  if (state.currentView === "dashboard") loadDashboard();
  if ($("#client-detail-sheet").open && state.selectedClient) {
    closeDialog("client-detail-sheet");
    openClientDetail(state.selectedClient.id);
  }
  if ($("#batch-status-sheet").open && state.selectedImport) {
    closeDialog("batch-status-sheet");
    openBatchStatus(state.selectedImport.id);
  }
}

async function authenticate() {
  tg?.ready();
  tg?.expand();
  const preview = new URLSearchParams(location.search).get("preview") === "1";
  const localPreview = ["localhost", "127.0.0.1"].includes(location.hostname);
  if (!tg?.initData && localPreview && preview) {
    state.demo = true;
    state.authenticated = true;
    state.statuses = demo.statuses;
    state.defaultTransitDays = 12;
    state.settings = demo.settings;
    $("#company-name").textContent = demo.settings.company_name;
    buildStatusControls();
    await loadParcels();
    showView("dashboard");
    return;
  }
  if (!tg?.initData) {
    showView("auth");
    return;
  }
  try {
    await api("/api/auth/telegram", { method: "POST", body: JSON.stringify({ init_data: tg.initData }) });
    state.authenticated = true;
    const meta = await api("/api/meta");
    state.statuses = meta.statuses;
    state.defaultTransitDays = meta.default_transit_days;
    $("#company-name").textContent = meta.company;
    buildStatusControls();
    await loadParcels();
    showView("dashboard");
    connectEvents();
  } catch (error) {
    showView("auth");
    toast(error.message, true);
  }
}

document.addEventListener("click", async (event) => {
  const closeButton = event.target.closest("[data-close-dialog]");
  if (closeButton) closeDialog(closeButton.dataset.closeDialog);

  const pickerTrigger = event.target.closest("[data-open-picker]");
  if (pickerTrigger) openPicker(pickerTrigger.dataset.openPicker);

  const pickerOption = event.target.closest("[data-picker-value]");
  if (pickerOption) await choosePickerValue(pickerOption.dataset.pickerValue);

  const nav = event.target.closest("[data-nav], [data-open-view]");
  if (nav) showView(nav.dataset.nav || nav.dataset.openView);

  const edit = event.target.closest("[data-edit-parcel]");
  if (edit) {
    state.selectedParcel = state.parcels.find((parcel) => parcel.id === Number(edit.dataset.editParcel));
    $("#status-track").textContent = `${state.selectedParcel.tracking_number} · ${state.selectedParcel.client_code}`;
    $("#parcel-client-code").value = state.selectedParcel.client_code;
    $("#status-select").value = state.selectedParcel.status;
    $("#parcel-sent-date").value = state.selectedParcel.sent_date || "";
    $("#parcel-expected-date").value = state.selectedParcel.expected_date || "";
    $("#status-sheet").showModal();
  }

  const clientButton = event.target.closest("[data-manage-client]");
  if (clientButton) openClientDetail(clientButton.dataset.manageClient);

  const importButton = event.target.closest("[data-edit-import]");
  if (importButton) openBatchStatus(importButton.dataset.editImport);

  const arrived = event.target.closest("[data-arrive-import]");
  const arriveConfirmation = i18n.language === "en" ? "Has the truck arrived? Clients will be notified." : i18n.language === "zh" ? "确认车辆已经到达吗？客户将收到通知。" : "Машина действительно прибыла? Клиенты получат уведомления.";
  if (arrived && confirm(arriveConfirmation)) {
    if (state.demo) return toast(tr("Демо: партия отмечена прибывшей"));
    try {
      const result = await api(`/api/imports/${arrived.dataset.arriveImport}/arrived`, { method: "POST" });
      toast(i18n.language === "en" ? `Shipments updated: ${result.updated}. Notifications: ${result.notifications}` : i18n.language === "zh" ? `已更新货物：${result.updated}。通知：${result.notifications}` : `Обновлено товаров: ${result.updated}. Уведомлений: ${result.notifications}`);
      await Promise.all([loadImports(), loadParcels(), loadDashboard()]);
    } catch (error) { toast(error.message, true); }
  }
});

$("#picker-sheet").addEventListener("close", () => {
  setPickerExpanded();
  state.activePicker = null;
});

$("#menu-toggle").addEventListener("click", () => {
  if ($("#drawer").classList.contains("open")) closeDrawer(); else openDrawer();
});
$("#drawer-backdrop").addEventListener("click", closeDrawer);
document.addEventListener("keydown", (event) => { if (event.key === "Escape") closeDrawer(); });
document.addEventListener("keydown", (event) => {
  const importRowElement = event.target.closest?.(".import-row[data-edit-import]");
  if (importRowElement && event.target === importRowElement && ["Enter", " "].includes(event.key)) {
    event.preventDefault();
    openBatchStatus(importRowElement.dataset.editImport);
  }
});

$("#parcel-status-filter").addEventListener("change", async (event) => {
  state.statusFilter = event.target.value;
  await loadParcels();
});
$("#parcel-sort").addEventListener("change", renderParcels);

$("#parcel-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!state.selectedParcel) return;
  const selectedParcel = state.selectedParcel;
  const payload = {
    client_code: $("#parcel-client-code").value.trim(),
    status: $("#status-select").value,
    sent_date: $("#parcel-sent-date").value || null,
    expected_date: $("#parcel-expected-date").value || null,
  };
  const button = event.target.querySelector("[type=submit]");
  button.disabled = true;
  if (state.demo) {
    const status = state.statuses.find((item) => item.value === payload.status);
    Object.assign(selectedParcel, payload, {
      status_label: status?.label || payload.status,
      sent_at: payload.sent_date,
      expected_at: payload.expected_date,
    });
    closeDialog("status-sheet");
    renderParcels();
    button.disabled = false;
    return toast(tr("Демо: статус обновлён"));
  }
  try {
    const result = await api(`/api/parcels/${selectedParcel.id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
    Object.assign(selectedParcel, result.parcel);
    closeDialog("status-sheet");
    toast(tr(result.notified ? "Товар обновлён, клиент уведомлён" : "Товар обновлён"));
    await Promise.all([loadParcels(), loadDashboard()]);
  } catch (error) { toast(error.message, true); }
  finally { button.disabled = false; }
});

$("#delete-parcel").addEventListener("click", async () => {
  const parcel = state.selectedParcel;
  if (!parcel) return;
  const confirmation = i18n.language === "en"
    ? `Delete shipment ${parcel.tracking_number}? This action cannot be undone.`
    : i18n.language === "zh"
      ? `确定删除货物 ${parcel.tracking_number} 吗？此操作无法撤销。`
      : `Удалить товар ${parcel.tracking_number}? Это действие нельзя отменить.`;
  if (!confirm(confirmation)) return;
  try {
    if (!state.demo) await api(`/api/parcels/${parcel.id}`, { method: "DELETE" });
    state.parcels = state.parcels.filter((item) => item.id !== parcel.id);
    closeDialog("status-sheet");
    renderParcels();
    toast(tr("Товар удалён"));
    await loadDashboard();
  } catch (error) { toast(error.message, true); }
});

$("#batch-status-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!state.selectedImport) return;
  const importRecord = state.selectedImport;
  const statusValue = $("#batch-status-select").value;
  const payload = {
    status: statusValue,
    sent_date: $("#batch-sent-date").value || null,
    expected_date: $("#batch-expected-date").value || null,
    transit_days: Number($("#batch-transit-days").value || state.defaultTransitDays),
  };
  closeDialog("batch-status-sheet");
  if (state.demo) {
    const status = state.statuses.find((item) => item.value === statusValue);
    importRecord.status = statusValue;
    importRecord.status_label = status?.label || statusValue;
    importRecord.sent_date = payload.sent_date;
    importRecord.expected_date = payload.expected_date;
    importRecord.sent_at = payload.sent_date;
    importRecord.expected_at = payload.expected_date;
    renderImports();
    return toast(tr("Демо: статус всей партии обновлён"));
  }
  try {
    const result = await api(`/api/imports/${importRecord.id}/status`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
    toast(i18n.language === "en" ? `Shipments updated: ${result.updated}. Notifications: ${result.notifications}` : i18n.language === "zh" ? `已更新货物：${result.updated}。通知：${result.notifications}` : `Обновлено товаров: ${result.updated}. Уведомлений: ${result.notifications}`);
    await Promise.all([loadImports(), loadParcels(), loadDashboard()]);
  } catch (error) { toast(error.message, true); }
});

$("#open-client-create").addEventListener("click", () => openClientForm());
$("#client-edit-action").addEventListener("click", () => {
  const client = state.selectedClient;
  closeDialog("client-detail-sheet");
  openClientForm(client);
});
$("#client-parcels-action").addEventListener("click", async () => {
  const client = state.selectedClient;
  if (!client) return;
  closeDialog("client-detail-sheet");
  try {
    const parcels = state.demo
      ? demo.parcels.filter((parcel) => parcel.client_code === client.client_code)
      : await api(`/api/clients/${client.id}/parcels`);
    renderClientParcels(client, parcels);
    $("#client-parcels-sheet").showModal();
  } catch (error) { toast(error.message, true); }
});
$("#client-admin-action").addEventListener("click", async () => {
  const client = state.selectedClient;
  if (!client || client.is_system_admin) return;
  const nextValue = !client.is_admin;
  const confirmation = i18n.language === "en"
    ? `${nextValue ? "Grant" : "Revoke"} administrator access for ${client.full_name}?`
    : i18n.language === "zh"
      ? `确定要${nextValue ? "授予" : "撤销"} ${client.full_name} 的管理员权限吗？`
      : `${nextValue ? "Выдать" : "Отозвать"} админ-доступ для ${client.full_name}?`;
  if (!confirm(confirmation)) return;
  try {
    if (state.demo) {
      client.is_admin = nextValue;
    } else {
      const updated = await api(`/api/clients/${client.id}/admin`, {
        method: "POST",
        body: JSON.stringify({ is_admin: nextValue }),
      });
      Object.assign(client, updated);
    }
    renderClients();
    closeDialog("client-detail-sheet");
    openClientDetail(client.id);
    toast(tr(nextValue ? "Админ-доступ выдан" : "Админ-доступ отозван"));
  } catch (error) { toast(error.message, true); }
});
$("#client-block-action").addEventListener("click", () => {
  if (!state.selectedClient) return;
  closeDialog("client-detail-sheet");
  $("#client-block-title").textContent = state.selectedClient.full_name;
  $("#client-block-mode").value = state.selectedClient.is_blocked ? "unblock" : "temporary";
  $("#client-block-days-field").hidden = $("#client-block-mode").value !== "temporary";
  $("#client-block-sheet").showModal();
});
$("#client-block-mode").addEventListener("change", (event) => {
  $("#client-block-days-field").hidden = event.target.value !== "temporary";
});
$("#client-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const clientId = Number($("#client-form-id").value) || null;
  const telegramId = $("#client-form-telegram").value.trim();
  const payload = {
    full_name: $("#client-form-name").value.trim(),
    phone: $("#client-form-phone").value.trim(),
    city: $("#client-form-city").value.trim() || null,
    telegram_id: telegramId ? Number(telegramId) : null,
  };
  if (!clientId) payload.client_code = $("#client-form-code").value.trim() || null;
  const button = event.target.querySelector("[type=submit]");
  button.disabled = true;
  try {
    if (state.demo) {
      if (clientId) Object.assign(state.selectedClient, payload);
      else state.clients.unshift({
        ...payload,
        id: Date.now(),
        client_code: payload.client_code || `J-${String(state.clients.length + 1).padStart(4, "0")}`,
        parcels: 0,
        is_active: true,
        is_blocked: false,
        block_mode: null,
        blocked_until_text: null,
      });
    } else {
      await api(clientId ? `/api/clients/${clientId}` : "/api/clients", {
        method: clientId ? "PATCH" : "POST",
        body: JSON.stringify(payload),
      });
      await loadClients();
    }
    closeDialog("client-form-sheet");
    renderClients();
    toast(tr(clientId ? "Данные клиента обновлены" : "Клиент добавлен"));
  } catch (error) { toast(error.message, true); }
  finally { button.disabled = false; }
});
$("#client-block-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!state.selectedClient) return;
  const client = state.selectedClient;
  const mode = $("#client-block-mode").value;
  const payload = { mode, days: Number($("#client-block-days").value) };
  const button = event.target.querySelector("[type=submit]");
  button.disabled = true;
  try {
    if (state.demo) {
      client.is_blocked = mode !== "unblock";
      client.is_active = mode !== "permanent";
      client.block_mode = mode === "unblock" ? null : mode;
      client.blocked_until_text = mode === "temporary" ? `через ${payload.days} дн.` : null;
    } else {
      const updated = await api(`/api/clients/${client.id}/block`, {
        method: "POST",
        body: JSON.stringify(payload),
      });
      Object.assign(client, updated);
    }
    closeDialog("client-block-sheet");
    renderClients();
    toast(tr(mode === "unblock" ? "Клиент разблокирован" : "Ограничение применено"));
  } catch (error) { toast(error.message, true); }
  finally { button.disabled = false; }
});

function openImportDialog() { $("#import-sheet").showModal(); }
$("#open-import").addEventListener("click", openImportDialog);
$("#cancel-import").addEventListener("click", () => $("#import-sheet").close());
$("#excel-file").addEventListener("change", (event) => {
  $("#file-name").textContent = event.target.files[0]?.name || tr(".xls или .xlsx, до 20 МБ");
});
$("#import-status").addEventListener("change", (event) => {
  $("#transit-fields").hidden = event.target.value !== "IN_TRANSIT";
});
$("#import-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (state.demo) {
    $("#import-sheet").close();
    return toast(tr("Демо: Excel обработан"));
  }
  const button = event.target.querySelector("[type=submit]");
  button.disabled = true;
  button.textContent = tr("Обрабатываю…");
  try {
    const result = await api("/api/imports", { method: "POST", body: new FormData(event.target) });
    $("#import-sheet").close();
    event.target.reset();
    $("#file-name").textContent = tr(".xls или .xlsx, до 20 МБ");
    toast(i18n.language === "en" ? `New: ${result.created}, updated: ${result.updated}` : i18n.language === "zh" ? `新增：${result.created}，更新：${result.updated}` : `Новых: ${result.created}, обновлено: ${result.updated}`);
    await Promise.all([loadImports(), loadParcels(), loadDashboard()]);
  } catch (error) { toast(error.message, true); }
  finally { button.disabled = false; button.textContent = tr("Импортировать"); }
});

$("#settings-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const values = Object.fromEntries(new FormData(event.target).entries());
  values.default_transit_days = Number(values.default_transit_days);
  if (state.demo) {
    state.settings = values;
    $("#company-name").textContent = values.company_name;
    return toast(tr("Демо: настройки сохранены"));
  }
  const button = event.target.querySelector("[type=submit]");
  button.disabled = true;
  try {
    const result = await api("/api/settings", { method: "PATCH", body: JSON.stringify(values) });
    state.settings = result;
    state.defaultTransitDays = result.default_transit_days;
    $("#company-name").textContent = result.company_name;
    $("#transit-days").value = result.default_transit_days;
    toast(tr("Настройки сохранены"));
  } catch (error) { toast(error.message, true); }
  finally { button.disabled = false; }
});

$("#floating-action").addEventListener("click", () => {
  if (state.currentView === "imports") openImportDialog();
  else if (state.currentView === "clients") openClientForm();
});

let parcelTimer;
$("#parcel-search").addEventListener("input", () => {
  clearTimeout(parcelTimer);
  parcelTimer = setTimeout(loadParcels, 300);
});
let clientTimer;
$("#client-search").addEventListener("input", () => {
  clearTimeout(clientTimer);
  clientTimer = setTimeout(loadClients, 300);
});
$("#refresh-parcels").addEventListener("click", loadParcels);
$("#refresh-clients").addEventListener("click", loadClients);
$("#retry-auth").addEventListener("click", authenticate);
$("#language-select").addEventListener("change", (event) => {
  i18n.setLanguage(event.target.value);
  refreshLanguage();
});

const demo = {
  statuses: [
    { value: "CHINA_WAREHOUSE", label: "🇨🇳 На складе в Китае" },
    { value: "PREPARING", label: "📦 Готовится к отправке" },
    { value: "IN_TRANSIT", label: "🚚 В пути" },
    { value: "ARRIVED_COUNTRY", label: "🏢 Прибыл" },
    { value: "LOCAL_WAREHOUSE", label: "🏢 На местном складе" },
    { value: "READY_FOR_PICKUP", label: "✅ Готов к выдаче" },
    { value: "DELIVERED", label: "📬 Получен" },
    { value: "CANCELLED", label: "❌ Отменён" },
  ],
  dashboard: {
    total_clients: 86,
    linked_clients: 64,
    total_parcels: 312,
    in_transit: 148,
    arrived: 27,
    status_counts: { CHINA_WAREHOUSE: 69, PREPARING: 38, IN_TRANSIT: 148, ARRIVED_COUNTRY: 27, READY_FOR_PICKUP: 18, DELIVERED: 12 },
  },
  parcels: [
    { id: 1, tracking_number: "78999695208956", client_code: "J-8226", client_name: "Султанов Азим", status: "IN_TRANSIT", status_label: "🚚 В пути", sent_at: "20.08.2026", expected_at: "01.09.2026", sent_date: "2026-08-20", expected_date: "2026-09-01" },
    { id: 2, tracking_number: "YT7592444294461", client_code: "J-0329", client_name: "Айжан Иманова", status: "CHINA_WAREHOUSE", status_label: "🇨🇳 На складе в Китае", sent_at: null, expected_at: null },
    { id: 3, tracking_number: "9812328869266", client_code: "J-4040", client_name: "Эльдар Каримов", status: "ARRIVED_COUNTRY", status_label: "🏢 Прибыл", sent_at: "08.08.2026", expected_at: "20.08.2026" },
    { id: 4, tracking_number: "SF604118237991", client_code: "J-1190", client_name: "Нурбек Алиев", status: "PREPARING", status_label: "📦 Готовится к отправке", sent_at: null, expected_at: null },
  ],
  clients: [
    { id: 1, client_code: "J-8226", full_name: "Султанов Азим", phone: "+996 555 123 456", city: "Бишкек", telegram_id: 1, parcels: 7, is_active: true, is_blocked: false, block_mode: null, blocked_until_text: null },
    { id: 2, client_code: "J-0329", full_name: "Айжан Иманова", phone: "+996 700 987 654", city: "Ош", telegram_id: 2, parcels: 3, is_active: true, is_blocked: true, block_mode: "temporary", blocked_until_text: "24.08.2026 12:00" },
    { id: 3, client_code: "J-4040", full_name: "Эльдар Каримов", phone: "+996 777 400 400", city: null, telegram_id: null, parcels: 5, is_active: true, is_blocked: false, block_mode: null, blocked_until_text: null },
  ],
  imports: [
    { id: 18, filename: "cargo-20-08.xlsx", status: "IN_TRANSIT", status_label: "🚚 В пути", sent_at: "20.08.2026", expected_at: "01.09.2026", sent_date: "2026-08-20", expected_date: "2026-09-01", created_rows: 48, updated_rows: 7 },
    { id: 17, filename: "china-warehouse.xls", status: "CHINA_WAREHOUSE", status_label: "🇨🇳 На складе в Китае", sent_at: null, expected_at: null, created_rows: 64, updated_rows: 2 },
  ],
  settings: {
    company_name: "BCL EXPRESS",
    default_transit_days: 12,
    warehouse_receiver: "王国利 J-8226",
    warehouse_phone: "18818913136",
    warehouse_address: "广东省广州市荔湾区站前路流花新街16号136",
    warehouse_name: "BCL库房",
    support_username: "@bcl_support",
  },
};

refreshIcons();
authenticate();
