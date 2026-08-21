from collections import defaultdict
from datetime import datetime
from html import escape

from app.core.dates import as_local, local_timezone
from app.core.enums import ParcelStatus
from app.db.models import Parcel
from app.i18n import normalize_language, status_label, t


def pluralize_days(days: int, language: str = "ru") -> str:
    language = normalize_language(language)
    if language == "en":
        return f"{days} {'day' if days == 1 else 'days'}"
    if language == "zh":
        return f"{days} 天"
    remainder_100 = days % 100
    remainder_10 = days % 10
    if remainder_10 == 1 and remainder_100 != 11:
        word = "день"
    elif remainder_10 in {2, 3, 4} and remainder_100 not in {12, 13, 14}:
        word = "дня"
    else:
        word = "дней"
    return f"{days} {word}"


def remaining_arrival_text(expected_at: datetime, today=None, language: str = "ru") -> str:
    expected = as_local(expected_at).date()
    current_date = today or datetime.now(local_timezone()).date()
    remaining = (expected - current_date).days
    if remaining > 0:
        return t("remaining_days", language, count=pluralize_days(remaining, language))
    if remaining == 0:
        return t("expected_today", language)
    return t("expected_passed", language)


def format_parcel(parcel: Parcel, language: str = "ru") -> str:
    lines = [f"📦 <code>{parcel.tracking_number}</code>"]
    if parcel.sent_at:
        lines.append(t("sent_at", language, date=f"{as_local(parcel.sent_at):%d.%m.%Y}"))
    if parcel.expected_at:
        expected = as_local(parcel.expected_at)
        lines.append(t("expected_at", language, date=f"{expected:%d.%m.%Y}"))
        if parcel.status not in {ParcelStatus.DELIVERED, ParcelStatus.CANCELLED}:
            lines.append(remaining_arrival_text(parcel.expected_at, language=language))
    return "\n".join(lines)


def format_parcel_list(
    parcels: list[Parcel],
    *,
    title: str = "📦 Мои товары",
    empty_message: str = "У вас пока нет зарегистрированных товаров.",
    language: str = "ru",
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
        lines.extend(["", f"<b>{status_label(status, language)}:</b>", ""])
        lines.append(
            "\n\n────────────\n\n".join(format_parcel(parcel, language) for parcel in items)
        )
    lines.extend(["", t("parcel_total", language, count=len(parcels))])
    return "\n".join(lines)


def warehouse_text(settings: dict[str, str], client_code: str, language: str = "ru") -> str:
    receiver = " ".join(part for part in [settings.get("warehouse_receiver", ""), client_code] if part)
    warehouse = " ".join(part for part in [settings.get("warehouse_name", ""), client_code] if part)
    missing = t("not_specified", language)
    return "\n".join(
        [
            t("warehouse_title", language),
            "",
            t("warehouse_receiver", language, value=escape(receiver) if receiver else missing),
            t(
                "warehouse_phone",
                language,
                value=escape(settings.get("warehouse_phone", "")) or missing,
            ),
            t(
                "warehouse_address",
                language,
                value=escape(settings.get("warehouse_address", "")) or missing,
            ),
            t("warehouse_name", language, value=escape(warehouse) if warehouse else missing),
        ]
    )
