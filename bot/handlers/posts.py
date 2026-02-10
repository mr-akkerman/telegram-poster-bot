import json
import logging
from urllib.parse import urlparse

from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)
import aiosqlite

from bot.db import queries
from bot.keyboards.menus import BTN_CREATE_POST, BTN_MY_POSTS, main_menu
from bot.states.post import CreatePost

router = Router()
logger = logging.getLogger(__name__)

CANCEL_TEXT = "❌ Отмена"
SKIP_BUTTONS_TEXT = "⏩ Без кнопок"

CB_POST_PUBLISH = "post_pub"
CB_POST_EDIT_TEXT = "post_edit_text"
CB_POST_EDIT_BUTTONS = "post_edit_btn"
CB_POST_CANCEL = "post_cancel"
CB_PUB_CHANNEL = "pub_ch:"

# My posts list callbacks
POSTS_PER_PAGE = 5
CB_POSTS_PAGE = "posts_pg:"
CB_POST_VIEW = "post_v:"
CB_POST_REPUB = "post_rp:"
CB_POST_DELETE = "post_rm:"
CB_POST_CONFIRM_DELETE = "post_rm_y:"
CB_POST_BACK_LIST = "posts_back"
CB_REPUB_CHANNEL = "rpub_ch:"
CB_REPUB_CANCEL = "rpub_cancel"


def _cancel_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=CANCEL_TEXT)]],
        resize_keyboard=True,
    )


def _buttons_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=SKIP_BUTTONS_TEXT)],
            [KeyboardButton(text=CANCEL_TEXT)],
        ],
        resize_keyboard=True,
    )


def _preview_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📢 Опубликовать", callback_data=CB_POST_PUBLISH),
        ],
        [
            InlineKeyboardButton(text="✏️ Изменить текст", callback_data=CB_POST_EDIT_TEXT),
            InlineKeyboardButton(text="🔘 Изменить кнопки", callback_data=CB_POST_EDIT_BUTTONS),
        ],
        [
            InlineKeyboardButton(text="❌ Отмена", callback_data=CB_POST_CANCEL),
        ],
    ])


def _channels_keyboard(channels: list) -> InlineKeyboardMarkup:
    buttons = []
    for ch in channels:
        title = ch["channel_title"]
        username = f" (@{ch['channel_username']})" if ch["channel_username"] else ""
        buttons.append([
            InlineKeyboardButton(
                text=f"{title}{username}",
                callback_data=f"{CB_PUB_CHANNEL}{ch['id']}",
            )
        ])
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data=CB_POST_CANCEL)])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def parse_buttons(text: str) -> list[list[dict]] | None:
    """Parse button text into rows of buttons.

    Format:
        Button text - https://example.com
        Another button - https://example2.com
        ---
        Third button - https://example3.com

    Returns list of rows, each row is a list of {text, url} dicts.
    Returns None if parsing fails.
    """
    rows = []
    current_row = []

    for line in text.strip().splitlines():
        line = line.strip()
        if not line:
            continue

        if line == "---":
            if current_row:
                rows.append(current_row)
                current_row = []
            continue

        # Split by " - " (with spaces around dash)
        parts = line.split(" - ", 1)
        if len(parts) != 2:
            return None

        btn_text = parts[0].strip()
        btn_url = parts[1].strip()

        if not btn_text or not btn_url:
            return None

        # Validate URL
        parsed = urlparse(btn_url)
        if parsed.scheme not in ("http", "https"):
            return None

        current_row.append({"text": btn_text, "url": btn_url})

    if current_row:
        rows.append(current_row)

    return rows if rows else None


