from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage
from sqlalchemy import func, select

from app.bot.handlers.user.registration import registration_name, registration_phone, update_own_phone
from app.bot.keyboards.user import phone_keyboard
from app.bot.states.user import RegistrationStates
from app.db.models import User
from app.services.normalization import normalize_phone


@pytest.mark.parametrize("raw,expected", [
    ("0555 123 456", "+996555123456"), ("555123456", "+996555123456"),
    ("+996 (555) 123-456", "+996555123456"), ("996555123456", "+996555123456"),
    ("+86 188 1891 3136", "+8618818913136"), ("+44 20 7946 0018", "+442079460018"),
    ("+555014645", ""), ("55501464", ""), ("+0755009390", ""), ("call me 555123456", ""),
])
def test_phone_normalization_preserves_country_and_rejects_incomplete_numbers(raw, expected):
    assert normalize_phone(raw) == expected


def message(text=None, contact_id=None, phone="996555123456"):
    return SimpleNamespace(
        text=text, contact=SimpleNamespace(user_id=contact_id, phone_number=phone) if contact_id else None,
        from_user=SimpleNamespace(id=12345), chat=SimpleNamespace(type="private"), answer=AsyncMock(),
    )


@pytest.mark.parametrize("use_contact", [True, False])
async def test_registration_waits_for_valid_phone_and_checks_contact_owner(session, use_contact):
    storage = MemoryStorage()
    state = FSMContext(storage, StorageKey(bot_id=1, chat_id=12345, user_id=12345))
    await state.update_data(language="ru")
    await registration_name(message(text="Иван Иванов"), state, session)
    assert await state.get_state() == RegistrationStates.phone.state
    assert await session.scalar(select(func.count(User.id))) == 0
    for bad in [message(text="55501464"), message(contact_id=999)]:
        await registration_phone(bad, state, session)
        assert await session.scalar(select(func.count(User.id))) == 0
    good = message(contact_id=12345) if use_contact else message(text="0555 123 456")
    await registration_phone(good, state, session)
    user = await session.scalar(select(User))
    assert user.telegram_id == 12345
    assert user.phone == "+996555123456"
    assert user.full_name == "Иван Иванов"
    assert await state.get_state() is None
    assert phone_keyboard().keyboard[0][0].request_contact is True
    await storage.close()


async def test_existing_client_can_replace_bad_phone_only_with_own_contact(session):
    user = User(client_code="H-853", full_name="Клиент", telegram_id=12345, phone="+55501464")
    session.add(user)
    await session.commit()
    await update_own_phone(message(contact_id=999), session)
    assert user.phone == "+55501464"
    await update_own_phone(message(contact_id=12345), session)
    assert user.phone == "+996555123456"
