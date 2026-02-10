import time
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery


class ThrottleMiddleware(BaseMiddleware):
    """Simple per-user rate limiter.

    Drops updates that arrive faster than ``rate_limit`` seconds apart
    for the same user. Uses a dict with periodic cleanup to avoid
    unbounded memory growth.
    """

    def __init__(self, rate_limit: float = 0.5, cleanup_interval: int = 300):
        self._rate_limit = rate_limit
        self._cleanup_interval = cleanup_interval
        self._last_time: dict[int, float] = {}
        self._last_cleanup = time.monotonic()

    def _get_user_id(self, event: TelegramObject) -> int | None:
        if isinstance(event, Message) and event.from_user:
            return event.from_user.id
        if isinstance(event, CallbackQuery) and event.from_user:
            return event.from_user.id
        return None

    def _cleanup(self, now: float) -> None:
        if now - self._last_cleanup < self._cleanup_interval:
            return
        cutoff = now - self._rate_limit * 2
        self._last_time = {
            uid: ts for uid, ts in self._last_time.items() if ts > cutoff
        }
        self._last_cleanup = now

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user_id = self._get_user_id(event)
        if user_id is None:
            return await handler(event, data)

        now = time.monotonic()
        self._cleanup(now)

        last = self._last_time.get(user_id, 0.0)
        if now - last < self._rate_limit:
            # Too fast — silently drop
            if isinstance(event, CallbackQuery):
                await event.answer()
            return None

        self._last_time[user_id] = now
        return await handler(event, data)
