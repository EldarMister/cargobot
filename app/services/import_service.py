from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums import ImportRowResult, ParcelStatus
from app.db.models import Import, ImportRevision, ImportRow, Parcel, User
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
    language: str = "ru"


@dataclass(slots=True)
class ImportOutcome:
    import_record: Import
    notifications: list[ParcelNotification]
    is_revision: bool = False


@dataclass(slots=True)
class ImportSuggestion:
    import_id: int
    filename: str
    overlap: int
    uploaded_rows: int
    batch_rows: int
    similarity: float


class DuplicateImportError(ValueError):
    def __init__(self, import_id: int):
        super().__init__("This Excel file has already been uploaded")
        self.import_id = import_id


class ImportNotFoundError(ValueError):
    pass


class ImportBatchConflictError(ValueError):
    def __init__(self, tracking_numbers: list[str]):
        super().__init__("Some shipments already belong to another batch")
        self.tracking_numbers = tracking_numbers


class ImportService:
    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _normalized_filename(filename: str) -> str:
        stem = Path(filename).stem.casefold().strip()
        return re.sub(r"[\s_-]*(?:copy|копия|\(\d+\))$", "", stem).strip()

    async def find_similar_import(
        self,
        parsed: ExcelParseResult,
        filename: str,
    ) -> ImportSuggestion | None:
        tracking_numbers = {row.tracking_number for row in parsed.valid_rows if row.tracking_number}
        if not tracking_numbers:
            return None

        overlap_rows = list(
            (
                await self.session.execute(
                    select(Import, func.count(Parcel.id))
                    .join(Parcel, Parcel.import_id == Import.id)
                    .where(Parcel.tracking_number.in_(tracking_numbers))
                    .group_by(Import.id)
                )
            ).all()
        )
        if not overlap_rows:
            return None

        import_ids = [record.id for record, _ in overlap_rows]
        batch_sizes = dict(
            (
                await self.session.execute(
                    select(Parcel.import_id, func.count(Parcel.id))
                    .where(Parcel.import_id.in_(import_ids))
                    .group_by(Parcel.import_id)
                )
            ).all()
        )
        normalized_name = self._normalized_filename(filename)
        suggestions: list[tuple[bool, float, int, ImportSuggestion]] = []
        for record, overlap_value in overlap_rows:
            overlap = int(overlap_value)
            batch_rows = int(batch_sizes.get(record.id, 0))
            union = len(tracking_numbers) + batch_rows - overlap
            similarity = overlap / union if union else 0.0
            name_matches = self._normalized_filename(record.filename) == normalized_name
            suggestion = ImportSuggestion(
                import_id=record.id,
                filename=record.filename,
                overlap=overlap,
                uploaded_rows=len(tracking_numbers),
                batch_rows=batch_rows,
                similarity=similarity,
            )
            suggestions.append((name_matches, similarity, overlap, suggestion))

        name_matches, similarity, overlap, best = max(suggestions, key=lambda item: item[:3])
        uploaded_coverage = overlap / len(tracking_numbers)
        if similarity >= 0.5 or uploaded_coverage >= 0.7 or (name_matches and uploaded_coverage >= 0.25):
            return best
        return None

    async def process(
        self,
        parsed: ExcelParseResult,
        filename: str,
        selected_status: ParcelStatus,
        uploaded_by: int,
        sent_at: datetime | None = None,
        expected_at: datetime | None = None,
        target_import_id: int | None = None,
        file_hash: str | None = None,
        auto_match: bool = True,
    ) -> ImportOutcome:
        if file_hash:
            duplicate_import_id = await self.session.scalar(
                select(ImportRevision.import_id).where(ImportRevision.file_hash == file_hash)
            )
            if duplicate_import_id is not None:
                raise DuplicateImportError(duplicate_import_id)

        if target_import_id is None and auto_match:
            suggestion = await self.find_similar_import(parsed, filename)
            target_import_id = suggestion.import_id if suggestion else None

        is_revision = target_import_id is not None
        if target_import_id is not None:
            record = await self.session.scalar(
                select(Import)
                .options(selectinload(Import.rows))
                .where(Import.id == target_import_id)
                .with_for_update()
            )
            if record is None:
                raise ImportNotFoundError(f"Import {target_import_id} was not found")
            record.rows.clear()
            record.filename = filename
            record.selected_status = selected_status
            record.uploaded_by = uploaded_by
            record.sent_at = sent_at
            record.expected_at = expected_at
            record.total_rows = parsed.total_rows
            record.valid_rows = len(parsed.valid_rows)
            record.created_rows = 0
            record.updated_rows = 0
            record.skipped_rows = len(parsed.skipped_rows)
        else:
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
        conflicts = sorted(
            parcel.tracking_number
            for parcel in parcels.values()
            if parcel.import_id is not None and parcel.import_id != record.id
        )
        if conflicts:
            raise ImportBatchConflictError(conflicts)

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
            if (
                user
                and user.telegram_id
                and user.has_access()
                and (is_new or status_changed or dates_changed)
            ):
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
                        language=user.language or "ru",
                    )
                )

        if file_hash:
            self.session.add(
                ImportRevision(
                    import_id=record.id,
                    filename=filename,
                    file_hash=file_hash,
                    uploaded_by=uploaded_by,
                    total_rows=record.total_rows,
                    valid_rows=record.valid_rows,
                    created_rows=record.created_rows,
                    updated_rows=record.updated_rows,
                    skipped_rows=record.skipped_rows,
                )
            )
        await self.session.flush()
        return ImportOutcome(record, notifications, is_revision=is_revision)
