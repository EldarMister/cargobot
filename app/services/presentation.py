from collections import defaultdict
from datetime import datetime
from html import escape

from app.core.dates import as_local, local_timezone
from app.core.enums import ParcelStatus
from app.db.models import Parcel


def pluralize_days(days: int) -> str:
    remainder_100 = days % 100
    remainder_10 = days % 10
    if remainder_10 == 1 and remainder_100 != 11:
        word = "день"
    elif remainder_10 in {2, 3, 4} and remainder_100 not in {12, 13, 14}:
        word = "дня"
    else:
        word = "дней"
    return f"{days} {word}"


def remaining_arrival_text(expected_at: datetime, today=None) -> str:
    expected = as_local(expected_at).date()
    current_date = today or datetime.now(local_timezone()).date()
    remaining = (expected - current_date).days
    if remaining > 0:
        return f"⌛ Осталось примерно: {pluralize_days(remaining)}"
    if remaining == 0:
        return "🗓 Ожидается сегодня"
    return "🗓 Ожидаемая дата прибытия уже наступила"


def format_parcel(parcel: Parcel) -> str:
    lines = [f"📦 <code>{parcel.tracking_number}</code>"]
    if parcel.sent_at:
        lines.append(f"📅 Выехал: {as_local(parcel.sent_at):%d.%m.%Y}")
    if parcel.expected_at:
        expected = as_local(parcel.expected_at)
        lines.append(f"🗓 Примерно приедет: {expected:%d.%m.%Y}")
        if parcel.status not in {ParcelStatus.DELIVERED, ParcelStatus.CANCELLED}:
            lines.append(remaining_arrival_text(parcel.expected_at))
    return "\n".join(lines)


def format_parcel_list(
    parcels: list[Parcel],
    *,
    title: str = "📦 Мои товары",
    empty_message: str = "У вас пока нет зарегистрированных товаров.",
) -> str:
    if not parcels:
        return empty_message
    grouped = defaultdict(list)
    for parcel in parcels:
        grouped[parcel.status].append(parcel)
    lines = [f"<b>{escape(title)}</b>"]
    for group_number, (status, items) in enumerate(grouped.items()):
        if group_number:
            lines.extend(["", "────────────"])
        lines.extend(["", f"<b>{status.label}:</b>", ""])
        lines.append("\n\n────────────\n\n".join(format_parcel(parcel) for parcel in items))
    lines.extend(["", f"📊 Всего товаров: {len(parcels)}"])
    return "\n".join(lines)


def warehouse_text(settings: dict[str, str], client_code: str) -> str:
    receiver = " ".join(part for part in [settings.get("warehouse_receiver", ""), client_code] if part)
    warehouse = " ".join(part for part in [settings.get("warehouse_name", ""), client_code] if part)
    return (
        "📦 <b>Адрес склада в Китае</b>\n\n"
        f"Получатель: {escape(receiver) if receiver else 'не указан'}\n"
        f"Телефон: {escape(settings.get('warehouse_phone', '')) or 'не указан'}\n"
        f"Адрес: {escape(settings.get('warehouse_address', '')) or 'не указан'}\n"
        f"Склад: {escape(warehouse) if warehouse else 'не указан'}"
    )
