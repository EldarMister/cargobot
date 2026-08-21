from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select

from app.core.enums import ParcelStatus
from app.db.models import Import, ImportRevision, Parcel, ParcelStatusHistory, User
from app.services.excel_importer import ExcelParseResult, ParsedExcelRow
from app.services.import_service import DuplicateImportError, ImportBatchConflictError, ImportService
from app.services.notification_service import notification_text
from app.services.parcel_service import ParcelService


def parsed(tracking="YT7592444294461", code="J-0329"):
    return ExcelParseResult(rows=[ParsedExcelRow("Sheet1", 2, tracking_number=tracking, client_code=code)])


async def test_repeat_import_updates_instead_of_duplicate(session):
    first = await ImportService(session).process(parsed(), "first.xlsx", ParcelStatus.CHINA_WAREHOUSE, 100)
    await session.commit()
    first_id = first.import_record.id
    first_created_rows = first.import_record.created_rows
    second = await ImportService(session).process(parsed(), "second.xlsx", ParcelStatus.IN_TRANSIT, 100)
    await session.commit()

    assert first_created_rows == 1
    assert second.import_record.created_rows == 0
    assert second.import_record.updated_rows == 1
    assert second.import_record.id == first_id
    assert second.is_revision is True
    assert await session.scalar(select(func.count(Import.id))) == 1
    assert await session.scalar(select(func.count(Parcel.id))) == 1
    assert await session.scalar(select(func.count(ParcelStatusHistory.id))) == 2
    parcel = await session.scalar(select(Parcel))
    assert parcel.status == ParcelStatus.IN_TRANSIT
    assert parcel.sent_at is None
    assert parcel.expected_at is None


async def test_exact_file_is_rejected_and_revisions_are_recorded(session):
    service = ImportService(session)
    first_hash = "a" * 64
    second_hash = "b" * 64
    first = await service.process(
        parsed(),
        "cargo.xlsx",
        ParcelStatus.CHINA_WAREHOUSE,
        100,
        file_hash=first_hash,
    )
    await session.commit()

    updated = await service.process(
        parsed(),
        "cargo-edited.xlsx",
        ParcelStatus.CHINA_WAREHOUSE,
        100,
        file_hash=second_hash,
    )
    await session.commit()

    assert updated.import_record.id == first.import_record.id
    assert await session.scalar(select(func.count(ImportRevision.id))) == 2

    with pytest.raises(DuplicateImportError) as error:
        await service.process(
            parsed(),
            "cargo-copy.xlsx",
            ParcelStatus.CHINA_WAREHOUSE,
            100,
            file_hash=first_hash,
        )
    assert error.value.import_id == first.import_record.id


async def test_explicit_new_batch_does_not_steal_existing_tracking(session):
    service = ImportService(session)
    await service.process(parsed(), "cargo.xlsx", ParcelStatus.CHINA_WAREHOUSE, 100)
    await session.commit()

    with pytest.raises(ImportBatchConflictError):
        await service.process(
            parsed(),
            "another-batch.xlsx",
            ParcelStatus.IN_TRANSIT,
            100,
            auto_match=False,
        )


async def test_same_status_does_not_notify_twice(session):
    user = User(client_code="J-0329", full_name="Иван Иванов", phone="+996555000000", telegram_id=777)
    session.add(user)
    await session.commit()
    first = await ImportService(session).process(parsed(), "first.xlsx", ParcelStatus.CHINA_WAREHOUSE, 100)
    await session.commit()
    second = await ImportService(session).process(parsed(), "second.xlsx", ParcelStatus.CHINA_WAREHOUSE, 100)

    assert len(first.notifications) == 1
    assert second.notifications == []
    assert await session.scalar(select(func.count(Parcel.id))) == 1


async def test_duplicate_tracking_inside_one_file_is_not_duplicated(session):
    data = parsed()
    data.rows.append(ParsedExcelRow("Sheet2", 3, tracking_number="YT7592444294461", client_code="J-0329"))
    outcome = await ImportService(session).process(data, "duplicate.xlsx", ParcelStatus.CHINA_WAREHOUSE, 100)
    await session.commit()

    assert outcome.import_record.created_rows == 1
    assert await session.scalar(select(func.count(Parcel.id))) == 1


async def test_new_in_transit_parcel_receives_explicit_delivery_dates(session):
    sent_at = datetime(2026, 5, 16, tzinfo=UTC)
    expected_at = datetime(2026, 5, 26, tzinfo=UTC)
    user = User(
        client_code="J-0329",
        full_name="Иван Иванов",
        phone="+996555000000",
        telegram_id=777,
    )
    session.add(user)
    await session.commit()

    outcome = await ImportService(session).process(
        parsed(),
        "in-transit.xlsx",
        ParcelStatus.IN_TRANSIT,
        100,
        sent_at=sent_at,
        expected_at=expected_at,
    )
    await session.commit()
    parcel = await session.scalar(select(Parcel))

    assert parcel.status == ParcelStatus.IN_TRANSIT
    assert parcel.sent_at == sent_at.replace(tzinfo=None)
    assert parcel.expected_at == expected_at.replace(tzinfo=None)
    assert outcome.import_record.sent_at == sent_at
    assert outcome.import_record.expected_at == expected_at
    assert len(outcome.notifications) == 1
    assert "Выехал" in notification_text(outcome.notifications[0])


