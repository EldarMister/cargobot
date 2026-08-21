from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import ImportRowResult, ParcelStatus
from app.db.models import Import, ImportRow, Parcel, User
from app.services.excel_importer import ExcelParseResult
from app.services.parcel_service import STATUS_DATE_FIELD, apply_delivery_dates


@dataclass(slots=True)
class ParcelNotification:
    telegram_id: int
    tracking_number: str
    client_code: str
    status: ParcelStatus
    is_new: bool
    status_changed: bool = False
    dates_changed: bool = False
    sent_at_changed: bool = False
    expected_at_changed: bool = False
    sent_at: datetime | None = None
    expected_at: datetime | None = None


@dataclass(slots=True)
class ImportOutcome:
    import_record: Import
    notifications: list[ParcelNotification]


class ImportService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def process(
        self,
        parsed: ExcelParseResult,
        filename: str,
        selected_status: ParcelStatus,
        uploaded_by: int,
        sent_at: datetime | None = None,
        expected_at: datetime | None = None,
    ) -> ImportOutcome:
        record = Import(
            filename=filename,
            selected_status=selected_status,
            uploaded_by=uploaded_by,
            sent_at=sent_at,
            expected_at=expected_at,
            total_rows=parsed.total_rows,
            valid_rows=len(parsed.valid_rows),
            skipped_rows=len(parsed.skipped_rows),
            rows=[],
        )
        self.session.add(record)
        await self.session.flush()

        notifications: list[ParcelNotification] = []
        client_codes = {row.client_code for row in parsed.valid_rows if row.client_code}
        tracking_numbers = {row.tracking_number for row in parsed.valid_rows if row.tracking_number}
        users = {
            user.client_code: user
            for user in await self.session.scalars(select(User).where(User.client_code.in_(client_codes)))
        }
        parcels = {
            parcel.tracking_number: parcel
            for parcel in await self.session.scalars(
                select(Parcel).where(Parcel.tracking_number.in_(tracking_numbers))
            )
        }

        for row in parsed.rows:
            if not row.is_valid:
                record.rows.append(
                    ImportRow(
                        row_number=row.row_number,
                        sheet_name=row.sheet_name,
                        tracking_number=row.tracking_number,
                        client_code=row.client_code,
                        result=ImportRowResult.SKIPPED,
                        error=row.error,
                    )
                )
                continue

            user = users.get(row.client_code)
            parcel = parcels.get(row.tracking_number)
            is_new = parcel is None
            status_changed = False
            date_changes = None
            date_field = STATUS_DATE_FIELD.get(selected_status)
            if is_new:
                parcel = Parcel(
                    tracking_number=row.tracking_number,
                    client_code=row.client_code,
                    user_id=user.id if user else None,
                    import_id=record.id,
                    status=selected_status,
                    sent_at=sent_at,
                    expected_at=expected_at,
                )
                if date_field:
                    setattr(parcel, date_field, datetime.now(UTC))
                self.session.add(parcel)
                await self.session.flush()
                parcels[parcel.tracking_number] = parcel
                from app.db.models import ParcelStatusHistory

                self.session.add(
                    ParcelStatusHistory(
                        parcel_id=parcel.id,
                        old_status=None,
                        new_status=selected_status,
                        changed_by=uploaded_by,
                    )
                )
                record.created_rows += 1
                result = ImportRowResult.CREATED
                status_changed = True
            else:
                old_status = parcel.status
                parcel.client_code = row.client_code
                parcel.user_id = user.id if user else None
                parcel.import_id = record.id
                date_changes = apply_delivery_dates(parcel, sent_at, expected_at)
                if old_status != selected_status:
                    parcel.status = selected_status
                    if selected_status == ParcelStatus.IN_TRANSIT:
                        parcel.approaching_notified_at = None
                        parcel.due_notified_at = None
                    if date_field and getattr(parcel, date_field) is None:
                        setattr(parcel, date_field, datetime.now(UTC))
                    from app.db.models import ParcelStatusHistory

                    self.session.add(
                        ParcelStatusHistory(
                            parcel_id=parcel.id,
                            old_status=old_status,
                            new_status=selected_status,
                            changed_by=uploaded_by,
                        )
                    )
                    status_changed = True
                record.updated_rows += 1
                result = (
                    ImportRowResult.UPDATED
                    if status_changed or date_changes.any
                    else ImportRowResult.UNCHANGED
                )

            record.rows.append(
                ImportRow(
                    row_number=row.row_number,
                    sheet_name=row.sheet_name,
                    tracking_number=row.tracking_number,
                    client_code=row.client_code,
                    result=result,
                )
            )
            dates_changed = bool(date_changes and date_changes.any)
            if user and user.telegram_id and (is_new or status_changed or dates_changed):
                notifications.append(
                    ParcelNotification(
                        telegram_id=user.telegram_id,
                        tracking_number=parcel.tracking_number,
                        client_code=parcel.client_code,
                        status=parcel.status,
                        is_new=is_new,
                        status_changed=status_changed,
                        dates_changed=dates_changed,
                        sent_at_changed=bool(date_changes and date_changes.sent_at),
                        expected_at_changed=bool(date_changes and date_changes.expected_at),
                        sent_at=parcel.sent_at,
                        expected_at=parcel.expected_at,
                    )
                )

        await self.session.flush()
        return ImportOutcome(record, notifications)
