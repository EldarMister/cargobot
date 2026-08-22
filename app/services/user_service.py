from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.db.repositories import UserRepository
from app.services.normalization import (
    normalize_client_code,
    normalize_name,
    normalize_phone,
)


class UserServiceError(ValueError):
    """A safe, user-facing domain validation error."""

    def __init__(self, message: str, code: str = "owner_mismatch"):
        super().__init__(message)
        self.code = code


class UserService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.users = UserRepository(session)

    async def register(
        self,
        telegram_id: int,
        full_name: str,
        phone: str = "",
        city: str | None = None,
        language: str | None = None,
    ) -> User:
        if await self.users.by_telegram_id(telegram_id):
            raise UserServiceError("Этот Telegram-аккаунт уже зарегистрирован.", "telegram_registered")
        full_name = " ".join(full_name.split())
        phone = normalize_phone(phone) if phone else ""
        if len(full_name) < 3:
            raise UserServiceError("Укажите полное имя.", "full_name")
        if phone and len(phone) < 8:
            raise UserServiceError("Не удалось распознать номер телефона.", "phone")

        for _ in range(5):
            number = await self.users.next_client_number()
            user = User(
                telegram_id=telegram_id,
                client_code=f"H-{number}",
                full_name=full_name,
                phone=phone,
                city=city or None,
                language=language,
            )
            self.session.add(user)
            try:
                await self.session.flush()
                await self.users.attach_parcels(user)
                return user
            except IntegrityError:
                await self.session.rollback()
        raise UserServiceError(
            "Не удалось назначить свободный код. Повторите попытку.",
            "client_code_assignment",
        )

    async def link_existing(self, telegram_id: int, client_code: str, full_name: str) -> User:
        existing_telegram = await self.users.by_telegram_id(telegram_id)
        if existing_telegram:
            if existing_telegram.client_code == normalize_client_code(client_code):
                return existing_telegram
            raise UserServiceError(
                "К этому Telegram-аккаунту уже привязан другой код.",
                "other_code",
            )

        user = await self.users.by_client_code(normalize_client_code(client_code))
        generic_error = "Код или данные владельца не совпадают."
        if not user or not user.has_access():
            raise UserServiceError(generic_error)
        if user.telegram_id is not None and user.telegram_id != telegram_id:
            raise UserServiceError(
                "Этот код уже привязан. Обратитесь к администратору.",
                "code_linked",
            )
        if normalize_name(user.full_name) != normalize_name(full_name):
            raise UserServiceError(generic_error)

        user.telegram_id = telegram_id
        await self.session.flush()
        await self.users.attach_parcels(user)
        return user

    async def unlink(self, user: User) -> None:
        user.telegram_id = None
        await self.session.flush()