async def test_identical_status_and_dates_do_not_repeat_notification(session):
    sent_at = datetime(2026, 5, 16, tzinfo=UTC)
    expected_at = datetime(2026, 5, 26, tzinfo=UTC)
    session.add(
        User(
            client_code="J-0329",
            full_name="Иван Иванов",
            phone="+996555000000",
            telegram_id=777,
        )
    )
    await session.commit()
    service = ImportService(session)
    await service.process(
        parsed(),
        "first.xlsx",
        ParcelStatus.IN_TRANSIT,
        100,
        sent_at=sent_at,
        expected_at=expected_at,
    )
    await session.commit()

    repeated = await service.process(
        parsed(),
        "repeated.xlsx",
        ParcelStatus.IN_TRANSIT,
        100,
        sent_at=sent_at,
        expected_at=expected_at,
    )

    assert repeated.notifications == []
    assert await session.scalar(select(func.count(Parcel.id))) == 1
    assert await session.scalar(select(func.count(ParcelStatusHistory.id))) == 1


async def test_changed_expected_date_notifies_without_status_history(session):
    first_expected = datetime(2026, 5, 26, tzinfo=UTC)
    new_expected = datetime(2026, 5, 29, tzinfo=UTC)
    session.add(
        User(
            client_code="J-0329",
            full_name="Иван Иванов",
            phone="+996555000000",
            telegram_id=777,
        )
    )
    await session.commit()
    service = ImportService(session)
    await service.process(
        parsed(),
        "first.xlsx",
        ParcelStatus.IN_TRANSIT,
        100,
        expected_at=first_expected,
    )
    await session.commit()

    changed = await service.process(
        parsed(),
        "changed.xlsx",
        ParcelStatus.IN_TRANSIT,
        100,
        expected_at=new_expected,
    )
    await session.commit()

    assert len(changed.notifications) == 1
    event = changed.notifications[0]
    assert event.dates_changed is True
    assert event.expected_at_changed is True
    assert event.status_changed is False
    assert "Обновлена информация о доставке" in notification_text(event)
    assert "29.05.2026" in notification_text(event)
    assert await session.scalar(select(func.count(ParcelStatusHistory.id))) == 1


async def test_changed_status_creates_history_and_notification(session):
    session.add(
        User(
            client_code="J-0329",
            full_name="Иван Иванов",
            phone="+996555000000",
            telegram_id=777,
        )
    )
    await session.commit()
    service = ImportService(session)
    await service.process(parsed(), "china.xlsx", ParcelStatus.CHINA_WAREHOUSE, 100)
    await session.commit()

    changed = await service.process(parsed(), "arrived.xlsx", ParcelStatus.ARRIVED_COUNTRY, 100)
    await session.commit()

    assert len(changed.notifications) == 1
    event = changed.notifications[0]
    assert event.status_changed is True
    assert "Ваш товар прибыл" in notification_text(event)
    assert await session.scalar(select(func.count(ParcelStatusHistory.id))) == 2


async def test_admin_marks_whole_import_batch_arrived(session):
    batch = Import(
        filename="truck.xlsx",
        selected_status=ParcelStatus.IN_TRANSIT,
        uploaded_by=100,
    )
    session.add(batch)
    await session.flush()
    session.add_all(
        [
            Parcel(
                tracking_number="BATCH000001",
                client_code="J-0001",
                import_id=batch.id,
                status=ParcelStatus.IN_TRANSIT,
            ),
            Parcel(
                tracking_number="BATCH000002",
                client_code="J-0002",
                import_id=batch.id,
                status=ParcelStatus.IN_TRANSIT,
            ),
        ]
    )
    await session.commit()

    changed = await ParcelService(session).mark_import_arrived(batch.id, changed_by=100)
    await session.commit()

    assert len(changed) == 2
    assert all(parcel.status == ParcelStatus.ARRIVED_COUNTRY for parcel in changed)
    assert all(parcel.arrived_at is not None for parcel in changed)


async def test_admin_changes_status_for_whole_import_batch(session):
    batch = Import(
        filename="truck.xlsx",
        selected_status=ParcelStatus.CHINA_WAREHOUSE,
        uploaded_by=100,
    )
    session.add(batch)
    await session.flush()
    session.add_all(
        [
            Parcel(
                tracking_number="GROUP000001",
                client_code="J-0001",
                import_id=batch.id,
                status=ParcelStatus.CHINA_WAREHOUSE,
            ),
            Parcel(
                tracking_number="GROUP000002",
                client_code="J-0002",
                import_id=batch.id,
                status=ParcelStatus.PREPARING,
            ),
        ]
    )
    await session.commit()

    record, changed = await ParcelService(session).change_import_status(
        batch.id,
        ParcelStatus.READY_FOR_PICKUP,
        changed_by=100,
    )
    await session.commit()

    assert record is not None
    assert record.selected_status == ParcelStatus.READY_FOR_PICKUP
    assert len(changed) == 2
    assert all(parcel.status == ParcelStatus.READY_FOR_PICKUP for parcel in changed)