def build_inline_keyboard(buttons_data: list[list[dict]]) -> InlineKeyboardMarkup:
    """Build InlineKeyboardMarkup from parsed buttons data."""
    keyboard = []
    for row in buttons_data:
        keyboard.append([
            InlineKeyboardButton(text=btn["text"], url=btn["url"])
            for btn in row
        ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ── Start post creation ───────────────────────────────────────────────────

@router.message(F.text == BTN_CREATE_POST)
async def start_create_post(message: Message, db: aiosqlite.Connection, state: FSMContext):
    channels = await queries.get_channels(db, message.from_user.id)
    if not channels:
        await message.answer(
            "Сначала подключите хотя бы один канал через «📢 Мои каналы».",
        )
        return

    await state.set_state(CreatePost.waiting_for_text)
    await message.answer(
        "Введите текст поста.\n\n"
        "Поддерживается HTML-форматирование:\n"
        "<code>&lt;b&gt;жирный&lt;/b&gt;</code>\n"
        "<code>&lt;i&gt;курсив&lt;/i&gt;</code>\n"
        "<code>&lt;u&gt;подчёркнутый&lt;/u&gt;</code>\n"
        "<code>&lt;a href=\"url\"&gt;ссылка&lt;/a&gt;</code>",
        reply_markup=_cancel_kb(),
    )


# ── Cancel at any FSM state ──────────────────────────────────────────────

@router.message(CreatePost(), F.text == CANCEL_TEXT)
async def cancel_post_creation(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Создание поста отменено.", reply_markup=main_menu())


# ── Receive post text ─────────────────────────────────────────────────────

@router.message(CreatePost.waiting_for_text, F.text)
async def receive_post_text(message: Message, state: FSMContext):
    await state.update_data(text=message.html_text)
    await state.set_state(CreatePost.waiting_for_buttons)
    await message.answer(
        "Текст сохранён. Теперь добавьте кнопки или нажмите «⏩ Без кнопок».\n\n"
        "Формат кнопок (каждая на новой строке):\n"
        "<code>Текст кнопки - https://ссылка.com</code>\n\n"
        "Для нового ряда кнопок используйте разделитель:\n"
        "<code>---</code>\n\n"
        "Пример:\n"
        "<code>Наш сайт - https://example.com\n"
        "Telegram - https://t.me/channel\n"
        "---\n"
        "Подписаться - https://t.me/channel2</code>",
        reply_markup=_buttons_kb(),
    )


@router.message(CreatePost.waiting_for_text)
async def receive_post_text_invalid(message: Message):
    await message.answer("Пожалуйста, отправьте текст поста.")


# ── Receive buttons ───────────────────────────────────────────────────────

@router.message(CreatePost.waiting_for_buttons, F.text == SKIP_BUTTONS_TEXT)
async def skip_buttons(message: Message, state: FSMContext):
    await state.update_data(buttons=None)
    await _show_preview(message, state)


@router.message(CreatePost.waiting_for_buttons, F.text)
async def receive_buttons(message: Message, state: FSMContext):
    buttons = parse_buttons(message.text)
    if buttons is None:
        await message.answer(
            "Неверный формат кнопок. Проверьте формат:\n"
            "<code>Текст кнопки - https://ссылка.com</code>\n\n"
            "URL должен начинаться с http:// или https://\n"
            "Попробуйте ещё раз или нажмите «⏩ Без кнопок».",
        )
        return

    await state.update_data(buttons=buttons)
    await _show_preview(message, state)


@router.message(CreatePost.waiting_for_buttons)
async def receive_buttons_invalid(message: Message):
    await message.answer("Отправьте кнопки текстом или нажмите «⏩ Без кнопок».")


# ── Preview ───────────────────────────────────────────────────────────────

async def _show_preview(message_or_callback, state: FSMContext):
    """Show post preview. Works with both Message and CallbackQuery."""
    data = await state.get_data()
    text = data["text"]
    buttons = data.get("buttons")

    # Build post keyboard (the buttons that will be in the published post)
    post_kb = build_inline_keyboard(buttons) if buttons else None

    # Determine how to send the preview
    if isinstance(message_or_callback, CallbackQuery):
        send = message_or_callback.message.answer
    else:
        send = message_or_callback.answer

    # Send preview of the post itself
    await send(
        "👁 <b>Предпросмотр поста:</b>",
        reply_markup=ReplyKeyboardRemove(),
    )
    await send(text, reply_markup=post_kb)

    # Send control buttons
    await send(
        "Что делаем с постом?",
        reply_markup=_preview_keyboard(),
    )
    await state.set_state(CreatePost.preview)


# ── Preview actions ───────────────────────────────────────────────────────

@router.callback_query(CreatePost.preview, F.data == CB_POST_EDIT_TEXT)
async def cb_edit_text(callback: CallbackQuery, state: FSMContext):
    await state.set_state(CreatePost.waiting_for_text)
    await callback.message.answer(
        "Введите новый текст поста:",
        reply_markup=_cancel_kb(),
    )
    await callback.answer()


@router.callback_query(CreatePost.preview, F.data == CB_POST_EDIT_BUTTONS)
async def cb_edit_buttons(callback: CallbackQuery, state: FSMContext):
    await state.set_state(CreatePost.waiting_for_buttons)
    await callback.message.answer(
        "Отправьте новые кнопки или нажмите «⏩ Без кнопок»:\n\n"
        "Формат: <code>Текст кнопки - https://ссылка.com</code>\n"
        "Разделитель рядов: <code>---</code>",
        reply_markup=_buttons_kb(),
    )
    await callback.answer()


@router.callback_query(CreatePost.preview, F.data == CB_POST_CANCEL)
async def cb_cancel_preview(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("Создание поста отменено.", reply_markup=main_menu())
    await callback.answer()


# ── Publish: select channel ──────────────────────────────────────────────

@router.callback_query(CreatePost.preview, F.data == CB_POST_PUBLISH)
async def cb_publish(callback: CallbackQuery, db: aiosqlite.Connection, state: FSMContext):
    # Save post to DB first
    data = await state.get_data()
    post_id = data.get("post_id")

    if not post_id:
        post_id = await queries.create_post(
            db,
            user_id=callback.from_user.id,
            text=data["text"],
            buttons=data.get("buttons"),
        )
        await state.update_data(post_id=post_id)

    channels = await queries.get_channels(db, callback.from_user.id)
    if not channels:
        await callback.message.answer(
            "У вас нет подключённых каналов. Добавьте канал и попробуйте снова.",
            reply_markup=main_menu(),
        )
        await state.clear()
        await callback.answer()
        return

    await state.set_state(CreatePost.select_channel)
    await callback.message.answer(
        "Выберите канал для публикации:",
        reply_markup=_channels_keyboard(channels),
    )
    await callback.answer()


# ── Publish to channel ────────────────────────────────────────────────────

@router.callback_query(CreatePost.select_channel, F.data.startswith(CB_PUB_CHANNEL))
async def cb_select_channel(
    callback: CallbackQuery,
    db: aiosqlite.Connection,
    bot: Bot,
    state: FSMContext,
):
    channel_db_id = int(callback.data.split(":")[1])
    channel = await queries.get_channel(db, channel_db_id, callback.from_user.id)

    if not channel:
        await callback.message.edit_text("Канал не найден.")
        await state.clear()
        await callback.answer()
        return

    data = await state.get_data()
    text = data["text"]
    buttons = data.get("buttons")
    post_id = data["post_id"]

    post_kb = build_inline_keyboard(buttons) if buttons else None

    try:
        sent = await bot.send_message(
            chat_id=channel["channel_id"],
            text=text,
            reply_markup=post_kb,
        )
    except Exception as e:
        logger.error("Failed to publish to channel %s: %s", channel["channel_id"], e)
        await callback.message.edit_text(
            f"Ошибка публикации: {e}\n\n"
            "Проверьте, что бот всё ещё является администратором канала.",
        )
        await callback.answer()
        return

    await queries.add_publication(db, post_id, channel_db_id, sent.message_id)

    title = channel["channel_title"]
    await callback.message.edit_text(f"✅ Пост опубликован в «{title}»!")
    await state.clear()
    await callback.message.answer("Главное меню:", reply_markup=main_menu())
    await callback.answer()


@router.callback_query(CreatePost.select_channel, F.data == CB_POST_CANCEL)
async def cb_cancel_channel_select(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Публикация отменена.")
    await callback.message.answer("Главное меню:", reply_markup=main_menu())
    await callback.answer()


# ══════════════════════════════════════════════════════════════════════════
# Stage 6 — My Posts: list, view, republish, delete
# ══════════════════════════════════════════════════════════════════════════


def _posts_list_keyboard(posts: list, page: int, total: int) -> InlineKeyboardMarkup:
    buttons = []
    for p in posts:
        preview = p["text"][:40].replace("\n", " ")
        if len(p["text"]) > 40:
            preview += "…"
        buttons.append([
            InlineKeyboardButton(text=f"📄 {preview}", callback_data=f"{CB_POST_VIEW}{p['id']}"),
        ])

    # Pagination
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"{CB_POSTS_PAGE}{page - 1}"))
    total_pages = (total + POSTS_PER_PAGE - 1) // POSTS_PER_PAGE
    nav.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="noop"))
    if (page + 1) * POSTS_PER_PAGE < total:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"{CB_POSTS_PAGE}{page + 1}"))
    if nav:
        buttons.append(nav)

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _post_actions_keyboard(post_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📢 Опубликовать", callback_data=f"{CB_POST_REPUB}{post_id}"),
            InlineKeyboardButton(text="🗑 Удалить", callback_data=f"{CB_POST_DELETE}{post_id}"),
        ],
        [
            InlineKeyboardButton(text="◀️ К списку", callback_data=CB_POST_BACK_LIST),
        ],
    ])


