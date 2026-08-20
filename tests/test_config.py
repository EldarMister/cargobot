from app.core.config import Settings


def test_railway_database_url_uses_async_driver():
    settings = Settings(
        _env_file=None,
        DATABASE_URL="postgresql://cargo:secret@postgres.railway.internal:5432/railway",
    )

    assert settings.database_url == (
        "postgresql+asyncpg://cargo:secret@postgres.railway.internal:5432/railway"
    )
    assert settings.sync_database_url == (
        "postgresql+psycopg://cargo:secret@postgres.railway.internal:5432/railway"
    )


def test_legacy_postgres_url_uses_async_driver():
    settings = Settings(_env_file=None, DATABASE_URL="postgres://cargo:secret@host:5432/cargo")

    assert settings.database_url == "postgresql+asyncpg://cargo:secret@host:5432/cargo"
