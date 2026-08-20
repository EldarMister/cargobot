from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AppSetting

DEFAULT_SETTINGS = {
    "warehouse_receiver": "",
    "warehouse_phone": "",
    "warehouse_address": "",
    "warehouse_name": "",
    "support_username": "",
}


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
