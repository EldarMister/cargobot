from aiogram import Router

from app.bot.filters import AdminFilter
from app.bot.handlers.admin import imports, menu, misc, parcels, users
from app.core.config import Settings


def build_admin_router(settings: Settings) -> Router:
    router = Router(name="admin")
    admin_filter = AdminFilter(settings)
    router.message.filter(admin_filter)
    router.callback_query.filter(admin_filter)
    router.include_router(menu.router)
    router.include_router(imports.router)
    router.include_router(parcels.router)
    router.include_router(users.router)
    router.include_router(misc.router)
    return router
