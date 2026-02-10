from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
import aiosqlite

from bot.db import queries
from bot.keyboards.menus import main_menu, BTN_CREATE_POST, BTN_MY_CHANNELS, BTN_MY_POSTS

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


@router.message(F.text == BTN_MY_CHANNELS)
async def menu_my_channels(message: Message, db: aiosqlite.Connection):
    channels = await queries.get_channels(db, message.from_user.id)
    if not channels:
        await message.answer(
            "У вас пока нет подключённых каналов.\n\n"
            "Чтобы добавить канал:\n"
            "1. Добавьте меня администратором в канал\n"
            "2. Перешлите мне любое сообщение из этого канала",
        )
    else:
        lines = ["<b>Ваши каналы:</b>\n"]
        for ch in channels:
            title = ch["channel_title"]
            username = f" (@{ch['channel_username']})" if ch["channel_username"] else ""
            lines.append(f"• {title}{username}")
        lines.append("\nПерешлите сообщение из канала, чтобы добавить новый.")
        await message.answer("\n".join(lines))


@router.message(F.text == BTN_CREATE_POST)
async def menu_create_post(message: Message, db: aiosqlite.Connection):
    channels = await queries.get_channels(db, message.from_user.id)
    if not channels:
        await message.answer(
            "Сначала подключите хотя бы один канал через «📢 Мои каналы».",
        )
        return
    await message.answer(
        "Создание нового поста будет доступно в следующем обновлении.",
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
