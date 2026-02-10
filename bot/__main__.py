import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import Config
from bot.db.database import Database
from bot.middlewares.db import DatabaseMiddleware
from bot.middlewares.throttle import ThrottleMiddleware
from bot.handlers import start, channels, posts

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    config = Config.from_env()

    db = Database(config.database_path)
    await db.init()
    logger.info("Database initialized: %s", config.database_path)

    # FSM storage: Redis if REDIS_URL is set, else in-memory
    storage = MemoryStorage()
    if config.redis_url:
        try:
            from aiogram.fsm.storage.redis import RedisStorage
            storage = RedisStorage.from_url(config.redis_url)
            logger.info("Using Redis FSM storage")
        except ImportError:
            logger.warning("redis package not installed, falling back to MemoryStorage")
        except Exception:
            logger.warning("Failed to connect Redis, falling back to MemoryStorage", exc_info=True)
    else:
        logger.info("REDIS_URL not set, using MemoryStorage (FSM state lost on restart)")

    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=storage)

    # Register middleware
    dp.update.middleware(DatabaseMiddleware(db))
    dp.message.middleware(ThrottleMiddleware())
    dp.callback_query.middleware(ThrottleMiddleware())

    # Register routers (posts first — FSM handlers must have priority)
    dp.include_routers(
        posts.router,
        channels.router,
        start.router,
    )

    logger.info("Bot starting...")
    try:
        await dp.start_polling(bot, drop_pending_updates=True)
    finally:
        await bot.session.close()
        logger.info("Bot stopped.")


if __name__ == "__main__":
    asyncio.run(main())
