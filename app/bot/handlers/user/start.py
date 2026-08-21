from html import escape

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.user import main_menu_keyboard, start_keyboard
from app.db.repositories import SettingRepository, UserRepository

router = Router(name="user_start")


@router.message(CommandStart())
async def start(message: Message, state: FSMContext, session: AsyncSession) -> None:
    await state.clear()
    user = await UserRepository(session).by_telegram_id(message.from_user.id)
    if user and user.is_active:
        await message.answer(
            f"👋 С возвращением, {escape(user.full_name)}!\nВаш код: <b>{user.client_code}</b>",
            parse_mode="HTML",
            reply_markup=main_menu_keyboard(),
        )
        return
    settings = await SettingRepository(session).all()
    company_name = escape(settings["company_name"] or "BCL EXPRESS")
    await message.answer(
        f"👋 <b>Добро пожаловать в {company_name}!</b>\n\n"
        "Если у вас уже есть код клиента — привяжите его.\n"
        "Если вы новый клиент — пройдите регистрацию.",
        parse_mode="HTML",
        reply_markup=start_keyboard(),
    )


@router.message(F.text == "❌ Отмена")
@router.message(Command("cancel"))
async def cancel(message: Message, state: FSMContext, session: AsyncSession) -> None:
    await state.clear()
    user = await UserRepository(session).by_telegram_id(message.from_user.id)
    markup = main_menu_keyboard() if user else start_keyboard()
    await message.answer("Действие отменено.", reply_markup=markup)