def _repub_channels_keyboard(channels: list, post_id: int) -> InlineKeyboardMarkup:
    buttons = []
    for ch in channels:
        title = ch["channel_title"]
        username = f" (@{ch['channel_username']})" if ch["channel_username"] else ""
        buttons.append([
            InlineKeyboardButton(
                text=f"{title}{username}",
                callback_data=f"{CB_REPUB_CHANNEL}{ch['id']}:{post_id}",
            )
        ])
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data=CB_REPUB_CANCEL)])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ── My Posts list ──────────────────────────────────────────────────────────

@router.message(F.text == BTN_MY_POSTS)
async def menu_my_posts(message: Message, db: aiosqlite.Connection):
    await _show_posts_page(message, db, message.from_user.id, page=0)


async def _show_posts_page(target, db: aiosqlite.Connection, user_id: int, page: int):
    """Show a page of posts. target is Message or CallbackQuery."""
    total = await queries.count_posts(db, user_id)
    if total == 0:
        text = "У вас пока нет созданных постов."
        if isinstance(target, CallbackQuery):
            await target.message.edit_text(text)
        else:
            await target.answer(text)
        return

    offset = page * POSTS_PER_PAGE
    posts = await queries.get_posts(db, user_id, limit=POSTS_PER_PAGE, offset=offset)
    kb = _posts_list_keyboard(posts, page, total)

    text = f"<b>Ваши посты</b> ({total}):"
    if isinstance(target, CallbackQuery):
        await target.message.edit_text(text, reply_markup=kb)
    else:
        await target.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith(CB_POSTS_PAGE))
