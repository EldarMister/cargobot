from app.core.config import Settings
from app.web.app import create_web_app


def test_web_panel_registers_public_shell_and_protected_api():
    settings = Settings(
        _env_file=None,
        BOT_TOKEN="123456:test-token",
        ADMIN_IDS="777",
    )
    app = create_web_app(bot=object(), session_factory=None, settings=settings)

    paths = {route.path for route in app.routes}

    assert {
        "/health",
        "/panel",
        "/api/auth/telegram",
        "/api/dashboard",
        "/api/settings",
        "/api/clients/{client_id}/block",
        "/api/clients/{client_id}/parcels",
        "/api/imports/analyze",
        "/api/imports/{import_id}/status",
    } <= paths
