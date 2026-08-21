const tg = window.Telegram?.WebApp;

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
    throw new Error(data.detail || "Не удалось выполнить действие");
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
  $("#page-title").textContent = pageTitles[name] || "Панель";
  $("#floating-action").hidden = name === "auth" || name === "settings";
  closeDrawer();
  if (name !== "auth") loadView(name);
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function empty(message) {
  return `<div class="empty-state">${escapeHtml(message)}</div>`;
}

function parcelRow(parcel, actions = true) {
  return `
    <article class="table-row">
      <div><strong>${escapeHtml(parcel.tracking_number)}</strong><small>${parcel.expected_at ? `Ожидается ${escapeHtml(parcel.expected_at)}` : "Дата не указана"}</small></div>
      <div><span class="table-cell-code">${escapeHtml(parcel.client_code)}</span><small>${escapeHtml(parcel.client_name || "Клиент не привязан")}</small></div>
      <div><span class="status-badge">${escapeHtml(parcel.status_label)}</span>${actions ? `<button class="row-action" data-edit-parcel="${parcel.id}">Изменить статус</button>` : ""}</div>
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
  const total = Math.max(1, data.total_parcels);
  const labels = Object.fromEntries(state.statuses.map((item) => [item.value, item.label]));
  labels.OTHER = "Остальные статусы";
  $("#status-summary").innerHTML = Object.entries(statusCounts)
    .filter(([, count]) => count > 0)
    .map(([value, count]) => `
      <div class="status-line">
        <div><span>${escapeHtml(labels[value] || value)}</span><b>${count}</b></div>
        <span class="status-track"><i style="width:${Math.max(3, Math.round(count / total * 100))}%"></i></span>
      </div>`).join("") || empty("Статистика появится после загрузки товаров");

  const recent = state.parcels.slice(0, 5);
  $("#recent-parcels").innerHTML = recent.length
    ? recent.map((parcel) => parcelRow(parcel, false)).join("")
    : empty("Товаров пока нет");
}

function sortedParcels() {
  const rows = [...state.parcels];
  if ($("#parcel-sort").value === "tracking") {
    rows.sort((a, b) => a.tracking_number.localeCompare(b.tracking_number, "ru"));
  }
  return rows;
}

function renderParcels() {
  const rows = sortedParcels();
  $("#parcel-summary").innerHTML = `Показано товаров: <b>${rows.length}</b>${state.statusFilter ? " · применён фильтр по статусу" : " · все статусы"}`;
  $("#parcel-list").innerHTML = rows.length
    ? rows.map((parcel) => parcelRow(parcel)).join("")
    : empty("По этому запросу товары не найдены");
}

function renderClients() {
  $("#client-list").innerHTML = state.clients.length
    ? state.clients.map((client) => `
      <article class="table-row">
        <div><strong>${escapeHtml(client.full_name)}</strong><small>${escapeHtml(client.phone)} · ${client.telegram_id ? "Telegram привязан" : "Telegram не привязан"}</small></div>
        <div><span class="table-cell-code">${escapeHtml(client.client_code)}</span></div>
        <div><b>${client.parcels}</b><small>товаров</small></div>
      </article>`).join("")
    : empty("Клиенты не найдены");
}

function importRow(item) {
  const canArrive = item.status === "IN_TRANSIT";
  return `
    <article class="table-row">
      <div><strong>${escapeHtml(item.filename)}</strong><small>Партия №${item.id} · ${escapeHtml(item.status_label)}</small></div>
      <div>${item.sent_at ? `<span>${escapeHtml(item.sent_at)}</span>` : "—"}<small>${item.expected_at ? `Ожидается ${escapeHtml(item.expected_at)}` : "Без расчётной даты"}</small></div>
      <div><b>+${item.created_rows}</b> / ${item.updated_rows}<small>новых / обновлено</small>${canArrive ? `<button class="row-action" data-arrive-import="${item.id}">Партия прибыла</button>` : ""}</div>
    </article>`;
}

function renderImports() {
  $("#import-list").innerHTML = state.imports.length
    ? state.imports.map(importRow).join("")
    : empty("Импортов пока нет");
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
  const options = state.statuses.map((item) => `<option value="${item.value}">${escapeHtml(item.label)}</option>`).join("");
  $("#status-select").innerHTML = options;
  $("#import-status").innerHTML = options;
  $("#parcel-status-filter").innerHTML = `<option value="">Все статусы</option>${options}`;
  $("#import-status").value = "IN_TRANSIT";
  $("#transit-days").value = state.defaultTransitDays;
  $("#picker-status-value").textContent = "Все статусы";
}

function pickerItems(name) {
  if (name === "status") {
    return [{ value: "", label: "Все статусы" }, ...state.statuses];
  }
  return [
    { value: "recent", label: "Сначала обновлённые" },
    { value: "tracking", label: "По трек-коду" },
  ];
}

function openPicker(name) {
  state.activePicker = name;
  const select = name === "status" ? $("#parcel-status-filter") : $("#parcel-sort");
  $("#picker-title").textContent = name === "status" ? "Выберите статус" : "Сортировать товары";
  $("#picker-options").innerHTML = pickerItems(name).map((item) => `
    <button class="picker-option${item.value === select.value ? " selected" : ""}" type="button" data-picker-value="${escapeHtml(item.value)}">
      <span>${escapeHtml(item.label)}</span><i>✓</i>
    </button>`).join("");
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
    $("#live-pill b").textContent = "Онлайн";
  };
  events.onerror = () => {
    $("#live-pill").classList.add("offline");
    $("#live-pill b").textContent = "Нет связи";
  };
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
    $("#status-select").value = state.selectedParcel.status;
    $("#status-sheet").showModal();
  }

  const arrived = event.target.closest("[data-arrive-import]");
  if (arrived && confirm("Машина действительно прибыла? Клиенты получат уведомления.")) {
    if (state.demo) return toast("Демо: партия отмечена прибывшей");
    try {
      const result = await api(`/api/imports/${arrived.dataset.arriveImport}/arrived`, { method: "POST" });
      toast(`Обновлено товаров: ${result.updated}. Уведомлений: ${result.notifications}`);
      await Promise.all([loadImports(), loadParcels(), loadDashboard()]);
    } catch (error) { toast(error.message, true); }
  }
});

$("#menu-toggle").addEventListener("click", () => {
  if ($("#drawer").classList.contains("open")) closeDrawer(); else openDrawer();
});
$("#drawer-backdrop").addEventListener("click", closeDrawer);
document.addEventListener("keydown", (event) => { if (event.key === "Escape") closeDrawer(); });

$("#parcel-status-filter").addEventListener("change", async (event) => {
  state.statusFilter = event.target.value;
  await loadParcels();
});
$("#parcel-sort").addEventListener("change", renderParcels);

$("#save-status").addEventListener("click", async () => {
  if (!state.selectedParcel) return;
  if (state.demo) {
    $("#status-sheet").close();
    return toast("Демо: статус обновлён");
  }
  try {
    const result = await api(`/api/parcels/${state.selectedParcel.id}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status: $("#status-select").value }),
    });
    $("#status-sheet").close();
    toast(result.notified ? "Статус обновлён, клиент уведомлён" : "Статус обновлён");
    await Promise.all([loadParcels(), loadDashboard()]);
  } catch (error) { toast(error.message, true); }
});

