from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
import aiosqlite

from bot.db import queries
from bot.keyboards.menus import main_menu

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, db: aiosqlite.Connection, state: FSMContext):
    await state.clear()
    await queries.upsert_user(db, message.from_user.id, message.from_user.username)
    await message.answer(
        "Привет! Я бот для публикации постов в Telegram-каналы.\n\n"
        "Что я умею:\n"
        "• Создавать посты с текстом и кнопками\n"
        "• Публиковать их в ваши каналы\n\n"
        "Для начала добавьте меня администратором в ваш канал, "
        "а затем подключите канал через меню.",
        reply_markup=main_menu(),
    )
