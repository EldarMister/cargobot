import asyncio
import hashlib
import json
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated, Literal

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import MenuButtonCommands, MenuButtonWebApp, WebAppInfo
from fastapi import (
    Cookie,
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import String, cast, delete, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from app.core.config import Settings
from app.core.dates import as_local, calculate_expected_at, local_timezone
from app.core.enums import ParcelStatus
from app.db.models import AppSetting, Import, ImportRevision, Parcel, User
from app.db.repositories import SettingRepository, UserRepository
from app.services.excel_importer import ExcelImporter
from app.services.import_service import (
    DuplicateImportError,
    ImportBatchConflictError,
    ImportNotFoundError,
    ImportService,
)
from app.services.normalization import (
    is_valid_client_code,
    normalize_client_code,
    normalize_phone,
)
from app.services.notification_service import notify_parcel_status, send_notification
from app.services.parcel_service import ParcelService
from app.web.auth import (
    WebAuthError,
    create_admin_session,
    validate_admin_session,
    validate_telegram_init_data,
)

SESSION_COOKIE = "bcl_admin_session"
MAX_UPLOAD_BYTES = 20 * 1024 * 1024
STATIC_DIR = Path(__file__).with_name("static")


class TelegramAuthRequest(BaseModel):
    init_data: str


class StatusUpdateRequest(BaseModel):
    status: ParcelStatus


class ParcelUpdateRequest(BaseModel):
    client_code: str = Field(min_length=1, max_length=32)
    status: ParcelStatus
    sent_date: str | None = None
    expected_date: str | None = None


class ImportStatusUpdateRequest(BaseModel):
    status: ParcelStatus
    sent_date: str | None = None
    expected_date: str | None = None
    transit_days: int = Field(default=12, ge=1, le=90)


class ClientWriteRequest(BaseModel):
    full_name: str = Field(min_length=3, max_length=255)
    phone: str = Field(min_length=8, max_length=32)
    city: str | None = Field(default=None, max_length=120)
    telegram_id: int | None = None


class ClientCreateRequest(ClientWriteRequest):
    client_code: str | None = Field(default=None, max_length=32)


class ClientBlockRequest(BaseModel):
    mode: Literal["permanent", "temporary", "unblock"]
    days: int = Field(default=1, ge=1, le=365)


class ClientAdminRequest(BaseModel):
    is_admin: bool


class SettingsUpdateRequest(BaseModel):
    company_name: str = Field(min_length=1, max_length=80)
    default_transit_days: int = Field(ge=1, le=90)
    warehouse_receiver: str = Field(default="", max_length=200)
    warehouse_phone: str = Field(default="", max_length=100)
    warehouse_address: str = Field(default="", max_length=1000)
    warehouse_name: str = Field(default="", max_length=200)
    warehouse_receiver_2: str = Field(default="", max_length=200)
    warehouse_phone_2: str = Field(default="", max_length=100)
    warehouse_address_2: str = Field(default="", max_length=1000)
    warehouse_name_2: str = Field(default="", max_length=200)
    support_username: str = Field(default="", max_length=100)
    contact_whatsapp: str = Field(default="", max_length=300)
    local_warehouse_address: str = Field(default="", max_length=1000)
    work_schedule: str = Field(default="", max_length=1000)


def _date(value: datetime | None) -> str | None:
    return as_local(value).strftime("%d.%m.%Y") if value else None


def _date_input(value: datetime | None) -> str | None:
    return as_local(value).strftime("%Y-%m-%d") if value else None


def _parcel_payload(parcel: Parcel) -> dict:
    return {
        "id": parcel.id,
        "tracking_number": parcel.tracking_number,
        "client_code": parcel.client_code,
        "client_name": parcel.user.full_name if parcel.user else None,
        "telegram_linked": bool(parcel.user and parcel.user.telegram_id),
        "status": parcel.status.value,
        "status_label": parcel.status.label,
        "sent_at": _date(parcel.sent_at),
        "expected_at": _date(parcel.expected_at),
        "sent_date": _date_input(parcel.sent_at),
        "expected_date": _date_input(parcel.expected_at),
        "updated_at": as_local(parcel.updated_at).isoformat(),
    }


def _client_payload(user: User, parcel_count: int, system_admin_ids: set[int] | None = None) -> dict:
    blocked_until = user.blocked_until
    blocked_temporarily = bool(blocked_until and not user.has_access())
    is_system_admin = bool(user.telegram_id and user.telegram_id in (system_admin_ids or set()))
    return {
        "id": user.id,
        "client_code": user.client_code,
        "full_name": user.full_name,
        "phone": user.phone,
        "city": user.city,
        "telegram_id": user.telegram_id,
        "language": user.language,
        "is_admin": user.is_admin or is_system_admin,
        "is_system_admin": is_system_admin,
        "parcels": int(parcel_count),
        "is_active": user.is_active,
        "is_blocked": not user.has_access(),
        "block_mode": (
            "permanent" if user.is_active is False else "temporary" if blocked_temporarily else None
        ),
        "blocked_until": as_local(blocked_until).isoformat() if blocked_temporarily else None,
        "blocked_until_text": (
            as_local(blocked_until).strftime("%d.%m.%Y %H:%M") if blocked_temporarily else None
        ),
    }


def _parse_web_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Некорректная дата") from exc
    return parsed.replace(tzinfo=local_timezone()).astimezone(UTC)


def _transit_days(value: str) -> int:
    try:
        days = int(value)
    except ValueError:
        return 12
    return days if 1 <= days <= 90 else 12


def create_web_app(
    bot: Bot,
    session_factory: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> FastAPI:
    app = FastAPI(
        title="BCL EXPRESS Admin",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    async def require_admin(
        session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE),
    ) -> int:
        if not session_token:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Откройте панель через Telegram")
        try:
            telegram_id = validate_admin_session(session_token, settings.bot_token)
        except WebAuthError as exc:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc
        if telegram_id not in settings.admin_id_set:
            async with session_factory() as session:
                delegated = await session.scalar(
                    select(User.is_admin).where(
                        User.telegram_id == telegram_id,
                        User.is_admin.is_(True),
                    )
                )
            if not delegated:
                raise HTTPException(status.HTTP_403_FORBIDDEN, "Нет доступа")
        return telegram_id

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    @app.get("/", include_in_schema=False)
    @app.get("/panel", include_in_schema=False)
    async def panel() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.post("/api/auth/telegram")
    async def telegram_auth(payload: TelegramAuthRequest, response: Response) -> dict:
        try:
            telegram_user = validate_telegram_init_data(payload.init_data, settings.bot_token)
        except WebAuthError as exc:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc
        if telegram_user.telegram_id not in settings.admin_id_set:
            async with session_factory() as session:
                delegated = await session.scalar(
                    select(User.is_admin).where(
                        User.telegram_id == telegram_user.telegram_id,
                        User.is_admin.is_(True),
                    )
                )
            if not delegated:
                raise HTTPException(status.HTTP_403_FORBIDDEN, "Нет доступа к админ-панели")
        session_token = create_admin_session(telegram_user.telegram_id, settings.bot_token)
        response.set_cookie(
            SESSION_COOKIE,
            session_token,
            max_age=12 * 60 * 60,
            httponly=True,
            secure=settings.public_web_url.startswith("https://"),
            samesite="strict",
            path="/",
        )
        return {
            "ok": True,
            "admin": {
                "id": telegram_user.telegram_id,
                "name": telegram_user.first_name,
                "username": telegram_user.username,
            },
        }

    @app.get("/api/meta")
    async def meta(_: int = Depends(require_admin)) -> dict:
        async with session_factory() as session:
            values = await SettingRepository(session).all()
            return {
                "company": values["company_name"] or "BCL EXPRESS",
                "default_transit_days": _transit_days(values["default_transit_days"]),
                "statuses": [{"value": item.value, "label": item.label} for item in ParcelStatus],
            }

    @app.get("/api/settings")
    async def get_settings(_: int = Depends(require_admin)) -> dict:
        async with session_factory() as session:
            values = await SettingRepository(session).all()
            return {
                **values,
                "default_transit_days": _transit_days(values["default_transit_days"]),
            }

    @app.patch("/api/settings")
    async def update_settings(
        payload: SettingsUpdateRequest,
        _: int = Depends(require_admin),
    ) -> dict:
        values = payload.model_dump()
        values = {key: str(value).strip() for key, value in values.items()}
        async with session_factory() as session:
            repository = SettingRepository(session)
            for key, value in values.items():
                await repository.set(key, value)
            await session.commit()
        return {
            "ok": True,
            **values,
            "default_transit_days": _transit_days(values["default_transit_days"]),
        }

    @app.delete("/api/settings/warehouses/{slot}")
    async def delete_warehouse(slot: int, _: int = Depends(require_admin)) -> dict:
        if slot not in {1, 2}:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Склад не найден")
        async with session_factory() as session:
            values = await SettingRepository(session).clear_warehouse(slot)
            await session.commit()
        return {
            "ok": True,
            **values,
            "default_transit_days": _transit_days(values["default_transit_days"]),
        }

    @app.get("/api/dashboard")
    async def dashboard(_: int = Depends(require_admin)) -> dict:
        async with session_factory() as session:
            total_clients = int(await session.scalar(select(func.count(User.id))) or 0)
            linked_clients = int(
                await session.scalar(select(func.count(User.id)).where(User.telegram_id.is_not(None))) or 0
            )
            total_parcels = int(await session.scalar(select(func.count(Parcel.id))) or 0)
            in_transit = int(
                await session.scalar(
                    select(func.count(Parcel.id)).where(Parcel.status == ParcelStatus.IN_TRANSIT)
                )
                or 0
            )
            arrived = int(
                await session.scalar(
                    select(func.count(Parcel.id)).where(
                        Parcel.status.in_(
                            {
                                ParcelStatus.ARRIVED_COUNTRY,
                                ParcelStatus.LOCAL_WAREHOUSE,
                                ParcelStatus.READY_FOR_PICKUP,
                            }
                        )
                    )
                )
                or 0
            )
            status_rows = await session.execute(
                select(Parcel.status, func.count(Parcel.id)).group_by(Parcel.status)
            )
            return {
                "total_clients": total_clients,
                "linked_clients": linked_clients,
                "total_parcels": total_parcels,
                "in_transit": in_transit,
                "arrived": arrived,
                "status_counts": {
                    parcel_status.value: int(count) for parcel_status, count in status_rows.all()
                },
            }

    @app.get("/api/parcels")
    async def parcels(
        query: str = "",
        parcel_status: ParcelStatus | None = None,
        _: int = Depends(require_admin),
    ) -> list[dict]:
        async with session_factory() as session:
            statement = (
                select(Parcel)
                .options(selectinload(Parcel.user))
                .order_by(Parcel.updated_at.desc())
            )
            if query.strip():
                pattern = f"%{query.strip()}%"
                statement = statement.where(
                    or_(
                        Parcel.tracking_number.ilike(pattern),
                        Parcel.client_code.ilike(pattern),
                    )
                )
            if parcel_status:
                statement = statement.where(Parcel.status == parcel_status)
            rows = list(await session.scalars(statement))
            return [_parcel_payload(parcel) for parcel in rows]

    @app.patch("/api/parcels/{parcel_id}/status")
    async def update_parcel_status(
        parcel_id: int,
        payload: StatusUpdateRequest,
        admin_id: int = Depends(require_admin),
    ) -> dict:
        async with session_factory() as session:
            parcel = await session.scalar(
                select(Parcel).options(selectinload(Parcel.user)).where(Parcel.id == parcel_id)
            )
            if not parcel:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Товар не найден")
            changed = await ParcelService(session).change_status(parcel, payload.status, admin_id)
            if changed:
                await session.commit()
                notified = await notify_parcel_status(bot, parcel, status_changed=True)
            else:
                notified = False
            return {"parcel": _parcel_payload(parcel), "changed": changed, "notified": notified}

    @app.patch("/api/parcels/{parcel_id}")
    async def update_parcel(
        parcel_id: int,
        payload: ParcelUpdateRequest,
        admin_id: int = Depends(require_admin),
    ) -> dict:
        if not is_valid_client_code(payload.client_code):
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "Код клиента должен быть в формате H-801",
            )
        sent_at = _parse_web_date(payload.sent_date)
        expected_at = _parse_web_date(payload.expected_date)
        if sent_at and expected_at and expected_at < sent_at:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "Ожидаемая дата не может быть раньше даты выезда",
            )
        client_code = normalize_client_code(payload.client_code)
        async with session_factory() as session:
            parcel = await session.scalar(
                select(Parcel).options(selectinload(Parcel.user)).where(Parcel.id == parcel_id)
            )
            if not parcel:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Товар не найден")

            old_sent_at = parcel.sent_at
            old_expected_at = parcel.expected_at
            old_client_code = parcel.client_code
            status_changed = await ParcelService(session).change_status(
                parcel,
                payload.status,
                admin_id,
            )
            parcel.client_code = client_code
            parcel.user = await UserRepository(session).by_client_code(client_code)
            parcel.sent_at = sent_at
            parcel.expected_at = expected_at
            dates_changed = old_sent_at != sent_at or old_expected_at != expected_at
            client_changed = old_client_code != client_code
            if old_expected_at != expected_at:
                parcel.approaching_notified_at = None
                parcel.due_notified_at = None
            await session.commit()
            parcel = await session.scalar(
                select(Parcel).options(selectinload(Parcel.user)).where(Parcel.id == parcel_id)
            )
            notified = False
            if status_changed or dates_changed or client_changed:
                notified = await notify_parcel_status(
                    bot,
                    parcel,
                    status_changed=status_changed or client_changed,
                    dates_changed=dates_changed,
                    sent_at_changed=old_sent_at != sent_at,
                    expected_at_changed=old_expected_at != expected_at,
                )
            return {
                "parcel": _parcel_payload(parcel),
                "changed": status_changed or dates_changed or client_changed,
                "notified": notified,
            }

    @app.delete("/api/parcels/{parcel_id}")
    async def delete_parcel(
        parcel_id: int,
        _: int = Depends(require_admin),
    ) -> dict:
        async with session_factory() as session:
            parcel = await session.get(Parcel, parcel_id)
            if not parcel:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Товар не найден")
            await session.delete(parcel)
            await session.commit()
        return {"ok": True, "id": parcel_id}

    @app.get("/api/clients")
    async def clients(query: str = "", _: int = Depends(require_admin)) -> list[dict]:
        async with session_factory() as session:
            statement = (
                select(User, func.count(Parcel.id))
                .outerjoin(Parcel, Parcel.client_code == User.client_code)
                .group_by(User.id)
                .order_by(User.updated_at.desc())
                .limit(150)
            )
            if query.strip():
                pattern = f"%{query.strip()}%"
                statement = statement.where(
                    or_(
                        User.client_code.ilike(pattern),
                        User.full_name.ilike(pattern),
                        User.phone.ilike(pattern),
                        cast(User.telegram_id, String).ilike(pattern),
                    )
                )
            rows = (await session.execute(statement)).all()
            return [
                _client_payload(user, parcel_count, settings.admin_id_set)
                for user, parcel_count in rows
            ]

    @app.post("/api/clients")
    async def create_client(
        payload: ClientCreateRequest,
        _: int = Depends(require_admin),
    ) -> dict:
        full_name = " ".join(payload.full_name.split())
        phone = normalize_phone(payload.phone)
        if len(full_name) < 3 or len(phone) < 8:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Проверьте ФИО и телефон")
        async with session_factory() as session:
            repository = UserRepository(session)
            if payload.client_code:
                if not is_valid_client_code(payload.client_code):
                    raise HTTPException(
                        status.HTTP_422_UNPROCESSABLE_ENTITY,
                        "Код клиента должен быть в формате H-801",
                    )
                client_code = normalize_client_code(payload.client_code)
            else:
                client_code = f"H-{await repository.next_client_number()}"
            user = User(
                client_code=client_code,
                full_name=full_name,
                phone=phone,
                city=" ".join(payload.city.split()) if payload.city else None,
                telegram_id=payload.telegram_id,
            )
            session.add(user)
            try:
                await session.flush()
                await repository.attach_parcels(user)
                await session.commit()
            except IntegrityError as exc:
                await session.rollback()
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    "H-код или Telegram ID уже используется",
                ) from exc
            parcel_count = int(
                await session.scalar(
                    select(func.count(Parcel.id)).where(Parcel.client_code == user.client_code)
                )
                or 0
            )
            return _client_payload(user, parcel_count, settings.admin_id_set)

    @app.patch("/api/clients/{client_id}")
    async def update_client(
        client_id: int,
        payload: ClientWriteRequest,
        _: int = Depends(require_admin),
    ) -> dict:
        full_name = " ".join(payload.full_name.split())
        phone = normalize_phone(payload.phone)
        if len(full_name) < 3 or len(phone) < 8:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Проверьте ФИО и телефон")
        async with session_factory() as session:
            user = await session.get(User, client_id)
            if not user:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Клиент не найден")
            user.full_name = full_name
            user.phone = phone
            user.city = " ".join(payload.city.split()) if payload.city else None
            user.telegram_id = payload.telegram_id
            try:
                await session.commit()
            except IntegrityError as exc:
                await session.rollback()
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    "Этот Telegram ID уже привязан к другому клиенту",
                ) from exc
            parcel_count = int(
                await session.scalar(
                    select(func.count(Parcel.id)).where(Parcel.client_code == user.client_code)
                )
                or 0
            )
            return _client_payload(user, parcel_count, settings.admin_id_set)

    @app.post("/api/clients/{client_id}/block")
    async def block_client(
        client_id: int,
        payload: ClientBlockRequest,
        _: int = Depends(require_admin),
    ) -> dict:
        async with session_factory() as session:
            user = await session.get(User, client_id)
            if not user:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Клиент не найден")
            if payload.mode == "permanent":
                user.is_active = False
                user.blocked_until = None
            elif payload.mode == "temporary":
                user.is_active = True
                user.blocked_until = datetime.now(UTC) + timedelta(days=payload.days)
            else:
                user.is_active = True
                user.blocked_until = None
            await session.commit()
            parcel_count = int(
                await session.scalar(
                    select(func.count(Parcel.id)).where(Parcel.client_code == user.client_code)
                )
                or 0
            )
            return _client_payload(user, parcel_count, settings.admin_id_set)

    @app.post("/api/clients/{client_id}/admin")
    async def set_client_admin(
        client_id: int,
        payload: ClientAdminRequest,
        _: int = Depends(require_admin),
    ) -> dict:
        async with session_factory() as session:
            user = await session.get(User, client_id)
            if not user:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Клиент не найден")
            if not user.telegram_id:
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    "Сначала привяжите Telegram ID клиента",
                )
            if user.telegram_id in settings.admin_id_set and not payload.is_admin:
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    "Главного администратора нельзя лишить доступа из панели",
                )
            user.is_admin = payload.is_admin
            await session.commit()

            try:
                if payload.is_admin and settings.public_web_url:
                    menu_button = MenuButtonWebApp(
                        text="Админ-панель",
                        web_app=WebAppInfo(url=f"{settings.public_web_url}/panel"),
                    )
                else:
                    menu_button = MenuButtonCommands()
                await bot.set_chat_menu_button(chat_id=user.telegram_id, menu_button=menu_button)
            except TelegramAPIError:
                pass

            parcel_count = int(
                await session.scalar(
                    select(func.count(Parcel.id)).where(Parcel.client_code == user.client_code)
                )
                or 0
            )
            return _client_payload(user, parcel_count, settings.admin_id_set)

    @app.get("/api/clients/{client_id}/parcels")
    async def client_parcels(
        client_id: int,
        _: int = Depends(require_admin),
    ) -> list[dict]:
        async with session_factory() as session:
            user = await session.get(User, client_id)
            if not user:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Клиент не найден")
            rows = list(
                await session.scalars(
                    select(Parcel)
                    .options(selectinload(Parcel.user))
                    .where(Parcel.client_code == user.client_code)
                    .order_by(Parcel.updated_at.desc())
                )
            )
            return [_parcel_payload(parcel) for parcel in rows]

    @app.get("/api/imports")
    async def imports(_: int = Depends(require_admin)) -> list[dict]:
        async with session_factory() as session:
            rows = list(await session.scalars(select(Import).order_by(Import.created_at.desc()).limit(50)))
            return [
                {
                    "id": item.id,
                    "filename": item.filename,
                    "status": item.selected_status.value,
                    "status_label": item.selected_status.label,
                    "sent_at": _date(item.sent_at),
                    "expected_at": _date(item.expected_at),
                    "sent_date": _date_input(item.sent_at),
                    "expected_date": _date_input(item.expected_at),
                    "created_rows": item.created_rows,
                    "updated_rows": item.updated_rows,
                    "skipped_rows": item.skipped_rows,
                    "created_at": as_local(item.created_at).isoformat(),
                }
                for item in rows
            ]

    @app.post("/api/imports/analyze")
    async def analyze_import(
        file: Annotated[UploadFile, File()],
        _: int = Depends(require_admin),
    ) -> dict:
        filename = Path(file.filename or "import").name
        suffix = Path(filename).suffix.lower()
        if suffix not in {".xls", ".xlsx"}:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Нужен файл .xls или .xlsx")
        content = await file.read(MAX_UPLOAD_BYTES + 1)
        if len(content) > MAX_UPLOAD_BYTES:
            raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "Файл больше 20 МБ")
        file_hash = hashlib.sha256(content).hexdigest()
        async with session_factory() as session:
            duplicate = await session.execute(
                select(Import.id, Import.filename)
                .join(ImportRevision, ImportRevision.import_id == Import.id)
                .where(ImportRevision.file_hash == file_hash)
            )
            duplicate_row = duplicate.first()
            if duplicate_row:
                return {
                    "duplicate": {
                        "import_id": duplicate_row.id,
                        "filename": duplicate_row.filename,
                    },
                    "suggestion": None,
                }
            with tempfile.TemporaryDirectory(prefix="bcl_web_analyze_") as temp_dir:
                path = Path(temp_dir) / f"upload{suffix}"
                path.write_bytes(content)
                parsed = await asyncio.to_thread(ExcelImporter().parse, path)
            suggestion = await ImportService(session).find_similar_import(parsed, filename)
            return {
                "duplicate": None,
                "suggestion": (
                    {
                        "import_id": suggestion.import_id,
                        "filename": suggestion.filename,
                        "overlap": suggestion.overlap,
                        "uploaded_rows": suggestion.uploaded_rows,
                        "batch_rows": suggestion.batch_rows,
                        "similarity": round(suggestion.similarity, 4),
                    }
                    if suggestion
                    else None
                ),
            }

    @app.post("/api/imports")
    async def upload_import(
        file: Annotated[UploadFile, File()],
        selected_status: Annotated[ParcelStatus, Form()],
        sent_date: Annotated[str | None, Form()] = None,
        transit_days: Annotated[int, Form()] = 12,
        target_import_id: Annotated[int | None, Form()] = None,
        admin_id: int = Depends(require_admin),
    ) -> dict:
        filename = Path(file.filename or "import").name
        suffix = Path(filename).suffix.lower()
        if suffix not in {".xls", ".xlsx"}:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Нужен файл .xls или .xlsx")
        content = await file.read(MAX_UPLOAD_BYTES + 1)
        if len(content) > MAX_UPLOAD_BYTES:
            raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "Файл больше 20 МБ")
        file_hash = hashlib.sha256(content).hexdigest()
        sent_at = _parse_web_date(sent_date)
        expected_at = None
        if selected_status == ParcelStatus.IN_TRANSIT:
            if not sent_at:
                sent_at = (
                    datetime.now(local_timezone())
                    .replace(hour=0, minute=0, second=0, microsecond=0)
                    .astimezone(UTC)
                )
            try:
                expected_at = calculate_expected_at(sent_at, transit_days)
            except ValueError as exc:
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    "Срок должен быть от 1 до 90 дней",
                ) from exc
        with tempfile.TemporaryDirectory(prefix="bcl_web_import_") as temp_dir:
            path = Path(temp_dir) / f"upload{suffix}"
            path.write_bytes(content)
            parsed = await asyncio.to_thread(ExcelImporter().parse, path)
        async with session_factory() as session:
            try:
                outcome = await ImportService(session).process(
                    parsed,
                    filename,
                    selected_status,
                    admin_id,
                    sent_at=sent_at,
                    expected_at=expected_at,
                    target_import_id=target_import_id,
                    file_hash=file_hash,
                    auto_match=False,
                )
                await session.commit()
            except DuplicateImportError as exc:
                await session.rollback()
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    f"Этот Excel уже загружен в партию №{exc.import_id}",
                ) from exc
            except ImportNotFoundError as exc:
                await session.rollback()
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Партия не найдена") from exc
            except ImportBatchConflictError as exc:
                await session.rollback()
                preview = ", ".join(exc.tracking_numbers[:3])
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    f"Товары уже находятся в другой партии: {preview}",
                ) from exc
            except IntegrityError as exc:
                await session.rollback()
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    "Этот Excel уже был загружен",
                ) from exc
            delivered = 0
            for event in outcome.notifications:
                delivered += int(await send_notification(bot, event))
            record = outcome.import_record
            return {
                "id": record.id,
                "filename": filename,
                "created": record.created_rows,
                "updated": record.updated_rows,
                "skipped": record.skipped_rows,
                "notifications": delivered,
                "is_revision": outcome.is_revision,
            }

    @app.delete("/api/imports/{import_id}")
    async def delete_import(
        import_id: int,
        delete_parcels: bool = False,
        _: int = Depends(require_admin),
    ) -> dict:
        async with session_factory() as session:
            record = await session.get(Import, import_id)
            if not record:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Партия не найдена")
            parcel_count = int(
                await session.scalar(
                    select(func.count(Parcel.id)).where(Parcel.import_id == import_id)
                )
                or 0
            )
            if delete_parcels:
                await session.execute(delete(Parcel).where(Parcel.import_id == import_id))
            else:
                await session.execute(
                    update(Parcel).where(Parcel.import_id == import_id).values(import_id=None)
                )
            await session.delete(record)
            await session.commit()
            return {
                "ok": True,
                "id": import_id,
                "detached_parcels": 0 if delete_parcels else parcel_count,
                "deleted_parcels": parcel_count if delete_parcels else 0,
            }

    @app.post("/api/imports/{import_id}/arrived")
    async def mark_import_arrived(
        import_id: int,
        admin_id: int = Depends(require_admin),
    ) -> dict:
        async with session_factory() as session:
            changed = await ParcelService(session).mark_import_arrived(import_id, admin_id)
            if not changed:
                raise HTTPException(status.HTTP_409_CONFLICT, "Партия уже обновлена")
            await session.commit()
            notified = 0
            for parcel in changed:
                notified += int(await notify_parcel_status(bot, parcel, status_changed=True))
            return {"updated": len(changed), "notifications": notified}

    @app.patch("/api/imports/{import_id}/status")
    async def update_import_status(
        import_id: int,
        payload: ImportStatusUpdateRequest,
        admin_id: int = Depends(require_admin),
    ) -> dict:
        async with session_factory() as session:
            import_record = await session.get(Import, import_id)
            if not import_record:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Партия не найдена")
            sent_at = _parse_web_date(payload.sent_date)
            expected_at = _parse_web_date(payload.expected_date)
            if payload.status == ParcelStatus.IN_TRANSIT and not sent_at:
                sent_at = import_record.sent_at or (
                    datetime.now(local_timezone())
                    .replace(hour=0, minute=0, second=0, microsecond=0)
                    .astimezone(UTC)
                )
            if payload.status == ParcelStatus.IN_TRANSIT and not expected_at:
                expected_at = calculate_expected_at(sent_at, payload.transit_days)
            if sent_at and expected_at and expected_at < sent_at:
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    "Ожидаемая дата не может быть раньше даты выезда",
                )
            record, changed = await ParcelService(session).change_import_status(
                import_id,
                payload.status,
                admin_id,
                sent_at=sent_at,
                expected_at=expected_at,
            )
            await session.commit()
            notified = 0
            for parcel in changed:
                notified += int(await notify_parcel_status(bot, parcel, status_changed=True))
            return {
                "id": record.id,
                "status": record.selected_status.value,
                "status_label": record.selected_status.label,
                "sent_at": _date(record.sent_at),
                "expected_at": _date(record.expected_at),
                "sent_date": _date_input(record.sent_at),
                "expected_date": _date_input(record.expected_at),
                "updated": len(changed),
                "notifications": notified,
            }

    async def database_version() -> str:
        async with session_factory() as session:
            values = await session.execute(
                select(
                    select(func.max(Parcel.updated_at)).scalar_subquery(),
                    select(func.max(User.updated_at)).scalar_subquery(),
                    select(func.max(Import.updated_at)).scalar_subquery(),
                )
            )
            settings_rows = await session.execute(
                select(AppSetting.key, AppSetting.value).order_by(AppSetting.key)
            )
            return json.dumps(
                [*values.one(), settings_rows.all()],
                default=str,
                ensure_ascii=False,
            )

    @app.get("/api/events")
    async def events(request: Request, _: int = Depends(require_admin)) -> StreamingResponse:
        async def stream():
            last_version = ""
            keepalive = 0
            while not await request.is_disconnected():
                version = await database_version()
                if version != last_version:
                    last_version = version
                    yield f"event: change\ndata: {version}\n\n"
                    keepalive = 0
                else:
                    keepalive += 1
                    if keepalive >= 8:
                        yield ": keepalive\n\n"
                        keepalive = 0
                await asyncio.sleep(2)

        return StreamingResponse(
            stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    return app
