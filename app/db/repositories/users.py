from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Parcel, User


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def by_telegram_id(self, telegram_id: int) -> User | None:
        return await self.session.scalar(select(User).where(User.telegram_id == telegram_id))

    async def by_client_code(self, client_code: str) -> User | None:
        return await self.session.scalar(select(User).where(User.client_code == client_code))

    async def search(self, query: str, limit: int = 20) -> list[User]:
        conditions = [
            User.client_code.ilike(f"%{query}%"),
            User.full_name.ilike(f"%{query}%"),
            User.phone.ilike(f"%{query}%"),
        ]
        if query.isdigit():
            conditions.append(User.telegram_id == int(query))
        rows = await self.session.scalars(select(User).where(or_(*conditions)).limit(limit))
        return list(rows)

    async def next_client_number(self) -> int:
        codes = await self.session.scalars(select(User.client_code))
        maximum = 800
        for code in codes:
            if not code.upper().startswith("H-"):
                continue
            try:
                maximum = max(maximum, int(code.split("-", 1)[1]))
            except (IndexError, ValueError):
                continue
        return maximum + 1

    async def attach_parcels(self, user: User) -> int:
        result = await self.session.execute(
            update(Parcel)
            .where(Parcel.client_code == user.client_code)
            .where(Parcel.user_id.is_(None))
            .values(user_id=user.id)
        )
        return result.rowcount or 0

    async def parcel_counts(self, user_id: int) -> tuple[int, int, int]:
        from app.core.enums import ParcelStatus

        total = await self.session.scalar(select(func.count(Parcel.id)).where(Parcel.user_id == user_id))
        transit = await self.session.scalar(
            select(func.count(Parcel.id)).where(
                Parcel.user_id == user_id, Parcel.status == ParcelStatus.IN_TRANSIT
            )
        )
        delivered = await self.session.scalar(
            select(func.count(Parcel.id)).where(
                Parcel.user_id == user_id, Parcel.status == ParcelStatus.DELIVERED
            )
        )
        return int(total or 0), int(transit or 0), int(delivered or 0)
