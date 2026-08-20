from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Parcel, ParcelStatusHistory


class ParcelRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def by_tracking(self, tracking_number: str) -> Parcel | None:
        return await self.session.scalar(
            select(Parcel).options(selectinload(Parcel.user)).where(Parcel.tracking_number == tracking_number)
        )

    async def for_client(self, client_code: str) -> list[Parcel]:
        rows = await self.session.scalars(
            select(Parcel)
            .where(Parcel.client_code == client_code)
            .order_by(Parcel.status, Parcel.updated_at.desc())
        )
        return list(rows)

    async def add_history(
        self,
        parcel: Parcel,
        old_status,
        new_status,
        changed_by: int | None,
    ) -> ParcelStatusHistory:
        history = ParcelStatusHistory(
            parcel=parcel,
            old_status=old_status,
            new_status=new_status,
            changed_by=changed_by,
        )
        self.session.add(history)
        return history

    async def delete(self, parcel: Parcel) -> None:
        await self.session.delete(parcel)
