from dataclasses import dataclass
from os import getenv
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    bot_token: str
    database_path: Path
    redis_url: str | None

    @staticmethod
    def from_env() -> "Config":
        token = getenv("BOT_TOKEN")
        if not token:
            raise ValueError("BOT_TOKEN environment variable is required")

        db_path = Path(getenv("DATABASE_PATH", "/data/bot.db"))
        db_path.parent.mkdir(parents=True, exist_ok=True)

        redis_url = getenv("REDIS_URL")

        return Config(bot_token=token, database_path=db_path, redis_url=redis_url)
