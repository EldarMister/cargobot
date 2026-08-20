from aiogram import Router

from app.bot.handlers.user import parcels, registration, start


def build_user_router() -> Router:
    router = Router(name="user")
    router.include_router(start.router)
    router.include_router(registration.router)
    router.include_router(parcels.router)
    return router
