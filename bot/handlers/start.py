from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
import aiosqlite

from bot.db import queries
from bot.keyboards.menus import main_menu, BTN_MY_POSTS

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


@router.message(F.text == BTN_MY_POSTS)
async def menu_my_posts(message: Message, db: aiosqlite.Connection):
    count = await queries.count_posts(db, message.from_user.id)
    if count == 0:
        await message.answer("У вас пока нет созданных постов.")
    else:
        await message.answer(
            f"У вас {count} пост(ов). Управление постами будет доступно в следующем обновлении.",
        )
