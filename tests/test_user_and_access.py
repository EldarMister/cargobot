from datetime import UTC, datetime, timedelta

import pytest

from app.core.enums import ParcelStatus
from app.db.models import Parcel, User
from app.db.repositories import ParcelRepository
from app.services.user_service import UserService, UserServiceError


async def test_link_existing_client_attaches_old_parcels(session):
    user = User(client_code="J-8226", full_name="Султанов Азим", phone="+996555000000")
    parcel = Parcel(
        tracking_number="78999695208956",
        client_code="J-8226",
        status=ParcelStatus.IN_TRANSIT,
    )
    session.add_all([user, parcel])
    await session.commit()

    linked = await UserService(session).link_existing(123456, "j - 8226", "  Султанов   Азим ")
    await session.commit()
    await session.refresh(parcel)

    assert linked.telegram_id == 123456
    assert parcel.user_id == linked.id


async def test_wrong_name_cannot_link_client(session):
    session.add(User(client_code="J-8226", full_name="Султанов Азим", phone="+996555000000"))
    await session.commit()

    with pytest.raises(UserServiceError, match="не совпадают"):
        await UserService(session).link_existing(123456, "J-8226", "Чужое Имя")


async def test_client_sees_only_own_parcels(session):
    session.add_all(
        [
            Parcel(
                tracking_number="TRACK000001",
                client_code="J-0001",
                status=ParcelStatus.CHINA_WAREHOUSE,
            ),
            Parcel(
                tracking_number="TRACK000002",
                client_code="J-0002",
                status=ParcelStatus.CHINA_WAREHOUSE,
            ),
        ]
    )
    await session.commit()

    parcels = await ParcelRepository(session).for_client("J-0001")

    assert [parcel.tracking_number for parcel in parcels] == ["TRACK000001"]


async def test_one_telegram_cannot_link_two_codes(session):
    session.add_all(
        [
            User(client_code="J-0001", full_name="Иван Иванов", phone="+996111111111", telegram_id=10),
            User(client_code="J-0002", full_name="Петр Петров", phone="+996222222222"),
        ]
    )
    await session.commit()

    with pytest.raises(UserServiceError, match="другой код"):
        await UserService(session).link_existing(10, "J-0002", "Петр Петров")


def test_client_access_supports_temporary_and_permanent_blocks():
    now = datetime.now(UTC)
    user = User(client_code="J-0001", full_name="Иван Иванов", phone="+996111111111")

    assert user.has_access(now)
    user.blocked_until = now + timedelta(days=3)
    assert not user.has_access(now)
    assert user.has_access(now + timedelta(days=4))
    user.blocked_until = None
    user.is_active = False
    assert not user.has_access(now)
