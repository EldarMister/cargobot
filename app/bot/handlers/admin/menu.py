from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, WebAppInfo

from app.bot.keyboards.admin import admin_menu_keyboard
from app.bot.keyboards.user import main_menu_keyboard
from app.core.config import get_settings

router = Router(name="admin_menu")


@router.message(Command("admin"))
async def admin_menu(message: Message, state: FSMContext) -> None:
    await state.clear()
    web_url = get_settings().public_web_url
    await message.answer(
        "🛠 <b>Панель администратора</b>",
        parse_mode="HTML",
        reply_markup=admin_menu_keyboard(),
    )
    if web_url:
        await message.answer(
            "Мобильная панель управления:",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="🌐 Открыть веб-панель",
                            web_app=WebAppInfo(url=f"{web_url}/panel"),
                        )
                    ]
                ]
            ),
        )


@router.message(F.text == "↩️ Меню клиента")
async def client_menu(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Главное меню", reply_markup=main_menu_keyboard())


@router.message(Command("cancel"))
@router.message(F.text == "❌ Отмена")
async def admin_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Действие отменено.", reply_markup=admin_menu_keyboard())
