from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from app.core.config import get_settings


def local_timezone() -> ZoneInfo:
    return ZoneInfo(get_settings().timezone)


def as_local(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=local_timezone())
    return value.astimezone(local_timezone())


def local_date_text(value: datetime | None) -> str | None:
    return as_local(value).strftime("%d.%m.%Y") if value else None


def local_datetime_text(value: datetime) -> str:
    return as_local(value).strftime("%d.%m.%Y %H:%M")


def parse_local_date(value: str) -> datetime:
    return datetime.strptime(value.strip(), "%d.%m.%Y").replace(tzinfo=local_timezone()).astimezone(UTC)


def delivery_date_order_is_valid(
    sent_at: datetime | None,
    expected_at: datetime | None,
) -> bool:
    if not sent_at or not expected_at:
        return True
    return as_local(expected_at).date() >= as_local(sent_at).date()
