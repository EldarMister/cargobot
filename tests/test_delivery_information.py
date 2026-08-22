from datetime import UTC, date, datetime

import pytest
from sqlalchemy import func, select

from app.bot.handlers.user.parcels import whatsapp_link
from app.core.dates import calculate_expected_at, delivery_date_order_is_valid, parse_local_date
from app.core.enums import ParcelStatus
from app.db.models import Parcel, ParcelStatusHistory
from app.services.delivery_reminder_service import ReminderKind, reminder_for, reminder_text
from app.services.import_service import ParcelNotification
from app.services.notification_service import notification_text
from app.services.parcel_service import ParcelService, apply_delivery_dates
from app.services.presentation import (
    format_parcel,
    pluralize_days,
    remaining_arrival_text,
    warehouse_text,
)


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


def test_expected_arrival_is_calculated_from_transit_days():
    sent_at = datetime(2026, 5, 16, tzinfo=UTC)

    assert calculate_expected_at(sent_at, 12) == datetime(2026, 5, 28, tzinfo=UTC)

    with pytest.raises(ValueError):
        calculate_expected_at(sent_at, 0)


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


def test_warehouse_address_includes_client_code():
    text = warehouse_text(
        {
            "warehouse_receiver": "王国利",
            "warehouse_phone": "18818913136",
            "warehouse_address": "广东省广州市",
            "warehouse_name": "BCL库房",
        },
        "J-8226",
    )

    assert "Получатель: 王国利 J-8226" in text
    assert "Телефон: 18818913136" in text
    assert "Адрес: 广东省广州市" in text
    assert "Склад: BCL库房 J-8226" in text


def test_whatsapp_setting_accepts_phone_or_ready_link():
    assert whatsapp_link("+996 (555) 123-456") == "https://wa.me/996555123456"
    assert whatsapp_link("https://wa.me/996555123456") == "https://wa.me/996555123456"
    assert whatsapp_link("chat.whatsapp.com/invite-code") == (
        "https://chat.whatsapp.com/invite-code"
    )


def test_warehouse_address_shows_both_configured_warehouses():
    text = warehouse_text(
        {
            "warehouse_receiver": "First receiver",
            "warehouse_address": "First address",
            "warehouse_receiver_2": "Second receiver",
            "warehouse_phone_2": "200-02",
            "warehouse_address_2": "Second address",
            "warehouse_name_2": "Second warehouse",
        },
        "J-8226",
    )

    assert "Адрес склада в Китае №1" in text
    assert "Адрес склада в Китае №2" in text
    assert "Получатель: First receiver J-8226" in text
    assert "Адрес: First address" in text
    assert "Получатель: Second receiver J-8226" in text
    assert "Телефон: 200-02" in text
    assert "Адрес: Second address" in text
    assert "Склад: Second warehouse J-8226" in text


def test_warehouse_address_shows_only_the_configured_warehouse():
    text = warehouse_text(
        {
            "warehouse_receiver": "First receiver",
            "warehouse_address": "First address",
        },
        "J-0001",
    )

    assert "Получатель: First receiver J-0001" in text
    assert "Адрес: First address" in text
    assert "№1" not in text
    assert "№2" not in text


def test_delivery_reminders_are_one_time_and_do_not_mark_arrival():
    parcel = Parcel(
        tracking_number="REMINDER0001",
        client_code="J-8226",
        status=ParcelStatus.IN_TRANSIT,
        expected_at=datetime(2026, 5, 26, tzinfo=UTC),
    )

    approaching = reminder_for(parcel, date(2026, 5, 23))
    assert approaching is not None
    assert approaching.kind == ReminderKind.APPROACHING
    assert "со дня на день" in reminder_text(parcel, approaching)
    assert parcel.status == ParcelStatus.IN_TRANSIT

    parcel.approaching_notified_at = datetime(2026, 5, 23, tzinfo=UTC)
    assert reminder_for(parcel, date(2026, 5, 24)) is None

    due = reminder_for(parcel, date(2026, 5, 26))
    assert due is not None
    assert due.kind == ReminderKind.DUE
    assert "Точная дата прибытия уточняется" in reminder_text(parcel, due)
    assert parcel.status == ParcelStatus.IN_TRANSIT

    parcel.due_notified_at = datetime(2026, 5, 26, tzinfo=UTC)
    assert reminder_for(parcel, date(2026, 5, 27)) is None


def test_changed_expected_date_rearms_delivery_reminders():
    parcel = Parcel(
        tracking_number="REMINDER0002",
        client_code="J-8226",
        status=ParcelStatus.IN_TRANSIT,
        expected_at=datetime(2026, 5, 26, tzinfo=UTC),
        approaching_notified_at=datetime(2026, 5, 23, tzinfo=UTC),
        due_notified_at=datetime(2026, 5, 26, tzinfo=UTC),
    )

    changes = apply_delivery_dates(parcel, expected_at=datetime(2026, 5, 29, tzinfo=UTC))

    assert changes.expected_at is True
    assert parcel.approaching_notified_at is None
    assert parcel.due_notified_at is None
