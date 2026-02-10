import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import Config
from bot.db.database import Database
from bot.middlewares.db import DatabaseMiddleware
from bot.handlers import start, channels, posts

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    config = Config.from_env()

    db = Database(config.database_path)
    await db.connect()
    logger.info("Database connected: %s", config.database_path)

    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Register middleware
    dp.update.middleware(DatabaseMiddleware(db))

    # Register routers
    dp.include_routers(
        start.router,
        channels.router,
        posts.router,
    )

    logger.info("Bot starting...")
    try:
        await dp.start_polling(bot)
    finally:
        await db.close()
        await bot.session.close()
        logger.info("Bot stopped.")


if __name__ == "__main__":
    asyncio.run(main())
