from aiogram.filters import BaseFilter
from aiogram.types import TelegramObject

from app.core.config import Settings


class AdminFilter(BaseFilter):
    def __init__(self, settings: Settings):
        self.admin_ids = settings.admin_id_set

    async def __call__(self, event: TelegramObject) -> bool:
        user = getattr(event, "from_user", None)
        return bool(user and user.id in self.admin_ids)