async def cb_posts_page(callback: CallbackQuery, db: aiosqlite.Connection):
    page = int(callback.data.split(":")[1])
    await _show_posts_page(callback, db, callback.from_user.id, page)
    await callback.answer()


@router.callback_query(F.data == CB_POST_BACK_LIST)
async def cb_back_to_list(callback: CallbackQuery, db: aiosqlite.Connection):
    await _show_posts_page(callback, db, callback.from_user.id, page=0)
    await callback.answer()


# ── View post ──────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith(CB_POST_VIEW))
async def cb_view_post(callback: CallbackQuery, db: aiosqlite.Connection):
    post_id = int(callback.data.split(":")[1])
    post = await queries.get_post(db, post_id, callback.from_user.id)
    if not post:
        await callback.message.edit_text("Пост не найден.")
        await callback.answer()
        return

    buttons_data = json.loads(post["buttons"]) if post["buttons"] else None
    post_kb = build_inline_keyboard(buttons_data) if buttons_data else None

    # Send post preview
    await callback.message.edit_text("👁 <b>Просмотр поста:</b>")
    await callback.message.answer(post["text"], reply_markup=post_kb)
    await callback.message.answer(
        "Действия с постом:",
        reply_markup=_post_actions_keyboard(post_id),
    )
    await callback.answer()


