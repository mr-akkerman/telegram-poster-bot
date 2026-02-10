import logging
from html import escape

from aiogram import Router, F, Bot
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
import aiosqlite

from bot.db import queries
from bot.keyboards.menus import BTN_MY_CHANNELS

router = Router()
logger = logging.getLogger(__name__)

CALLBACK_PREFIX_DELETE = "ch_del:"
CALLBACK_CONFIRM_DELETE = "ch_confirm_del:"
CALLBACK_CANCEL_DELETE = "ch_cancel_del"
CALLBACK_ADD_CHANNEL = "ch_add"


def _channels_keyboard(channels: list) -> InlineKeyboardMarkup:
    buttons = []
    for ch in channels:
        title = ch["channel_title"]
        username = f" (@{ch['channel_username']})" if ch["channel_username"] else ""
        buttons.append([
            InlineKeyboardButton(text=f"{title}{username}", callback_data=f"ch_noop:{ch['id']}"),
            InlineKeyboardButton(text="🗑", callback_data=f"{CALLBACK_PREFIX_DELETE}{ch['id']}"),
        ])
    buttons.append([InlineKeyboardButton(text="➕ Добавить канал", callback_data=CALLBACK_ADD_CHANNEL)])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ── Show channels list ─────────────────────────────────────────────────────

@router.message(F.text == BTN_MY_CHANNELS)
async def menu_my_channels(message: Message, db: aiosqlite.Connection):
    channels = await queries.get_channels(db, message.from_user.id)
    if not channels:
        await message.answer(
            "У вас пока нет подключённых каналов.\n\n"
            "Чтобы добавить канал:\n"
            "1. Добавьте меня администратором в канал\n"
            "2. Перешлите мне любое сообщение из этого канала\n\n"
            "Или отправьте @username канала.",
        )
    else:
        await message.answer(
            "<b>Ваши каналы:</b>",
            reply_markup=_channels_keyboard(channels),
        )


@router.callback_query(F.data == CALLBACK_ADD_CHANNEL)
async def cb_add_channel(callback: CallbackQuery):
    await callback.message.answer(
        "Чтобы добавить канал:\n"
        "1. Добавьте меня администратором в канал с правом публикации\n"
        "2. Перешлите мне любое сообщение из этого канала\n\n"
        "Или отправьте @username канала.",
    )
    await callback.answer()


# ── Add channel via forwarded message ──────────────────────────────────────

@router.message(F.forward_from_chat)
async def handle_forwarded_from_channel(message: Message, db: aiosqlite.Connection, bot: Bot):
    chat = message.forward_from_chat
    if chat.type != ChatType.CHANNEL:
        await message.answer("Это не канал. Перешлите сообщение именно из канала.")
        return
    await _try_add_channel(message, db, bot, chat.id)


# ── Add channel via @username ──────────────────────────────────────────────

@router.message(F.text.startswith("@"))
async def handle_channel_username(message: Message, db: aiosqlite.Connection, bot: Bot):
    username = message.text.strip()
    try:
        chat = await bot.get_chat(username)
    except Exception:
        await message.answer(f"Не удалось найти канал {username}. Проверьте правильность username.")
        return
    if chat.type != ChatType.CHANNEL:
        await message.answer("Это не канал. Отправьте @username именно канала.")
        return
    await _try_add_channel(message, db, bot, chat.id)


# ── Shared add logic ──────────────────────────────────────────────────────

async def _try_add_channel(message: Message, db: aiosqlite.Connection, bot: Bot, channel_id: int):
    # Check that the USER is admin/creator of the channel
    try:
        user_member = await bot.get_chat_member(channel_id, message.from_user.id)
    except Exception:
        await message.answer(
            "Не удалось проверить ваши права в канале. "
            "Убедитесь, что канал существует и вы являетесь его администратором.",
        )
        return

    if user_member.status not in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR):
        await message.answer(
            "Вы не являетесь администратором этого канала.\n"
            "Добавить можно только каналы, в которых вы — администратор.",
        )
        return

    # Check bot is admin in the channel
    try:
        bot_member = await bot.get_chat_member(channel_id, bot.id)
    except Exception:
        await message.answer(
            "Я не могу получить информацию о канале. "
            "Убедитесь, что я добавлен в канал как администратор.",
        )
        return

    if bot_member.status not in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR):
        await message.answer(
            "Я не являюсь администратором этого канала.\n"
            "Добавьте меня администратором с правом публикации и попробуйте снова.",
        )
        return

    # Get channel info
    try:
        chat = await bot.get_chat(channel_id)
    except Exception:
        await message.answer("Не удалось получить информацию о канале.")
        return

    added = await queries.add_channel(
        db,
        user_id=message.from_user.id,
        channel_id=channel_id,
        title=chat.title or "Без названия",
        username=chat.username,
    )

    if added:
        title = escape(chat.title or "Без названия")
        await message.answer(f"✅ Канал «{title}» успешно добавлен!")
    else:
        await message.answer("Этот канал уже добавлен.")


# ── Delete channel ─────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith(CALLBACK_PREFIX_DELETE))
async def cb_delete_channel(callback: CallbackQuery):
    channel_db_id = callback.data.split(":")[1]
    await callback.message.edit_text(
        "Вы уверены, что хотите удалить этот канал?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"{CALLBACK_CONFIRM_DELETE}{channel_db_id}"),
                InlineKeyboardButton(text="❌ Отмена", callback_data=CALLBACK_CANCEL_DELETE),
            ]
        ]),
    )
    await callback.answer()


@router.callback_query(F.data.startswith(CALLBACK_CONFIRM_DELETE))
async def cb_confirm_delete_channel(callback: CallbackQuery, db: aiosqlite.Connection):
    channel_db_id = int(callback.data.split(":")[1])
    deleted = await queries.delete_channel(db, channel_db_id, callback.from_user.id)

    if deleted:
        await callback.message.edit_text("✅ Канал удалён.")
    else:
        await callback.message.edit_text("Канал не найден или уже удалён.")
    await callback.answer()


@router.callback_query(F.data == CALLBACK_CANCEL_DELETE)
async def cb_cancel_delete(callback: CallbackQuery, db: aiosqlite.Connection):
    channels = await queries.get_channels(db, callback.from_user.id)
    if channels:
        await callback.message.edit_text(
            "<b>Ваши каналы:</b>",
            reply_markup=_channels_keyboard(channels),
        )
    else:
        await callback.message.edit_text("У вас нет подключённых каналов.")
    await callback.answer()


@router.callback_query(F.data.startswith("ch_noop:"))
async def cb_noop(callback: CallbackQuery):
    await callback.answer()