function openImportDialog() { $("#import-sheet").showModal(); }
$("#open-import").addEventListener("click", openImportDialog);
$("#cancel-import").addEventListener("click", () => $("#import-sheet").close());
$("#excel-file").addEventListener("change", (event) => {
  $("#file-name").textContent = event.target.files[0]?.name || ".xls или .xlsx, до 20 МБ";
});
$("#import-status").addEventListener("change", (event) => {
  $("#transit-fields").hidden = event.target.value !== "IN_TRANSIT";
});
$("#import-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (state.demo) {
    $("#import-sheet").close();
    return toast("Демо: Excel обработан");
  }
  const button = event.target.querySelector("[type=submit]");
  button.disabled = true;
  button.textContent = "Обрабатываю…";
  try {
    const result = await api("/api/imports", { method: "POST", body: new FormData(event.target) });
    $("#import-sheet").close();
    event.target.reset();
    $("#file-name").textContent = ".xls или .xlsx, до 20 МБ";
    toast(`Новых: ${result.created}, обновлено: ${result.updated}`);
    await Promise.all([loadImports(), loadParcels(), loadDashboard()]);
  } catch (error) { toast(error.message, true); }
  finally { button.disabled = false; button.textContent = "Импортировать"; }
});

$("#settings-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const values = Object.fromEntries(new FormData(event.target).entries());
  values.default_transit_days = Number(values.default_transit_days);
  if (state.demo) {
    state.settings = values;
    $("#company-name").textContent = values.company_name;
    return toast("Демо: настройки сохранены");
  }
  const button = event.target.querySelector("[type=submit]");
  button.disabled = true;
  try {
    const result = await api("/api/settings", { method: "PATCH", body: JSON.stringify(values) });
    state.settings = result;
    state.defaultTransitDays = result.default_transit_days;
    $("#company-name").textContent = result.company_name;
    $("#transit-days").value = result.default_transit_days;
    toast("Настройки сохранены");
  } catch (error) { toast(error.message, true); }
  finally { button.disabled = false; }
});