# ── Delete post ────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith(CB_POST_DELETE))
async def cb_delete_post(callback: CallbackQuery):
    post_id = callback.data.split(":")[1]
    await callback.message.edit_text(
        "Вы уверены, что хотите удалить этот пост?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"{CB_POST_CONFIRM_DELETE}{post_id}"),
                InlineKeyboardButton(text="❌ Отмена", callback_data=CB_POST_BACK_LIST),
            ]
        ]),
    )
    await callback.answer()


@router.callback_query(F.data.startswith(CB_POST_CONFIRM_DELETE))
async def cb_confirm_delete_post(callback: CallbackQuery, db: aiosqlite.Connection):
    post_id = int(callback.data.split(":")[1])
    deleted = await queries.delete_post(db, post_id, callback.from_user.id)
    if deleted:
        await callback.message.edit_text("✅ Пост удалён.")
    else:
        await callback.message.edit_text("Пост не найден или уже удалён.")
    await callback.answer()


# ── Republish existing post ────────────────────────────────────────────────

@router.callback_query(F.data.startswith(CB_POST_REPUB))
async def cb_republish_post(callback: CallbackQuery, db: aiosqlite.Connection):
    post_id = int(callback.data.split(":")[1])
    post = await queries.get_post(db, post_id, callback.from_user.id)
    if not post:
        await callback.message.edit_text("Пост не найден.")
        await callback.answer()
        return

    channels = await queries.get_channels(db, callback.from_user.id)
    if not channels:
        await callback.message.edit_text("У вас нет подключённых каналов.")
        await callback.answer()
        return

    await callback.message.edit_text(
        "Выберите канал для публикации:",
        reply_markup=_repub_channels_keyboard(channels, post_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith(CB_REPUB_CHANNEL))
async def cb_repub_select_channel(callback: CallbackQuery, db: aiosqlite.Connection, bot: Bot):
    parts = callback.data.split(":")
    channel_db_id = int(parts[1])
    post_id = int(parts[2])

    channel = await queries.get_channel(db, channel_db_id, callback.from_user.id)
    post = await queries.get_post(db, post_id, callback.from_user.id)

    if not channel or not post:
        await callback.message.edit_text("Канал или пост не найден.")
        await callback.answer()
        return

    buttons_data = json.loads(post["buttons"]) if post["buttons"] else None
    post_kb = build_inline_keyboard(buttons_data) if buttons_data else None

    try:
        sent = await bot.send_message(
            chat_id=channel["channel_id"],
            text=post["text"],
            reply_markup=post_kb,
        )
    except Exception as e:
        logger.error("Failed to republish to channel %s: %s", channel["channel_id"], e)
        await callback.message.edit_text(
            f"Ошибка публикации: {e}\n\n"
            "Проверьте, что бот является администратором канала.",
        )
        await callback.answer()
        return

    await queries.add_publication(db, post_id, channel_db_id, sent.message_id)
    title = channel["channel_title"]
    await callback.message.edit_text(f"✅ Пост опубликован в «{title}»!")
    await callback.answer()


@router.callback_query(F.data == CB_REPUB_CANCEL)
async def cb_repub_cancel(callback: CallbackQuery, db: aiosqlite.Connection):
    await _show_posts_page(callback, db, callback.from_user.id, page=0)
    await callback.answer()


@router.callback_query(F.data == "noop")
async def cb_noop(callback: CallbackQuery):
    await callback.answer()
