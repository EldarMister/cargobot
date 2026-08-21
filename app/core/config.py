from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    bot_token: str = ""
    admin_ids: str = ""

    timezone: str = "Asia/Bishkek"
    log_level: str = "INFO"
    port: int = Field(default=8080, alias="PORT")
    web_app_url: str = ""
    railway_public_domain: str = ""
    database_url_override: str = Field(
        default="postgresql+asyncpg://cargo:cargo@postgres:5432/cargo",
        alias="DATABASE_URL",
    )

    @property
    def database_url(self) -> str:
        for prefix in ("postgres://", "postgresql://", "postgresql+psycopg://"):
            if self.database_url_override.startswith(prefix):
                return self.database_url_override.replace(prefix, "postgresql+asyncpg://", 1)
        return self.database_url_override

    @property
    def sync_database_url(self) -> str:
        return self.database_url.replace("postgresql+asyncpg://", "postgresql+psycopg://")

    @property
    def public_web_url(self) -> str:
        if self.web_app_url:
            return self.web_app_url.rstrip("/")
        if self.railway_public_domain:
            return f"https://{self.railway_public_domain.strip('/')}"
        return ""

    @property
    def admin_id_set(self) -> set[int]:
        result: set[int] = set()
        for value in self.admin_ids.split(","):
            value = value.strip()
            if value:
                try:
                    result.add(int(value))
                except ValueError as exc:
                    raise ValueError(f"ADMIN_IDS contains a non-numeric value: {value}") from exc
        return result


@lru_cache
def get_settings() -> Settings:
    return Settings()
