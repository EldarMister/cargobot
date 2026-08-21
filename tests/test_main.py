from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.types import MenuButtonCommands, MenuButtonWebApp

from app.core.config import Settings
from app.main import configure_menu_buttons


@pytest.mark.asyncio
async def test_configure_menu_buttons_keeps_commands_for_clients_and_adds_admin_app():
    bot = AsyncMock()
    settings = Settings(
        _env_file=None,
        BOT_TOKEN="123456:test-token",
        ADMIN_IDS="777,888",
        WEB_APP_URL="https://cargo.example.com",
    )

    await configure_menu_buttons(bot, settings)

    calls = bot.set_chat_menu_button.await_args_list
    assert len(calls) == 3
    assert isinstance(calls[0].kwargs["menu_button"], MenuButtonCommands)
    assert "chat_id" not in calls[0].kwargs
    assert [call.kwargs["chat_id"] for call in calls[1:]] == [777, 888]
    assert all(isinstance(call.kwargs["menu_button"], MenuButtonWebApp) for call in calls[1:])
    assert calls[1].kwargs["menu_button"].web_app.url == "https://cargo.example.com/panel"


@pytest.mark.asyncio
async def test_configure_menu_buttons_skips_admin_app_without_public_url():
    bot = AsyncMock()
    settings = Settings(
        _env_file=None,
        BOT_TOKEN="123456:test-token",
        ADMIN_IDS="777",
    )

    await configure_menu_buttons(bot, settings)

    bot.set_chat_menu_button.assert_awaited_once()
    assert isinstance(
        bot.set_chat_menu_button.await_args.kwargs["menu_button"],
        MenuButtonCommands,
    )


@pytest.mark.asyncio
async def test_configure_menu_buttons_includes_database_admins():
    bot = AsyncMock()
    settings = Settings(
        _env_file=None,
        BOT_TOKEN="123456:test-token",
        ADMIN_IDS="777",
        WEB_APP_URL="https://cargo.example.com",
    )
    session = AsyncMock()
    session.scalars.return_value = [888, 999]
    session_factory = MagicMock()
    session_factory.return_value.__aenter__ = AsyncMock(return_value=session)
    session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

    await configure_menu_buttons(bot, settings, session_factory)

    calls = bot.set_chat_menu_button.await_args_list
    assert [call.kwargs.get("chat_id") for call in calls] == [None, 777, 888, 999]
    assert all(isinstance(call.kwargs["menu_button"], MenuButtonWebApp) for call in calls[1:])
