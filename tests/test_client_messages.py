from types import SimpleNamespace
from unittest.mock import AsyncMock

from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage

from app.bot.handlers.admin.users import (
    client_message_confirm,
    client_message_preview,
    client_message_start,
)
from app.bot.states.admin import AdminStates
from app.db.models import User


async def test_bot_message_preview_confirmation_and_old_button_cannot_send_to_new_account(session):
    user = User(client_code="H-853", full_name="Клиент", phone="", telegram_id=123456)
    session.add(user)
    await session.commit()
    storage = MemoryStorage()
    state = FSMContext(storage, StorageKey(bot_id=1, chat_id=777, user_id=777))
    bot = AsyncMock()
    bot.send_message.return_value.message_id = 42
    callback = SimpleNamespace(
        data=f"user_message:{user.id}", message=AsyncMock(), answer=AsyncMock(),
        bot=bot, from_user=SimpleNamespace(id=777),
    )
    await client_message_start(callback, state, session)
    assert await state.get_state() == AdminStates.client_message_text.state
    message = SimpleNamespace(text="Груз <прибыл> & ждёт вас", answer=AsyncMock())
    await client_message_preview(message, state, session)
    assert await state.get_state() == AdminStates.client_message_confirm.state
    message.answer.assert_any_await(message.text, parse_mode=None)
    bot.send_message.assert_not_awaited()
    callback.data = f"client_message:send:{(await state.get_data())['client_message_token']}"
    old_confirmation = callback.data
    await client_message_confirm(callback, state, session)
    bot.send_message.assert_awaited_once_with(chat_id=123456, text=message.text, parse_mode=None)
    assert await state.get_state() is None

    callback.data = f"user_message:{user.id}"
    await client_message_start(callback, state, session)
    await client_message_preview(message, state, session)
    callback.data = old_confirmation
    await client_message_confirm(callback, state, session)
    assert await state.get_state() == AdminStates.client_message_confirm.state
    assert bot.send_message.await_count == 1
    user.telegram_id = 987654
    await session.commit()
    callback.data = f"client_message:send:{(await state.get_data())['client_message_token']}"
    await client_message_confirm(callback, state, session)
    assert bot.send_message.await_count == 1
    assert "изменился" in callback.message.answer.call_args.args[0]
    await storage.close()


async def test_bot_message_cancel_does_not_send(session):
    storage = MemoryStorage()
    state = FSMContext(storage, StorageKey(bot_id=1, chat_id=777, user_id=777))
    await state.set_state(AdminStates.client_message_confirm)
    await state.update_data(client_message="Не отправлять", client_message_token="test-token")
    bot = AsyncMock()
    callback = SimpleNamespace(
        data="client_message:cancel:test-token", message=AsyncMock(), answer=AsyncMock(), bot=bot,
    )
    await client_message_confirm(callback, state, session)
    assert await state.get_state() is None
    bot.send_message.assert_not_awaited()
    await storage.close()
