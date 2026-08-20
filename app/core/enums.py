from enum import StrEnum


class ParcelStatus(StrEnum):
    CHINA_WAREHOUSE = "CHINA_WAREHOUSE"
    PREPARING = "PREPARING"
    IN_TRANSIT = "IN_TRANSIT"
    ARRIVED_COUNTRY = "ARRIVED_COUNTRY"
    LOCAL_WAREHOUSE = "LOCAL_WAREHOUSE"
    READY_FOR_PICKUP = "READY_FOR_PICKUP"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"

    @property
    def label(self) -> str:
        return {
            self.CHINA_WAREHOUSE: "🇨🇳 На складе в Китае",
            self.PREPARING: "📦 Готовится к отправке",
            self.IN_TRANSIT: "🚚 В пути",
            self.ARRIVED_COUNTRY: "🏢 Прибыл",
            self.LOCAL_WAREHOUSE: "🏢 На местном складе",
            self.READY_FOR_PICKUP: "✅ Готов к выдаче",
            self.DELIVERED: "📬 Получен",
            self.CANCELLED: "❌ Отменён",
        }[self]


IMPORT_BATCH_STATUSES = (
    ParcelStatus.CHINA_WAREHOUSE,
    ParcelStatus.PREPARING,
    ParcelStatus.IN_TRANSIT,
    ParcelStatus.ARRIVED_COUNTRY,
    ParcelStatus.READY_FOR_PICKUP,
    ParcelStatus.DELIVERED,
    ParcelStatus.LOCAL_WAREHOUSE,
    ParcelStatus.CANCELLED,
)


class ImportRowResult(StrEnum):
    CREATED = "CREATED"
    UPDATED = "UPDATED"
    UNCHANGED = "UNCHANGED"
    SKIPPED = "SKIPPED"
    ERROR = "ERROR"
