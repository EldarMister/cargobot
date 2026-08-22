from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AppSetting

DEFAULT_SETTINGS = {
    "company_name": "BCL EXPRESS",
    "default_transit_days": "12",
    "warehouse_receiver": "",
    "warehouse_phone": "",
    "warehouse_address": "",
    "warehouse_name": "",
    "warehouse_receiver_2": "",
    "warehouse_phone_2": "",
    "warehouse_address_2": "",
    "warehouse_name_2": "",
    "support_username": "",
    "contact_whatsapp": "",
    "local_warehouse_address": "",
    "work_schedule": "",
}

WAREHOUSE_FIELDS = ("receiver", "phone", "address", "name")


def warehouse_setting_key(field: str, slot: int) -> str:
    if field not in WAREHOUSE_FIELDS or slot not in {1, 2}:
        raise ValueError("Unknown warehouse setting")
    suffix = "" if slot == 1 else "_2"
    return f"warehouse_{field}{suffix}"


def warehouse_is_configured(settings: dict[str, str], slot: int) -> bool:
    return any(settings.get(warehouse_setting_key(field, slot), "").strip() for field in WAREHOUSE_FIELDS)


class SettingRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, key: str, default: str = "") -> str:
        value = await self.session.scalar(select(AppSetting.value).where(AppSetting.key == key))
        return default if value is None else value

    async def all(self) -> dict[str, str]:
        rows = await self.session.execute(select(AppSetting.key, AppSetting.value))
        result = dict(DEFAULT_SETTINGS)
        result.update(dict(rows.all()))
        return result

    async def set(self, key: str, value: str) -> None:
        item = await self.session.get(AppSetting, key)
        if item:
            item.value = value
        else:
            self.session.add(AppSetting(key=key, value=value))

    async def clear_warehouse(self, slot: int) -> dict[str, str]:
        for field in WAREHOUSE_FIELDS:
            await self.set(warehouse_setting_key(field, slot), "")
        values = await self.all()
        values.update({warehouse_setting_key(field, slot): "" for field in WAREHOUSE_FIELDS})
        return values
