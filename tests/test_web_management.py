from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import Settings
from app.core.enums import ParcelStatus
from app.db.base import Base
from app.db.models import Import, Parcel, User
from app.web.app import SESSION_COOKIE, create_web_app
from app.web.auth import create_admin_session


@pytest.fixture
async def web_management_client():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    settings = Settings(
        _env_file=None,
        BOT_TOKEN="123456:test-token",
        ADMIN_IDS="777",
    )
    bot = AsyncMock()
    app = create_web_app(bot, session_factory, settings)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        client.cookies.set(SESSION_COOKIE, create_admin_session(777, settings.bot_token))
        yield client, session_factory, bot
    await engine.dispose()


async def test_web_admin_can_create_edit_block_and_inspect_client(web_management_client):
    client, session_factory, _ = web_management_client

    created = await client.post(
        "/api/clients",
        json={
            "client_code": "J-8226",
            "full_name": "Султанов Азим",
            "phone": "+996 555 123 456",
            "city": "Бишкек",
            "telegram_id": 12345,
        },
    )
    assert created.status_code == 200
    client_id = created.json()["id"]
    async with session_factory() as session:
        session.add(
            Parcel(
                tracking_number="MANAGE000001",
                client_code="J-8226",
                user_id=client_id,
                status=ParcelStatus.IN_TRANSIT,
            )
        )
        await session.commit()

    edited = await client.patch(
        f"/api/clients/{client_id}",
        json={
            "full_name": "Султанов Азим Бакытович",
            "phone": "+996555000000",
            "city": "Ош",
            "telegram_id": 12345,
        },
    )
    assert edited.status_code == 200
    assert edited.json()["city"] == "Ош"

    blocked = await client.post(
        f"/api/clients/{client_id}/block",
        json={"mode": "temporary", "days": 7},
    )
    assert blocked.status_code == 200
    assert blocked.json()["block_mode"] == "temporary"
    parcels = await client.get(f"/api/clients/{client_id}/parcels")
    assert [item["tracking_number"] for item in parcels.json()] == ["MANAGE000001"]


async def test_web_admin_can_change_status_for_whole_import(web_management_client):
    client, session_factory, bot = web_management_client
    async with session_factory() as session:
        user = User(
            client_code="J-0001",
            full_name="Иван Иванов",
            phone="+996555000000",
            telegram_id=12345,
        )
        batch = Import(
            filename="batch.xlsx",
            selected_status=ParcelStatus.CHINA_WAREHOUSE,
            uploaded_by=777,
        )
        session.add_all([user, batch])
        await session.flush()
        session.add_all(
            [
                Parcel(
                    tracking_number="WEBBATCH0001",
                    client_code=user.client_code,
                    user_id=user.id,
                    import_id=batch.id,
                    status=ParcelStatus.CHINA_WAREHOUSE,
                ),
                Parcel(
                    tracking_number="WEBBATCH0002",
                    client_code=user.client_code,
                    user_id=user.id,
                    import_id=batch.id,
                    status=ParcelStatus.PREPARING,
                ),
            ]
        )
        await session.commit()
        batch_id = batch.id

    response = await client.patch(
        f"/api/imports/{batch_id}/status",
        json={"status": "READY_FOR_PICKUP", "transit_days": 12},
    )

    assert response.status_code == 200
    assert response.json()["updated"] == 2
    assert response.json()["notifications"] == 2
    assert bot.send_message.await_count == 2


async def test_web_admin_can_delegate_and_revoke_admin_access(web_management_client):
    client, _, bot = web_management_client
    created = await client.post(
        "/api/clients",
        json={
            "client_code": "J-9001",
            "full_name": "Delegated Admin",
            "phone": "+996555900001",
            "city": "Bishkek",
            "telegram_id": 9001,
        },
    )
    client_id = created.json()["id"]

    granted = await client.post(f"/api/clients/{client_id}/admin", json={"is_admin": True})
    assert granted.status_code == 200
    assert granted.json()["is_admin"] is True
    bot.set_chat_menu_button.assert_awaited()

    client.cookies.set(SESSION_COOKIE, create_admin_session(9001, "123456:test-token"))
    assert (await client.get("/api/meta")).status_code == 200

    client.cookies.set(SESSION_COOKIE, create_admin_session(777, "123456:test-token"))
    revoked = await client.post(f"/api/clients/{client_id}/admin", json={"is_admin": False})
    assert revoked.status_code == 200
    assert revoked.json()["is_admin"] is False

    client.cookies.set(SESSION_COOKIE, create_admin_session(9001, "123456:test-token"))
    assert (await client.get("/api/meta")).status_code == 403


async def test_web_admin_can_edit_parcel_owner_dates_and_delete(web_management_client):
    client, session_factory, _ = web_management_client
    async with session_factory() as session:
        first_user = User(
            client_code="J-1001",
            full_name="First Client",
            phone="+996555100001",
            telegram_id=1001,
        )
        second_user = User(
            client_code="J-1002",
            full_name="Second Client",
            phone="+996555100002",
            telegram_id=1002,
        )
        session.add_all([first_user, second_user])
        await session.flush()
        parcel = Parcel(
            tracking_number="EDITABLE0001",
            client_code=first_user.client_code,
            user_id=first_user.id,
            status=ParcelStatus.CHINA_WAREHOUSE,
        )
        session.add(parcel)
        await session.commit()
        parcel_id = parcel.id

    updated = await client.patch(
        f"/api/parcels/{parcel_id}",
        json={
            "client_code": "J-1002",
            "status": "IN_TRANSIT",
            "sent_date": "2026-08-21",
            "expected_date": "2026-09-05",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["parcel"]["client_code"] == "J-1002"
    assert updated.json()["parcel"]["sent_date"] == "2026-08-21"
    assert updated.json()["parcel"]["expected_date"] == "2026-09-05"

    deleted = await client.delete(f"/api/parcels/{parcel_id}")
    assert deleted.status_code == 200
    async with session_factory() as session:
        assert await session.get(Parcel, parcel_id) is None


async def test_web_admin_can_assign_batch_sent_and_expected_dates(web_management_client):
    client, session_factory, _ = web_management_client
    async with session_factory() as session:
        batch = Import(
            filename="dated-batch.xlsx",
            selected_status=ParcelStatus.CHINA_WAREHOUSE,
            uploaded_by=777,
        )
        session.add(batch)
        await session.flush()
        session.add(
            Parcel(
                tracking_number="DATEDBATCH001",
                client_code="J-7001",
                import_id=batch.id,
                status=ParcelStatus.CHINA_WAREHOUSE,
            )
        )
        await session.commit()
        batch_id = batch.id

    response = await client.patch(
        f"/api/imports/{batch_id}/status",
        json={
            "status": "IN_TRANSIT",
            "sent_date": "2026-08-22",
            "expected_date": "2026-09-10",
            "transit_days": 12,
        },
    )
    assert response.status_code == 200
    assert response.json()["sent_date"] == "2026-08-22"
    assert response.json()["expected_date"] == "2026-09-10"
