from aiogram.filters import BaseFilter
from aiogram.types import TelegramObject
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.db.models import User


class AdminFilter(BaseFilter):
    def __init__(self, settings: Settings):
        self.admin_ids = settings.admin_id_set

    async def __call__(self, event: TelegramObject, session: AsyncSession) -> bool:
        user = getattr(event, "from_user", None)
        if not user:
            return False
        if user.id in self.admin_ids:
            return True
        return bool(
            await session.scalar(
                select(User.is_admin).where(
                    User.telegram_id == user.id,
                    User.is_admin.is_(True),
                )
            )
        )
