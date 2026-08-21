import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, date, datetime
from enum import StrEnum
from html import escape

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from app.core.dates import as_local, local_date_text, local_timezone
from app.core.enums import ParcelStatus
from app.db.models import Parcel
from app.services.presentation import pluralize_days

logger = logging.getLogger(__name__)

REMINDER_CHECK_INTERVAL_SECONDS = 60 * 60
APPROACHING_THRESHOLD_DAYS = 3


class ReminderKind(StrEnum):
    APPROACHING = "APPROACHING"
    DUE = "DUE"


@dataclass(frozen=True, slots=True)
class DeliveryReminder:
    kind: ReminderKind
    days_remaining: int


def reminder_for(parcel: Parcel, today: date | None = None) -> DeliveryReminder | None:
    if parcel.status != ParcelStatus.IN_TRANSIT or not parcel.expected_at:
        return None
    current_date = today or datetime.now(local_timezone()).date()
    days_remaining = (as_local(parcel.expected_at).date() - current_date).days
    if days_remaining <= 0 and parcel.due_notified_at is None:
        return DeliveryReminder(ReminderKind.DUE, days_remaining)
    if 0 < days_remaining <= APPROACHING_THRESHOLD_DAYS and parcel.approaching_notified_at is None:
        return DeliveryReminder(ReminderKind.APPROACHING, days_remaining)
    return None


def reminder_text(parcel: Parcel, reminder: DeliveryReminder) -> str:
    lines = [
        (
            "🚚 <b>Ваш товар ожидается со дня на день</b>"
            if reminder.kind == ReminderKind.APPROACHING
            else "🗓 <b>Расчётный срок доставки наступил</b>"
        ),
        "",
        f"📦 Трек-код: <code>{escape(parcel.tracking_number)}</code>",
        f"🔑 Код клиента: {escape(parcel.client_code)}",
    ]
    if parcel.expected_at:
        lines.append(f"🗓 Примерная дата: {local_date_text(parcel.expected_at)}")
    if reminder.kind == ReminderKind.APPROACHING:
        lines.append(f"⌛ Осталось примерно: {pluralize_days(reminder.days_remaining)}")
    else:
        lines.extend(["", "Точная дата прибытия уточняется."])
    return "\n".join(lines)


async def send_delivery_reminders(session: AsyncSession, bot: Bot) -> int:
    parcels = list(
        await session.scalars(
            select(Parcel)
            .options(selectinload(Parcel.user))
            .where(
                Parcel.status == ParcelStatus.IN_TRANSIT,
                Parcel.expected_at.is_not(None),
            )
        )
    )
    sent = 0
    now = datetime.now(UTC)
    for parcel in parcels:
        if not parcel.user or not parcel.user.telegram_id or not parcel.user.has_access():
            continue
        reminder = reminder_for(parcel)
        if not reminder:
            continue
        try:
            await bot.send_message(
                parcel.user.telegram_id,
                reminder_text(parcel, reminder),
                parse_mode="HTML",
            )
        except TelegramAPIError as exc:
            logger.warning(
                "Could not send delivery reminder: parcel_id=%s error=%s",
                parcel.id,
                type(exc).__name__,
            )
            continue
        if reminder.kind == ReminderKind.APPROACHING:
            parcel.approaching_notified_at = now
        else:
            parcel.due_notified_at = now
        sent += 1
    await session.commit()
    return sent


async def delivery_reminder_loop(
    bot: Bot,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    while True:
        try:
            async with session_factory() as session:
                sent = await send_delivery_reminders(session, bot)
                if sent:
                    logger.info("Sent %s delivery reminders", sent)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Delivery reminder check failed")
        await asyncio.sleep(REMINDER_CHECK_INTERVAL_SECONDS)
