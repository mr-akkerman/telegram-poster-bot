import aiosqlite
from pathlib import Path

SQL_CREATE_TABLES = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS channels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    channel_id INTEGER NOT NULL,
    channel_title TEXT NOT NULL,
    channel_username TEXT,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE(user_id, channel_id)
);

CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    text TEXT NOT NULL,
    buttons TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS publications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER NOT NULL,
    channel_id INTEGER NOT NULL,
    published_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    message_id INTEGER,
    FOREIGN KEY (post_id) REFERENCES posts(id),
    FOREIGN KEY (channel_id) REFERENCES channels(id)
);
"""


class Database:
    def __init__(self, db_path: Path):
        self._db_path = db_path

    async def init(self):
        """Create tables and set PRAGMAs. Call once on startup."""
        async with aiosqlite.connect(self._db_path) as conn:
            await conn.executescript(SQL_CREATE_TABLES)
            await conn.execute("PRAGMA journal_mode=WAL")
            await conn.execute("PRAGMA foreign_keys=ON")
            await conn.commit()

    def connect(self) -> aiosqlite.Connection:
        """Create a new connection. Intended for use with ``async with``."""
        return aiosqlite.connect(self._db_path)

    @property
    def path(self) -> Path:
        return self._db_path
