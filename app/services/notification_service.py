import logging

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from app.core.dates import local_date_text
from app.core.enums import ParcelStatus
from app.db.models import Parcel
from app.services.import_service import ParcelNotification
from app.services.presentation import remaining_arrival_text

logger = logging.getLogger(__name__)


def notification_text(event: ParcelNotification) -> str:
    if event.is_new:
        title = "📦 Новый товар зарегистрирован"
    elif event.dates_changed and not event.status_changed:
        title = "🗓 Обновлена информация о доставке"
    elif event.status in {ParcelStatus.ARRIVED_COUNTRY, ParcelStatus.LOCAL_WAREHOUSE}:
        title = "🏢 Ваш товар прибыл"
    elif event.status == ParcelStatus.READY_FOR_PICKUP:
        title = "✅ Ваш товар готов к выдаче"
    else:
        title = "🚚 Обновление по вашему товару"
    lines = [
        title,
        "",
        f"📦 Трек-код: <code>{event.tracking_number}</code>",
        f"🔑 Код клиента: {event.client_code}",
        f"📊 Статус: {event.status.label}",
    ]
    if event.sent_at:
        lines.append(f"📅 Выехал: {local_date_text(event.sent_at)}")
    if event.expected_at:
        date_label = (
            "🗓 Новая примерная дата прибытия"
            if event.expected_at_changed and not event.status_changed
            else "🗓 Примерно приедет"
        )
        lines.append(f"{date_label}: {local_date_text(event.expected_at)}")
        if event.status not in {ParcelStatus.DELIVERED, ParcelStatus.CANCELLED}:
            lines.append(remaining_arrival_text(event.expected_at))
    return "\n".join(lines)


async def send_notification(bot: Bot, event: ParcelNotification) -> bool:
    try:
        await bot.send_message(event.telegram_id, notification_text(event), parse_mode="HTML")
        return True
    except TelegramAPIError as exc:
        logger.warning("Could not notify telegram_id=%s: %s", event.telegram_id, type(exc).__name__)
        return False


async def notify_parcel_status(
    bot: Bot,
    parcel: Parcel,
    is_new: bool = False,
    status_changed: bool = False,
    dates_changed: bool = False,
    sent_at_changed: bool = False,
    expected_at_changed: bool = False,
) -> bool:
    if not parcel.user or not parcel.user.telegram_id or not parcel.user.has_access():
        return False
    return await send_notification(
        bot,
        ParcelNotification(
            telegram_id=parcel.user.telegram_id,
            tracking_number=parcel.tracking_number,
            client_code=parcel.client_code,
            status=parcel.status,
            is_new=is_new,
            status_changed=status_changed,
            dates_changed=dates_changed,
            sent_at_changed=sent_at_changed,
            expected_at_changed=expected_at_changed,
            sent_at=parcel.sent_at,
            expected_at=parcel.expected_at,
        ),
    )
