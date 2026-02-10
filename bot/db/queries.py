import json

import aiosqlite


# ── Users ──────────────────────────────────────────────────────────────────

async def upsert_user(
    conn: aiosqlite.Connection, user_id: int, username: str | None
) -> None:
    await conn.execute(
        """
        INSERT INTO users (id, username) VALUES (?, ?)
        ON CONFLICT(id) DO UPDATE SET username = excluded.username
        """,
        (user_id, username),
    )
    await conn.commit()


# ── Channels ───────────────────────────────────────────────────────────────

async def add_channel(
    conn: aiosqlite.Connection,
    user_id: int,
    channel_id: int,
    title: str,
    username: str | None,
) -> bool:
    """Add a channel. Returns True if added, False if already exists."""
    try:
        await conn.execute(
            """
            INSERT INTO channels (user_id, channel_id, channel_title, channel_username)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, channel_id, title, username),
        )
        await conn.commit()
        return True
    except aiosqlite.IntegrityError:
        return False


async def get_channels(
    conn: aiosqlite.Connection, user_id: int
) -> list[aiosqlite.Row]:
    cursor = await conn.execute(
        "SELECT * FROM channels WHERE user_id = ? ORDER BY added_at DESC",
        (user_id,),
    )
    return await cursor.fetchall()


async def get_channel(
    conn: aiosqlite.Connection, channel_db_id: int, user_id: int
) -> aiosqlite.Row | None:
    cursor = await conn.execute(
        "SELECT * FROM channels WHERE id = ? AND user_id = ?",
        (channel_db_id, user_id),
    )
    return await cursor.fetchone()


async def delete_channel(
    conn: aiosqlite.Connection, channel_db_id: int, user_id: int
) -> bool:
    cursor = await conn.execute(
        "DELETE FROM channels WHERE id = ? AND user_id = ?",
        (channel_db_id, user_id),
    )
    await conn.commit()
    return cursor.rowcount > 0


# ── Posts ──────────────────────────────────────────────────────────────────

async def create_post(
    conn: aiosqlite.Connection,
    user_id: int,
    text: str,
    buttons: list[list[dict]] | None = None,
) -> int:
    """Create a post. Returns the post ID."""
    buttons_json = json.dumps(buttons, ensure_ascii=False) if buttons else None
    cursor = await conn.execute(
        "INSERT INTO posts (user_id, text, buttons) VALUES (?, ?, ?)",
        (user_id, text, buttons_json),
    )
    await conn.commit()
    return cursor.lastrowid


async def get_posts(
    conn: aiosqlite.Connection, user_id: int, limit: int = 20, offset: int = 0
) -> list[aiosqlite.Row]:
    cursor = await conn.execute(
        "SELECT * FROM posts WHERE user_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (user_id, limit, offset),
    )
    return await cursor.fetchall()


async def get_post(
    conn: aiosqlite.Connection, post_id: int, user_id: int
) -> aiosqlite.Row | None:
    cursor = await conn.execute(
        "SELECT * FROM posts WHERE id = ? AND user_id = ?",
        (post_id, user_id),
    )
    return await cursor.fetchone()


async def delete_post(
    conn: aiosqlite.Connection, post_id: int, user_id: int
) -> bool:
    cursor = await conn.execute(
        "DELETE FROM posts WHERE id = ? AND user_id = ?",
        (post_id, user_id),
    )
    await conn.commit()
    return cursor.rowcount > 0


async def count_posts(conn: aiosqlite.Connection, user_id: int) -> int:
    cursor = await conn.execute(
        "SELECT COUNT(*) FROM posts WHERE user_id = ?", (user_id,)
    )
    row = await cursor.fetchone()
    return row[0]


# ── Publications ───────────────────────────────────────────────────────────

async def add_publication(
    conn: aiosqlite.Connection,
    post_id: int,
    channel_id: int,
    message_id: int,
) -> int:
    cursor = await conn.execute(
        "INSERT INTO publications (post_id, channel_id, message_id) VALUES (?, ?, ?)",
        (post_id, channel_id, message_id),
    )
    await conn.commit()
    return cursor.lastrowid
