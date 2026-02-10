from typing import Any, Awaitable, Callable, Dict

import aiosqlite
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from bot.db.database import Database


class DatabaseMiddleware(BaseMiddleware):
    def __init__(self, database: Database):
        self._database = database

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        async with self._database.connect() as conn:
            conn.row_factory = aiosqlite.Row
            await conn.execute("PRAGMA foreign_keys=ON")
            data["db"] = conn
            return await handler(event, data)