$("#floating-action").addEventListener("click", () => {
  if (["dashboard", "imports"].includes(state.currentView)) openImportDialog();
  else if (state.currentView === "parcels") $("#parcel-search").focus();
  else if (state.currentView === "clients") $("#client-search").focus();
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

const demo = {
  statuses: [
    { value: "CHINA_WAREHOUSE", label: "🇨🇳 На складе в Китае" },
    { value: "PREPARING", label: "📦 Готовится к отправке" },
    { value: "IN_TRANSIT", label: "🚚 В пути" },
    { value: "ARRIVED_COUNTRY", label: "🏢 Прибыл" },
    { value: "READY_FOR_PICKUP", label: "✅ Готов к выдаче" },
    { value: "DELIVERED", label: "📬 Получен" },
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
    { id: 1, tracking_number: "78999695208956", client_code: "J-8226", client_name: "Султанов Азим", status: "IN_TRANSIT", status_label: "🚚 В пути", sent_at: "20.08.2026", expected_at: "01.09.2026" },
    { id: 2, tracking_number: "YT7592444294461", client_code: "J-0329", client_name: "Айжан Иманова", status: "CHINA_WAREHOUSE", status_label: "🇨🇳 На складе в Китае", sent_at: null, expected_at: null },
    { id: 3, tracking_number: "9812328869266", client_code: "J-4040", client_name: "Эльдар Каримов", status: "ARRIVED_COUNTRY", status_label: "🏢 Прибыл", sent_at: "08.08.2026", expected_at: "20.08.2026" },
    { id: 4, tracking_number: "SF604118237991", client_code: "J-1190", client_name: "Нурбек Алиев", status: "PREPARING", status_label: "📦 Готовится к отправке", sent_at: null, expected_at: null },
  ],
  clients: [
    { id: 1, client_code: "J-8226", full_name: "Султанов Азим", phone: "+996 555 123 456", telegram_id: 1, parcels: 7 },
    { id: 2, client_code: "J-0329", full_name: "Айжан Иманова", phone: "+996 700 987 654", telegram_id: 2, parcels: 3 },
    { id: 3, client_code: "J-4040", full_name: "Эльдар Каримов", phone: "+996 777 400 400", telegram_id: null, parcels: 5 },
  ],
  imports: [
    { id: 18, filename: "cargo-20-08.xlsx", status: "IN_TRANSIT", status_label: "🚚 В пути", sent_at: "20.08.2026", expected_at: "01.09.2026", created_rows: 48, updated_rows: 7 },
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

authenticate();
