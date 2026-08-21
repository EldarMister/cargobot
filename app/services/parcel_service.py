from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import ParcelStatus
from app.db.models import Parcel
from app.db.repositories import ParcelRepository

STATUS_DATE_FIELD = {
    ParcelStatus.CHINA_WAREHOUSE: "china_received_at",
    ParcelStatus.ARRIVED_COUNTRY: "arrived_at",
    ParcelStatus.LOCAL_WAREHOUSE: "arrived_at",
    ParcelStatus.READY_FOR_PICKUP: "ready_at",
    ParcelStatus.DELIVERED: "delivered_at",
}


@dataclass(frozen=True, slots=True)
class DeliveryDateChanges:
    sent_at: bool = False
    expected_at: bool = False

    @property
    def any(self) -> bool:
        return self.sent_at or self.expected_at


def delivery_datetime_values_equal(current: datetime | None, new: datetime) -> bool:
    if current is None:
        return False
    current_utc = current.replace(tzinfo=UTC) if current.tzinfo is None else current.astimezone(UTC)
    new_utc = new.replace(tzinfo=UTC) if new.tzinfo is None else new.astimezone(UTC)
    return current_utc == new_utc


def apply_delivery_dates(
    parcel: Parcel,
    sent_at: datetime | None = None,
    expected_at: datetime | None = None,
) -> DeliveryDateChanges:
    """Update explicitly supplied delivery dates without clearing existing values."""
    sent_at_changed = bool(
        sent_at is not None and not delivery_datetime_values_equal(parcel.sent_at, sent_at)
    )
    expected_at_changed = bool(
        expected_at is not None and not delivery_datetime_values_equal(parcel.expected_at, expected_at)
    )
    if sent_at_changed:
        parcel.sent_at = sent_at
    if expected_at_changed:
        parcel.expected_at = expected_at
        parcel.approaching_notified_at = None
        parcel.due_notified_at = None
    return DeliveryDateChanges(sent_at=sent_at_changed, expected_at=expected_at_changed)


class ParcelService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.parcels = ParcelRepository(session)

    async def change_status(
        self,
        parcel: Parcel,
        new_status: ParcelStatus,
        changed_by: int | None,
    ) -> bool:
        if parcel.status == new_status:
            return False
        old_status = parcel.status
        parcel.status = new_status
        if new_status == ParcelStatus.IN_TRANSIT:
            parcel.approaching_notified_at = None
            parcel.due_notified_at = None
        date_field = STATUS_DATE_FIELD.get(new_status)
        if date_field and getattr(parcel, date_field) is None:
            setattr(parcel, date_field, datetime.now(UTC))
        await self.parcels.add_history(parcel, old_status, new_status, changed_by)
        await self.session.flush()
        return True
