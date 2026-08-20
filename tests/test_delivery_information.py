from datetime import UTC, date, datetime

import pytest
from sqlalchemy import func, select

from app.core.dates import delivery_date_order_is_valid, parse_local_date
from app.core.enums import ParcelStatus
from app.db.models import Parcel, ParcelStatusHistory
from app.services.import_service import ParcelNotification
from app.services.notification_service import notification_text
from app.services.parcel_service import ParcelService
from app.services.presentation import format_parcel, pluralize_days, remaining_arrival_text


@pytest.mark.parametrize(
    ("days", "expected"),
    [(1, "1 день"), (2, "2 дня"), (5, "5 дней"), (11, "11 дней"), (21, "21 день")],
)
def test_russian_day_forms(days, expected):
    assert pluralize_days(days) == expected


def test_remaining_days_today_and_past():
    today = date(2026, 5, 16)
    future = datetime(2026, 5, 26, tzinfo=UTC)
    current = datetime(2026, 5, 16, tzinfo=UTC)
    past = datetime(2026, 5, 15, tzinfo=UTC)

    assert remaining_arrival_text(future, today) == "⌛ Осталось примерно: 10 дней"
    assert remaining_arrival_text(current, today) == "🗓 Ожидается сегодня"
    assert "уже наступила" in remaining_arrival_text(past, today)
    assert "-" not in remaining_arrival_text(past, today)


def test_impossible_and_reversed_dates_are_rejected():
    with pytest.raises(ValueError):
        parse_local_date("31.02.2026")
    sent_at = parse_local_date("16.05.2026")
    earlier_arrival = parse_local_date("15.05.2026")
    assert not delivery_date_order_is_valid(sent_at, earlier_arrival)
    assert delivery_date_order_is_valid(sent_at, None)


async def test_manual_status_change_writes_history_only_once(session):
    parcel = Parcel(
        tracking_number="MANUAL000001",
        client_code="J-0001",
        status=ParcelStatus.CHINA_WAREHOUSE,
    )
    session.add(parcel)
    await session.commit()
    service = ParcelService(session)

    assert await service.change_status(parcel, ParcelStatus.IN_TRANSIT, 123) is True
    assert parcel.sent_at is None
    await session.commit()
    assert await service.change_status(parcel, ParcelStatus.IN_TRANSIT, 123) is False

    assert await session.scalar(select(func.count(ParcelStatusHistory.id))) == 1


def test_ready_for_pickup_has_dedicated_notification():
    event = ParcelNotification(
        telegram_id=1,
        tracking_number="TRACK000001",
        client_code="J-0001",
        status=ParcelStatus.READY_FOR_PICKUP,
        is_new=False,
        status_changed=True,
    )

    text = notification_text(event)

    assert "Ваш товар готов к выдаче" in text
    assert "TRACK000001" in text


def test_old_parcel_without_dates_is_rendered_safely():
    parcel = Parcel(
        tracking_number="OLDTRACK0001",
        client_code="J-0001",
        status=ParcelStatus.CHINA_WAREHOUSE,
    )

    text = format_parcel(parcel)

    assert "OLDTRACK0001" in text
    assert "Выехал" not in text
    assert "Примерно приедет" not in text
